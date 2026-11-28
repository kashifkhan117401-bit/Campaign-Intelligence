"""Background processing tasks for YouTube analysis and resumable publishing."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.audience_engine import generate_audience_intelligence
from app.ai.sentiment_engine import analyze_comments_in_batches
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import decrypt_secret
from app.integrations.youtube_client import (
    YouTubeDataClient,
    YouTubeIntegrationError,
    build_demo_video_and_comments,
)
from app.integrations.youtube_oauth import (
    YouTubeOAuthError,
    refresh_access_token,
    upload_video_to_youtube,
)
from app.models.analysis import (
    AudienceInsight,
    Comment,
    CommentSentimentResult,
    VideoAnalysis,
    YouTubeVideo,
)
from app.models.content import PublishingJob, UploadedMedia
from app.models.reporting import APIUsageLog, CampaignRecord
from app.models.user import ConnectedYouTubeChannel
from app.services.neon_storage import ensure_local_video_file

logger = logging.getLogger(__name__)


def _record_usage(
    db: Session,
    user_id: Optional[str],
    provider: str,
    endpoint: str,
    status_code: int = 200,
    units_used: int = 1,
    latency_ms: int = 0,
    error_message: Optional[str] = None,
) -> None:
    try:
        db.add(
            APIUsageLog(
                user_id=user_id,
                provider=provider,
                endpoint=endpoint,
                status_code=status_code,
                units_used=units_used,
                latency_ms=latency_ms,
                error_message=error_message,
            )
        )
        db.commit()
    except Exception:
        db.rollback()


def run_youtube_analysis_task(analysis_id: str, use_demo_fallback: bool = False) -> None:
    """Execute end-to-end YouTube comment collection, batch sentiment analysis, and audience insights."""
    db = SessionLocal()
    t0 = time.monotonic()
    try:
        analysis = db.query(VideoAnalysis).filter(VideoAnalysis.id == analysis_id).first()
        if not analysis:
            logger.error("Analysis %s not found for background processing.", analysis_id)
            return

        video = db.query(YouTubeVideo).filter(YouTubeVideo.id == analysis.video_id).first()
        if not video:
            analysis.status = "failed"
            analysis.error_message = "Associated YouTube video record not found."
            db.commit()
            return

        settings = get_settings()
        yt_client = YouTubeDataClient()

        analysis.status = "collecting"
        analysis.progress_pct = 10
        analysis.status_message = "Fetching YouTube video metadata..."
        db.commit()

        comments_data = []
        comments_disabled = False
        is_demo = False

        if yt_client.is_configured:
            video_meta = yt_client.fetch_video_metadata(video.youtube_video_id)
            _record_usage(db, analysis.user_id, "youtube_data", "videos.list", 200, 1, int((time.monotonic() - t0) * 1000))

            for field, val in video_meta.items():
                if hasattr(video, field):
                    setattr(video, field, val)
            db.commit()

            analysis.progress_pct = 20
            analysis.status_message = f"Collecting up to {analysis.requested_max_comments} public comments..."
            db.commit()

            def _on_collect(count: int):
                analysis.collected_comments_count = count
                analysis.progress_pct = min(38, 20 + int((count / max(1, analysis.requested_max_comments)) * 18))
                analysis.status_message = f"Collected {count} comments so far..."
                db.commit()

            comments_data, comments_disabled = yt_client.fetch_top_level_comments(
                video.youtube_video_id,
                max_comments=analysis.requested_max_comments,
                progress_cb=_on_collect,
            )
            video.comments_disabled = comments_disabled
            _record_usage(
                db,
                analysis.user_id,
                "youtube_data",
                "commentThreads.list",
                200,
                max(1, (len(comments_data) // 100) + 1),
                int((time.monotonic() - t0) * 1000),
            )
        elif settings.ALLOW_DEMO_MODE and use_demo_fallback:
            is_demo = True
            video_meta, comments_data = build_demo_video_and_comments(
                video.youtube_video_id, max_comments=analysis.requested_max_comments
            )
            for field, val in video_meta.items():
                if hasattr(video, field):
                    setattr(video, field, val)
            analysis.is_demo_data = True
            analysis.collected_comments_count = len(comments_data)
            analysis.status_message = f"[DEMO MODE] Loaded {len(comments_data)} sample comments for analysis..."
            db.commit()
        else:
            raise YouTubeIntegrationError(
                "YOUTUBE_API_KEY is not configured. Add your YouTube Data API v3 key in .env, "
                "or check 'Use Development Demo Mode' to test with visibly labeled demo data.",
                code="missing_api_key",
                status_code=503,
            )

        analysis.collected_comments_count = len(comments_data)
        analysis.status = "analyzing"
        analysis.progress_pct = 40
        analysis.status_message = (
            "Comments are disabled on this video; completing video summary."
            if comments_disabled
            else f"Running AI sentiment & emotion analysis on {len(comments_data)} comments..."
        )
        db.commit()

        # Persist collected comments
        comment_models = {}
        for c in comments_data:
            cm = Comment(
                analysis_id=analysis.id,
                youtube_comment_id=c["youtube_comment_id"],
                author_display_name=c["author_display_name"],
                text_original=c["text_original"],
                text_sanitized=c["text_sanitized"],
                like_count=c["like_count"],
                reply_count=c["reply_count"],
                published_at=c.get("published_at"),
            )
            db.add(cm)
            comment_models[c["youtube_comment_id"]] = cm
        db.flush()

        def _on_analyze(pct: int, msg: str):
            analysis.progress_pct = pct
            analysis.status_message = msg
            db.commit()

        video_dict = {
            "youtube_video_id": video.youtube_video_id,
            "title": video.title,
            "description": video.description,
            "channel_title": video.channel_title,
        }
        per_comment_results, summary = analyze_comments_in_batches(
            video_meta=video_dict,
            comments=comments_data,
            progress_cb=_on_analyze,
        )

        # Persist per-comment sentiment rows
        for r in per_comment_results:
            cm = comment_models.get(r["youtube_comment_id"])
            if not cm:
                continue
            db.add(
                CommentSentimentResult(
                    comment_id=cm.id,
                    analysis_id=analysis.id,
                    sentiment=r["sentiment"],
                    confidence=r["confidence"],
                    primary_emotion=r["primary_emotion"],
                    secondary_emotions_json=r.get("secondary_emotions", []),
                    purchase_intent=r.get("purchase_intent", False),
                    is_complaint=r.get("is_complaint", False),
                    is_feature_request=r.get("is_feature_request", False),
                    is_question=r.get("is_question", False),
                    topics_json=r.get("topics", []),
                    keywords_json=r.get("keywords", []),
                )
            )

        for field, val in summary.items():
            if hasattr(analysis, field):
                setattr(analysis, field, val)

        analysis.progress_pct = 88
        analysis.status_message = "Synthesizing Audience Intelligence & Opportunity Score..."
        db.commit()

        insight_data = generate_audience_intelligence(
            video_meta=video_dict,
            analysis_summary=summary,
            comments=comments_data,
            per_comment_results=per_comment_results,
        )
        insight = AudienceInsight(
            analysis_id=analysis.id,
            user_id=analysis.user_id,
            is_demo_data=is_demo,
            **insight_data,
        )
        db.add(insight)

        analysis.status = "completed"
        analysis.progress_pct = 100
        analysis.status_message = (
            f"Completed analysis of {analysis.analyzed_comments_count} comments"
            + (" (Development Demo Data)" if is_demo else "")
        )
        analysis.completed_at = datetime.now(timezone.utc)

        db.add(
            CampaignRecord(
                user_id=analysis.user_id,
                analysis_id=analysis.id,
                name=f"Analysis: {video.title[:120]}",
                record_type="video_analysis",
                status="completed",
                summary=(
                    f"Analyzed {analysis.analyzed_comments_count} comments — "
                    f"{analysis.positive_pct}% positive, Opportunity Score {insight.opportunity_score}/100."
                ),
                metadata_json={
                    "youtube_video_id": video.youtube_video_id,
                    "is_demo_data": is_demo,
                    "positive_pct": analysis.positive_pct,
                },
            )
        )
        db.commit()
    except YouTubeIntegrationError as exc:
        logger.warning("YouTube analysis %s failed (%s): %s", analysis_id, exc.code, exc.message)
        db.rollback()
        analysis = db.query(VideoAnalysis).filter(VideoAnalysis.id == analysis_id).first()
        if analysis:
            analysis.status = "failed"
            analysis.error_message = exc.message
            analysis.status_message = f"Failed: {exc.code}"
            db.commit()
            _record_usage(db, analysis.user_id, "youtube_data", "analyze", exc.status_code, 1, int((time.monotonic() - t0) * 1000), exc.message)
    except Exception as exc:
        logger.exception("Unexpected error during YouTube analysis %s: %s", analysis_id, exc)
        db.rollback()
        analysis = db.query(VideoAnalysis).filter(VideoAnalysis.id == analysis_id).first()
        if analysis:
            analysis.status = "failed"
            analysis.error_message = f"Unexpected analysis error: {exc}"
            analysis.status_message = "Analysis failed"
            db.commit()
    finally:
        db.close()


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def run_youtube_publish_task(job_id: str, is_scheduled_auto_upload: bool = False) -> None:
    """Execute confirmed YouTube Data API v3 upload with resumable progress tracking."""
    db = SessionLocal()
    t0 = time.monotonic()
    try:
        job = db.query(PublishingJob).filter(PublishingJob.id == job_id).first()
        if not job:
            return
        if not job.user_confirmed:
            job.status = "failed"
            job.error_message = "Explicit user confirmation is required prior to publishing."
            db.commit()
            return

        media = db.query(UploadedMedia).filter(UploadedMedia.id == job.media_id).first()
        channel = (
            db.query(ConnectedYouTubeChannel)
            .filter(ConnectedYouTubeChannel.id == job.channel_id)
            .first()
            if job.channel_id
            else None
        )
        if not media or not channel:
            job.status = "failed"
            job.error_message = "Missing uploaded video media or connected YouTube channel."
            db.commit()
            return

        if channel.is_demo_connection:
            job.status = "failed"
            job.error_message = (
                "Cannot publish to YouTube using a demo channel placeholder. "
                "Configure GOOGLE_CLIENT_ID & GOOGLE_CLIENT_SECRET and connect your real YouTube channel via OAuth 2.0."
            )
            db.commit()
            return

        job.status = "uploading"
        job.upload_progress_pct = 5
        db.commit()

        access_token = decrypt_secret(channel.encrypted_access_token)
        token_expiry = _as_utc(channel.token_expiry)
        if token_expiry and token_expiry <= datetime.now(timezone.utc):
            refreshed = refresh_access_token(channel.encrypted_refresh_token)
            access_token = refreshed["access_token"]
            channel.encrypted_access_token = refreshed["encrypted_access_token"]
            channel.token_expiry = refreshed["expires_at"]
            db.commit()

        def _progress(pct: int, uploaded_bytes: int):
            job.upload_progress_pct = pct
            job.bytes_uploaded = uploaded_bytes
            db.commit()

        # When auto-uploading at the scheduled time (or if the scheduled time has already passed),
        # upload directly with the chosen privacy_status instead of sending a past YouTube publishAt.
        sched_utc = _as_utc(job.scheduled_publish_at)
        yt_publish_at = (
            None
            if is_scheduled_auto_upload or not sched_utc or sched_utc <= datetime.now(timezone.utc)
            else sched_utc
        )

        local_video_path = ensure_local_video_file(media.file_path, media.stored_filename)

        api_resp = upload_video_to_youtube(
            access_token=access_token,
            file_path=local_video_path,
            mime_type=media.mime_type,
            title=job.title,
            description=job.description,
            tags=job.tags_json,
            category_id=job.category_id,
            privacy_status=job.privacy_status,
            scheduled_publish_at=yt_publish_at,
            progress_cb=_progress,
        )

        yt_id = api_resp["id"]
        job.youtube_video_id = yt_id
        job.youtube_video_url = f"https://www.youtube.com/watch?v={yt_id}"
        job.status = "scheduled" if yt_publish_at else "published"
        job.upload_progress_pct = 100
        job.api_response_json = api_resp

        db.add(
            CampaignRecord(
                user_id=job.user_id,
                publishing_job_id=job.id,
                name=f"Published: {job.title[:120]}",
                record_type="youtube_publish",
                status=job.status,
                summary=f"Uploaded to YouTube ({job.privacy_status}) — {job.youtube_video_url}",
                metadata_json={"youtube_video_id": yt_id, "privacy_status": job.privacy_status},
            )
        )
        db.commit()
        _record_usage(db, job.user_id, "youtube_upload", "videos.insert", 200, 1600, int((time.monotonic() - t0) * 1000))
    except YouTubeOAuthError as exc:
        logger.warning("Publishing job %s failed: %s", job_id, exc.message)
        db.rollback()
        job = db.query(PublishingJob).filter(PublishingJob.id == job_id).first()
        if job:
            job.status = "interrupted" if exc.code == "upload_interrupted" else "failed"
            job.error_message = exc.message
            db.commit()
            _record_usage(db, job.user_id, "youtube_upload", "videos.insert", exc.status_code, 100, int((time.monotonic() - t0) * 1000), exc.message)
    except Exception as exc:
        logger.exception("Unexpected publishing failure for job %s: %s", job_id, exc)
        db.rollback()
        job = db.query(PublishingJob).filter(PublishingJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = f"Publishing failed: {exc}"
            db.commit()
    finally:
        db.close()

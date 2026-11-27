"""YouTube OAuth 2.0 connection and confirmed video publishing routes."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, decode_token, encrypt_secret
from app.integrations.youtube_oauth import (
    YouTubeOAuthError,
    build_oauth_authorization_url,
    exchange_code_for_tokens,
    fetch_authenticated_channel,
)
from app.models.content import PublishingJob, UploadedMedia
from app.models.user import ConnectedYouTubeChannel, User
from app.schemas.video import (
    ConnectedChannelResponse,
    PublishingJobResponse,
    RescheduleJobRequest,
    YouTubePublishRequest,
)
from app.services.upload_scheduler import as_utc, process_due_scheduled_uploads
from app.tasks.analysis_tasks import run_youtube_publish_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/youtube", tags=["YouTube OAuth & Publishing"])


@router.get("/connect")
def connect_youtube_channel(current_user: User = Depends(get_current_user)):
    settings = get_settings()
    if not settings.has_google_oauth:
        return {
            "configured": False,
            "authorization_url": None,
            "message": (
                "Google OAuth 2.0 is not yet configured. Add GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, "
                "and GOOGLE_OAUTH_REDIRECT_URI to your backend .env file (see docs/YOUTUBE_OAUTH_SETUP.md)."
            ),
            "required_scopes": [
                "https://www.googleapis.com/auth/youtube.upload",
                "https://www.googleapis.com/auth/youtube.readonly",
                "https://www.googleapis.com/auth/yt-analytics.readonly",
            ],
        }

    state_token = create_access_token(subject=current_user.id, role="oauth_state")
    auth_url = build_oauth_authorization_url(state=state_token)
    return {
        "configured": True,
        "authorization_url": auth_url,
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        "message": "Redirect user to authorization_url to grant YouTube channel access.",
    }


@router.get("/callback")
def youtube_oauth_callback(
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if error:
        logger.warning("YouTube OAuth callback returned error: %s", error)
        qs = urlencode({"oauth_error": error})
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/video-studio?{qs}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth code or state parameter.")

    decoded = decode_token(state)
    if not decoded or decoded.get("role") != "oauth_state":
        logger.warning("YouTube OAuth callback received invalid or expired state token.")
        qs = urlencode({"oauth_error": "invalid_state", "oauth_detail": "OAuth session expired. Please click Connect YouTube Channel again."})
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/video-studio?{qs}")
    user_id = decoded.get("sub")

    try:
        tokens = exchange_code_for_tokens(code)
        ch_info = fetch_authenticated_channel(tokens["access_token"])
    except YouTubeOAuthError as exc:
        logger.warning("YouTube OAuth callback failed (%s): %s", exc.code, exc.message)
        qs = urlencode({"oauth_error": exc.code, "oauth_detail": exc.message})
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/video-studio?{qs}")

    existing = (
        db.query(ConnectedYouTubeChannel)
        .filter(
            ConnectedYouTubeChannel.user_id == user_id,
            ConnectedYouTubeChannel.channel_id == ch_info["channel_id"],
        )
        .first()
    )
    if existing:
        existing.channel_title = ch_info["channel_title"]
        existing.channel_thumbnail = ch_info["channel_thumbnail"]
        existing.subscriber_count = ch_info["subscriber_count"]
        existing.encrypted_access_token = encrypt_secret(tokens["access_token"])
        if tokens.get("refresh_token"):
            existing.encrypted_refresh_token = encrypt_secret(tokens["refresh_token"])
        existing.token_expiry = tokens["expires_at"]
        existing.scopes = tokens["scope"]
        existing.is_active = True
    else:
        db.add(
            ConnectedYouTubeChannel(
                user_id=user_id,
                channel_id=ch_info["channel_id"],
                channel_title=ch_info["channel_title"],
                channel_thumbnail=ch_info["channel_thumbnail"],
                subscriber_count=ch_info["subscriber_count"],
                encrypted_access_token=encrypt_secret(tokens["access_token"]),
                encrypted_refresh_token=encrypt_secret(tokens.get("refresh_token", "")),
                token_expiry=tokens["expires_at"],
                scopes=tokens["scope"],
                is_active=True,
                is_demo_connection=False,
            )
        )
    db.commit()
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/video-studio?oauth_connected=true")


@router.get("/channels", response_model=List[ConnectedChannelResponse])
def list_connected_channels(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(ConnectedYouTubeChannel)
        .filter(
            ConnectedYouTubeChannel.user_id == current_user.id,
            ConnectedYouTubeChannel.is_active.is_(True),
        )
        .order_by(desc(ConnectedYouTubeChannel.created_at))
        .all()
    )
    return [ConnectedChannelResponse.model_validate(r) for r in rows]


@router.delete("/channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_channel(
    channel_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ch = (
        db.query(ConnectedYouTubeChannel)
        .filter(
            ConnectedYouTubeChannel.id == channel_id,
            ConnectedYouTubeChannel.user_id == current_user.id,
        )
        .first()
    )
    if not ch:
        raise HTTPException(status_code=404, detail="Connected channel not found.")
    db.delete(ch)
    db.commit()
    return None


@router.post("/publish", response_model=PublishingJobResponse, status_code=status.HTTP_201_CREATED)
def publish_video(
    payload: YouTubePublishRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    media = (
        db.query(UploadedMedia)
        .filter(UploadedMedia.id == payload.media_id, UploadedMedia.user_id == current_user.id)
        .first()
    )
    if not media:
        raise HTTPException(status_code=404, detail="Uploaded media file not found.")

    if payload.publish_action == "draft":
        job = PublishingJob(
            user_id=current_user.id,
            media_id=media.id,
            channel_id=payload.channel_id,
            status="draft",
            privacy_status=payload.privacy_status,
            scheduled_publish_at=payload.scheduled_publish_at,
            title=payload.title,
            description=payload.description,
            tags_json=payload.tags[:30],
            category_id=payload.category_id,
            pinned_comment=payload.pinned_comment,
            user_confirmed=False,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return PublishingJobResponse.model_validate(job)

    # Non-draft publishing MUST have explicit user confirmation & a connected real OAuth channel
    if not payload.user_confirmed:
        raise HTTPException(
            status_code=400,
            detail="Explicit user confirmation (user_confirmed=true) is required before uploading or publishing to YouTube.",
        )

    channel = None
    if payload.channel_id:
        channel = (
            db.query(ConnectedYouTubeChannel)
            .filter(
                ConnectedYouTubeChannel.id == payload.channel_id,
                ConnectedYouTubeChannel.user_id == current_user.id,
                ConnectedYouTubeChannel.is_active.is_(True),
            )
            .first()
        )
    if not channel:
        raise HTTPException(
            status_code=400,
            detail=(
                "A connected YouTube channel via Google OAuth 2.0 is required to publish. "
                "Connect your channel first or save as draft."
            ),
        )

    scheduled_utc = as_utc(payload.scheduled_publish_at)
    if payload.publish_action == "schedule":
        if not scheduled_utc:
            raise HTTPException(
                status_code=422,
                detail="scheduled_publish_at (ISO-8601 UTC datetime) is required when scheduling an automatic upload.",
            )
        if scheduled_utc <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=422,
                detail="Scheduled upload time must be in the future.",
            )

    is_delayed_schedule = payload.publish_action == "schedule" and scheduled_utc is not None
    job = PublishingJob(
        user_id=current_user.id,
        media_id=media.id,
        channel_id=channel.id,
        status="scheduled_upload" if is_delayed_schedule else "queued",
        privacy_status=payload.privacy_status,
        scheduled_publish_at=scheduled_utc,
        title=payload.title,
        description=payload.description,
        tags_json=payload.tags[:30],
        category_id=payload.category_id,
        pinned_comment=payload.pinned_comment,
        user_confirmed=True,
        confirmed_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    if not is_delayed_schedule:
        if get_settings().is_vercel:
            run_youtube_publish_task(job.id)
        else:
            background_tasks.add_task(run_youtube_publish_task, job.id)
    return PublishingJobResponse.model_validate(job)


@router.get("/cron/process-scheduled")
def cron_process_scheduled_uploads(authorization: Optional[str] = Header(default=None)):
    """Trigger due scheduled YouTube uploads (for Vercel Cron or external schedulers)."""
    settings = get_settings()
    if settings.CRON_SECRET:
        expected = f"Bearer {settings.CRON_SECRET}"
        if authorization != expected:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized cron invocation.")

    def _run_sync(job_id: str) -> None:
        run_youtube_publish_task(job_id, is_scheduled_auto_upload=True)

    processed = process_due_scheduled_uploads(dispatch_fn=_run_sync)
    return {"processed_count": len(processed), "job_ids": processed}


@router.patch("/jobs/{job_id}/schedule", response_model=PublishingJobResponse)
def reschedule_publishing_job(
    job_id: str,
    payload: RescheduleJobRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = (
        db.query(PublishingJob)
        .filter(PublishingJob.id == job_id, PublishingJob.user_id == current_user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Publishing job not found.")
    if job.status != "scheduled_upload":
        raise HTTPException(
            status_code=400,
            detail=f"Only pending scheduled uploads can be rescheduled (current status: {job.status}).",
        )

    new_time = as_utc(payload.scheduled_publish_at)
    if not new_time or new_time <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="New scheduled upload time must be in the future.")

    job.scheduled_publish_at = new_time
    db.commit()
    db.refresh(job)
    return PublishingJobResponse.model_validate(job)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_publishing_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = (
        db.query(PublishingJob)
        .filter(PublishingJob.id == job_id, PublishingJob.user_id == current_user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Publishing job not found.")
    if job.status == "uploading":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a job while it is actively uploading to YouTube.",
        )
    db.delete(job)
    db.commit()
    return None


@router.delete("/jobs", status_code=status.HTTP_204_NO_CONTENT)
def clear_publishing_jobs_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(PublishingJob)
        .filter(PublishingJob.user_id == current_user.id, PublishingJob.status != "uploading")
        .all()
    )
    for row in rows:
        db.delete(row)
    db.commit()
    return None


@router.get("/jobs", response_model=List[PublishingJobResponse])
def list_publishing_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(PublishingJob)
        .filter(PublishingJob.user_id == current_user.id)
        .order_by(desc(PublishingJob.created_at))
        .limit(50)
        .all()
    )
    return [PublishingJobResponse.model_validate(r) for r in rows]


@router.get("/publishing-status/{job_id}", response_model=PublishingJobResponse)
def get_publishing_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = (
        db.query(PublishingJob)
        .filter(PublishingJob.id == job_id, PublishingJob.user_id == current_user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Publishing job not found.")
    return PublishingJobResponse.model_validate(job)

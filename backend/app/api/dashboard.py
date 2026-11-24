"""Main SaaS Dashboard overview and campaign activity endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.ads import AdvertisingStrategy
from app.models.analysis import VideoAnalysis
from app.models.content import GeneratedContent, PublishingJob
from app.models.reporting import CampaignRecord, PDFReport
from app.models.user import User
from app.schemas.reporting import (
    CampaignRecordResponse,
    DashboardActivityResponse,
    DashboardOverviewResponse,
)
from app.services.video_processor import is_ffmpeg_available

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview", response_model=DashboardOverviewResponse)
def get_dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    uid = current_user.id

    total_videos = db.query(func.count(VideoAnalysis.id)).filter(VideoAnalysis.user_id == uid).scalar() or 0
    total_comments = (
        db.query(func.coalesce(func.sum(VideoAnalysis.analyzed_comments_count), 0))
        .filter(VideoAnalysis.user_id == uid, VideoAnalysis.status == "completed")
        .scalar()
        or 0
    )
    avg_pos = (
        db.query(func.avg(VideoAnalysis.positive_pct))
        .filter(VideoAnalysis.user_id == uid, VideoAnalysis.status == "completed")
        .scalar()
        or 0.0
    )
    content_count = db.query(func.count(GeneratedContent.id)).filter(GeneratedContent.user_id == uid).scalar() or 0
    reports_count = db.query(func.count(PDFReport.id)).filter(PDFReport.user_id == uid).scalar() or 0
    published_count = (
        db.query(func.count(PublishingJob.id))
        .filter(PublishingJob.user_id == uid, PublishingJob.status.in_(["published", "scheduled"]))
        .scalar()
        or 0
    )
    ads_count = db.query(func.count(AdvertisingStrategy.id)).filter(AdvertisingStrategy.user_id == uid).scalar() or 0

    recent_rows = (
        db.query(VideoAnalysis)
        .options(joinedload(VideoAnalysis.video))
        .filter(VideoAnalysis.user_id == uid)
        .order_by(desc(VideoAnalysis.created_at))
        .limit(6)
        .all()
    )

    recent_analyses = [
        {
            "id": a.id,
            "status": a.status,
            "progress_pct": a.progress_pct,
            "analyzed_comments_count": a.analyzed_comments_count,
            "positive_pct": a.positive_pct,
            "negative_pct": a.negative_pct,
            "neutral_pct": a.neutral_pct,
            "is_demo_data": a.is_demo_data,
            "created_at": a.created_at.isoformat(),
            "video_title": a.video.title if a.video else "Untitled",
            "thumbnail_url": a.video.thumbnail_url if a.video else "",
            "channel_title": a.video.channel_title if a.video else "",
            "youtube_video_id": a.video.youtube_video_id if a.video else "",
        }
        for a in recent_rows
    ]

    sentiment_history = [
        {
            "label": (a.video.title[:22] + "...") if a.video and len(a.video.title) > 22 else (a.video.title if a.video else a.id[:6]),
            "positive": a.positive_pct,
            "negative": a.negative_pct,
            "neutral": a.neutral_pct,
            "comments": a.analyzed_comments_count,
        }
        for a in reversed(recent_rows)
        if a.status == "completed"
    ]

    content_mix = [
        {"category": "Analyses", "count": int(total_videos)},
        {"category": "Content Packs", "count": int(content_count)},
        {"category": "Ads Strategies", "count": int(ads_count)},
        {"category": "PDF Reports", "count": int(reports_count)},
        {"category": "Published Videos", "count": int(published_count)},
    ]

    settings = get_settings()
    return DashboardOverviewResponse(
        total_videos_analyzed=int(total_videos),
        total_comments_analyzed=int(total_comments),
        avg_positive_sentiment=round(float(avg_pos), 1),
        content_generated_count=int(content_count),
        reports_created_count=int(reports_count),
        published_videos_count=int(published_count),
        active_ad_strategies_count=int(ads_count),
        recent_analyses=recent_analyses,
        sentiment_history=sentiment_history,
        content_performance_mix=content_mix,
        integrations={
            "ai_configured": settings.has_ai_key,
            "gemini_configured": settings.has_gemini_key,
            "openai_configured": settings.has_openai_key,
            "youtube_api_configured": settings.has_youtube_api_key,
            "google_oauth_configured": settings.has_google_oauth,
            "ffmpeg_available": is_ffmpeg_available(),
            "allow_demo_mode": settings.ALLOW_DEMO_MODE,
            "llm_provider": settings.LLM_PROVIDER,
            "llm_model": settings.active_llm_model,
        },
    )


@router.get("/activity", response_model=DashboardActivityResponse)
def get_dashboard_activity(
    record_type: str | None = Query(default=None),
    limit: int = Query(default=40, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(CampaignRecord).filter(CampaignRecord.user_id == current_user.id)
    if record_type:
        q = q.filter(CampaignRecord.record_type == record_type)

    total = q.count()
    items = (
        q.order_by(desc(CampaignRecord.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return DashboardActivityResponse(
        items=[CampaignRecordResponse.model_validate(i) for i in items],
        total=total,
    )


@router.delete("/activity/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dashboard_activity_record(
    record_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(CampaignRecord)
        .filter(CampaignRecord.id == record_id, CampaignRecord.user_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Campaign history record not found.")
    db.delete(row)
    db.commit()
    return None


@router.delete("/activity", status_code=status.HTTP_204_NO_CONTENT)
def clear_dashboard_activity_history(
    record_type: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(CampaignRecord).filter(CampaignRecord.user_id == current_user.id)
    if record_type:
        q = q.filter(CampaignRecord.record_type == record_type)
    for row in q.all():
        db.delete(row)
    db.commit()
    return None

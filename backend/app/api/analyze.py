"""YouTube Video Sentiment Analysis & Audience Intelligence endpoints."""
from __future__ import annotations

import os
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.analysis import (
    AudienceInsight,
    Comment,
    CommentSentimentResult,
    VideoAnalysis,
    YouTubeVideo,
)
from app.models.reporting import PDFReport
from app.models.user import User
from app.schemas.analysis import (
    AnalyzeRequest,
    AudienceInsightResponse,
    CommentItemResponse,
    PaginatedCommentsResponse,
    VideoAnalysisResponse,
)
from app.tasks.analysis_tasks import run_youtube_analysis_task
from app.utils.youtube_url import canonical_youtube_url, extract_youtube_video_id

router = APIRouter(prefix="/analyze", tags=["YouTube Analysis"])


@router.post("", response_model=VideoAnalysisResponse, status_code=status.HTTP_202_ACCEPTED)
def start_youtube_analysis(
    payload: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        yt_video_id = extract_youtube_video_id(payload.youtube_url)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    settings = get_settings()
    if not settings.has_youtube_api_key and not (settings.ALLOW_DEMO_MODE and payload.use_demo_fallback):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "YOUTUBE_API_KEY is not configured on the backend. Add YOUTUBE_API_KEY in .env "
                "to analyze live videos, or toggle 'Development Demo Mode' to test with visibly labeled demo data."
            ),
        )

    video = YouTubeVideo(
        user_id=current_user.id,
        youtube_video_id=yt_video_id,
        url=canonical_youtube_url(yt_video_id),
        title=f"Loading video {yt_video_id}...",
        thumbnail_url=f"https://img.youtube.com/vi/{yt_video_id}/hqdefault.jpg",
        is_demo_data=not settings.has_youtube_api_key and payload.use_demo_fallback,
    )
    db.add(video)
    db.flush()

    analysis = VideoAnalysis(
        user_id=current_user.id,
        video_id=video.id,
        status="pending",
        progress_pct=5,
        status_message="Queued for comment collection & AI analysis...",
        requested_max_comments=min(payload.max_comments, settings.ANALYSIS_MAX_COMMENTS),
        is_demo_data=not settings.has_youtube_api_key and payload.use_demo_fallback,
    )
    db.add(analysis)
    db.commit()

    background_tasks.add_task(
        run_youtube_analysis_task,
        analysis.id,
        payload.use_demo_fallback,
    )

    hydrated = (
        db.query(VideoAnalysis)
        .options(joinedload(VideoAnalysis.video))
        .filter(VideoAnalysis.id == analysis.id)
        .first()
    )
    return VideoAnalysisResponse.model_validate(hydrated)


@router.get("", response_model=List[VideoAnalysisResponse])
def list_analyses(
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(VideoAnalysis)
        .options(joinedload(VideoAnalysis.video))
        .filter(VideoAnalysis.user_id == current_user.id)
        .order_by(desc(VideoAnalysis.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [VideoAnalysisResponse.model_validate(r) for r in rows]


@router.get("/{analysis_id}", response_model=VideoAnalysisResponse)
def get_analysis(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(VideoAnalysis)
        .options(joinedload(VideoAnalysis.video))
        .filter(VideoAnalysis.id == analysis_id, VideoAnalysis.user_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return VideoAnalysisResponse.model_validate(row)


@router.get("/{analysis_id}/comments", response_model=PaginatedCommentsResponse)
def get_analysis_comments(
    analysis_id: str,
    sentiment: Optional[str] = Query(default=None, pattern="^(positive|negative|neutral)$"),
    emotion: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = (
        db.query(VideoAnalysis)
        .filter(VideoAnalysis.id == analysis_id, VideoAnalysis.user_id == current_user.id)
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    query = (
        db.query(Comment, CommentSentimentResult)
        .join(CommentSentimentResult, CommentSentimentResult.comment_id == Comment.id)
        .filter(Comment.analysis_id == analysis_id)
    )
    if sentiment:
        query = query.filter(CommentSentimentResult.sentiment == sentiment)
    if emotion:
        query = query.filter(CommentSentimentResult.primary_emotion == emotion.lower())
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        query = query.filter(Comment.text_sanitized.ilike(pattern))

    total = query.count()
    rows = (
        query.order_by(desc(Comment.like_count), desc(Comment.published_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        CommentItemResponse(
            id=c.id,
            youtube_comment_id=c.youtube_comment_id,
            author_display_name=c.author_display_name,
            text=c.text_sanitized,
            like_count=c.like_count,
            reply_count=c.reply_count,
            published_at=c.published_at,
            sentiment=sr.sentiment,
            confidence=sr.confidence,
            primary_emotion=sr.primary_emotion,
            secondary_emotions=sr.secondary_emotions_json or [],
            purchase_intent=sr.purchase_intent,
            is_complaint=sr.is_complaint,
            is_feature_request=sr.is_feature_request,
            is_question=sr.is_question,
            topics=sr.topics_json or [],
            keywords=sr.keywords_json or [],
        )
        for c, sr in rows
    ]

    return PaginatedCommentsResponse(
        analysis_id=analysis.id,
        total=total,
        page=page,
        page_size=page_size,
        ai_disclaimer=analysis.ai_disclaimer,
        items=items,
    )


@router.get("/{analysis_id}/insights", response_model=AudienceInsightResponse)
def get_analysis_insights(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    insight = (
        db.query(AudienceInsight)
        .filter(
            AudienceInsight.analysis_id == analysis_id,
            AudienceInsight.user_id == current_user.id,
        )
        .first()
    )
    if not insight:
        raise HTTPException(
            status_code=404,
            detail="Audience intelligence insights are not yet available for this analysis.",
        )
    return AudienceInsightResponse.model_validate(insight)


def _delete_analysis_record(db: Session, analysis: VideoAnalysis) -> None:
    linked_reports = db.query(PDFReport).filter(PDFReport.analysis_id == analysis.id).all()
    for rep in linked_reports:
        if rep.file_path and os.path.exists(rep.file_path):
            try:
                os.unlink(rep.file_path)
            except OSError:
                pass
    video_id = analysis.video_id
    db.delete(analysis)
    db.flush()
    remaining = db.query(VideoAnalysis).filter(VideoAnalysis.video_id == video_id).count()
    if remaining == 0:
        video = db.query(YouTubeVideo).filter(YouTubeVideo.id == video_id).first()
        if video:
            db.delete(video)


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(VideoAnalysis)
        .filter(VideoAnalysis.id == analysis_id, VideoAnalysis.user_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    _delete_analysis_record(db, row)
    db.commit()
    return None


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_analyses_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(VideoAnalysis).filter(VideoAnalysis.user_id == current_user.id).all()
    for row in rows:
        _delete_analysis_record(db, row)
    db.commit()
    return None

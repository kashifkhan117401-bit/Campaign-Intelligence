"""YouTube video, sentiment analysis, comments, and audience intelligence models."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid, utcnow


class YouTubeVideo(Base, TimestampMixin):
    __tablename__ = "youtube_videos"
    __table_args__ = (Index("ix_yt_videos_user_ytid", "user_id", "youtube_video_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    youtube_video_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    channel_id: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    channel_title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_iso: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tags_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    category_id: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    comments_disabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_demo_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    analyses: Mapped[List["VideoAnalysis"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )


class VideoAnalysis(Base, TimestampMixin):
    __tablename__ = "video_analyses"
    __table_args__ = (Index("ix_video_analyses_user_status", "user_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    video_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("youtube_videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status_message: Mapped[str] = mapped_column(String(300), default="Queued for analysis", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    requested_max_comments: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    collected_comments_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    analyzed_comments_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    positive_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    negative_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    neutral_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    positive_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    negative_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    neutral_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    emotion_distribution_json: Mapped[Dict[str, int]] = mapped_column(JSON, default=dict, nullable=False)
    topics_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    keywords_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    pain_points_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    complaints_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    feature_requests_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    faqs_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    buying_objections_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    suggestions_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    emerging_topics_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    sentiment_trends_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    is_demo_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_disclaimer: Mapped[str] = mapped_column(
        Text,
        default=(
            "Sentiment, emotion, and topic classifications are AI-generated from collected "
            "public comments and may contain classification errors or nuance omissions."
        ),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    video: Mapped["YouTubeVideo"] = relationship(back_populates="analyses")
    comments: Mapped[List["Comment"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    insight: Mapped[Optional["AudienceInsight"]] = relationship(
        back_populates="analysis", uselist=False, cascade="all, delete-orphan"
    )


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        Index("ix_comments_analysis_published", "analysis_id", "published_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("video_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    youtube_comment_id: Mapped[str] = mapped_column(String(128), nullable=False)
    author_display_name: Mapped[str] = mapped_column(String(200), default="Anonymous", nullable=False)
    text_original: Mapped[str] = mapped_column(Text, nullable=False)
    text_sanitized: Mapped[str] = mapped_column(Text, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reply_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    analysis: Mapped["VideoAnalysis"] = relationship(back_populates="comments")
    sentiment_result: Mapped[Optional["CommentSentimentResult"]] = relationship(
        back_populates="comment", uselist=False, cascade="all, delete-orphan"
    )


class CommentSentimentResult(Base):
    __tablename__ = "comment_sentiment_results"
    __table_args__ = (
        Index("ix_csr_analysis_sentiment", "analysis_id", "sentiment"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    comment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("comments.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("video_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sentiment: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.75, nullable=False)
    primary_emotion: Mapped[str] = mapped_column(String(40), default="satisfaction", nullable=False)
    secondary_emotions_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    purchase_intent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_complaint: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_feature_request: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_question: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    topics_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    keywords_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    comment: Mapped["Comment"] = relationship(back_populates="sentiment_result")


class AudienceInsight(Base, TimestampMixin):
    __tablename__ = "audience_insights"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("video_analyses.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    interests_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    expectations_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    common_problems_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    unanswered_questions_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    agreement_reasons_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    disagreement_reasons_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    main_frustrations_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    content_gaps_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    product_opportunities_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    customer_objections_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    marketing_angles_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    top_10_questions_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    opportunity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    opportunity_score_breakdown_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    opportunity_formula_doc: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_demo_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    analysis: Mapped["VideoAnalysis"] = relationship(back_populates="insight")

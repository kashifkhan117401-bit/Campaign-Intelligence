"""Generated content, uploaded video media, and YouTube publishing job models."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class GeneratedContent(Base, TimestampMixin):
    __tablename__ = "generated_content"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("video_analyses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    tone: Mapped[str] = mapped_column(String(40), default="Professional", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    topic_brief: Mapped[str] = mapped_column(Text, default="", nullable=False)

    youtube_content_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    seo_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    social_media_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    content_strategy_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    disclaimer: Mapped[str] = mapped_column(
        Text,
        default=(
            "Generated titles, keywords, and hashtags are AI suggestions based on audience signals "
            "and are not guaranteed to rank or trend on YouTube."
        ),
        nullable=False,
    )
    is_demo_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class UploadedMedia(Base, TimestampMixin):
    __tablename__ = "uploaded_media"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    width: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    height: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    frame_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    audio_codec: Mapped[str] = mapped_column(String(60), default="unknown", nullable=False)
    audio_channels: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    audio_sample_rate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_source: Mapped[str] = mapped_column(String(40), default="ffprobe", nullable=False)

    frames_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    transcript_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    transcript_segments_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    content_analysis_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    generated_metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    analysis_status: Mapped[str] = mapped_column(String(32), default="uploaded", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_demo_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class PublishingJob(Base, TimestampMixin):
    __tablename__ = "publishing_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    media_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("uploaded_media.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("connected_youtube_channels.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    privacy_status: Mapped[str] = mapped_column(String(20), default="private", nullable=False)
    scheduled_publish_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tags_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    category_id: Mapped[str] = mapped_column(String(20), default="22", nullable=False)
    pinned_comment: Mapped[str] = mapped_column(Text, default="", nullable=False)

    upload_progress_pct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bytes_uploaded: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    youtube_video_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    youtube_video_url: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    user_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    api_response_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

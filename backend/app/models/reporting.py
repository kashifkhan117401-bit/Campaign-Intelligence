"""PDF reports, campaign history records, and API usage audit logs."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid, utcnow


class PDFReport(Base, TimestampMixin):
    __tablename__ = "pdf_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("video_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("generated_content.id", ondelete="SET NULL"), nullable=True
    )
    strategy_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("advertising_strategies.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ready", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class CampaignRecord(Base, TimestampMixin):
    __tablename__ = "campaign_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("video_analyses.id", ondelete="SET NULL"), nullable=True
    )
    content_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("generated_content.id", ondelete="SET NULL"), nullable=True
    )
    strategy_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("advertising_strategies.id", ondelete="SET NULL"), nullable=True
    )
    publishing_job_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("publishing_jobs.id", ondelete="SET NULL"), nullable=True
    )
    report_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("pdf_reports.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    record_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="completed", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class APIUsageLog(Base):
    __tablename__ = "api_usage_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(String(200), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    units_used: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

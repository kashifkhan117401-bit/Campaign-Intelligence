"""Advertising strategy and budget estimate models."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid, utcnow


class AdvertisingStrategy(Base, TimestampMixin):
    __tablename__ = "advertising_strategies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("video_analyses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    media_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("uploaded_media.id", ondelete="SET NULL"), nullable=True
    )

    campaign_name: Mapped[str] = mapped_column(String(200), nullable=False)
    video_context: Mapped[str] = mapped_column(Text, default="", nullable=False)
    target_country: Mapped[str] = mapped_column(String(100), nullable=False)
    target_audience: Mapped[str] = mapped_column(String(300), nullable=False)
    industry_niche: Mapped[str] = mapped_column(String(150), nullable=False)
    marketing_objective: Mapped[str] = mapped_column(String(80), nullable=False)
    campaign_duration_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    available_budget: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)

    recommended_objective: Mapped[str] = mapped_column(String(150), default="", nullable=False)
    audience_segments_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    geographic_targeting_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    audience_interests_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    campaign_type_and_format: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    placement_strategy_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    suggested_daily_budget: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    suggested_total_budget: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    creative_recommendations_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    ab_testing_ideas_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    optimization_strategy_json: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    executive_report: Mapped[str] = mapped_column(Text, default="", nullable=False)
    disclaimer: Mapped[str] = mapped_column(
        Text,
        default=(
            "Illustrative estimates based on configurable benchmark assumptions — not live "
            "Google Ads forecasts or guaranteed performance results."
        ),
        nullable=False,
    )
    is_demo_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    budget_estimates: Mapped[List["BudgetEstimate"]] = relationship(
        back_populates="strategy", cascade="all, delete-orphan"
    )


class BudgetEstimate(Base):
    __tablename__ = "budget_estimates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    strategy_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("advertising_strategies.id", ondelete="CASCADE"), nullable=True, index=True
    )
    tier: Mapped[str] = mapped_column(String(32), nullable=False)  # low, balanced, aggressive
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    campaign_duration_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    daily_budget: Mapped[float] = mapped_column(Float, nullable=False)
    total_budget: Mapped[float] = mapped_column(Float, nullable=False)
    assumed_cpv: Mapped[float] = mapped_column(Float, nullable=False)
    assumed_cpm: Mapped[float] = mapped_column(Float, nullable=False)
    assumed_ctr: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_reach: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assumptions_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    disclaimer: Mapped[str] = mapped_column(
        Text,
        default="Illustrative estimate derived from benchmark assumptions; actual Google Ads costs vary.",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    strategy: Mapped[Optional["AdvertisingStrategy"]] = relationship(back_populates="budget_estimates")

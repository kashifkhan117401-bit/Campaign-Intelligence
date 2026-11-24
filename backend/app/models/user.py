"""User, profile, refresh token, settings, and connected YouTube channel models."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid, utcnow


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reset_token_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    reset_token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    profile: Mapped[Optional["UserProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    settings: Mapped[Optional["UserSettings"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    youtube_channels: Mapped[List["ConnectedYouTubeChannel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(150), default="", nullable=False)
    company_name: Mapped[str] = mapped_column(String(150), default="", nullable=False)
    job_title: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    avatar_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    bio: Mapped[str] = mapped_column(Text, default="", nullable=False)
    niche: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    primary_goal: Mapped[str] = mapped_column(String(150), default="", nullable=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="profile")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class UserSettings(Base, TimestampMixin):
    __tablename__ = "user_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    default_tone: Mapped[str] = mapped_column(String(40), default="Professional", nullable=False)
    default_currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    preferred_llm_model: Mapped[str] = mapped_column(String(80), default="gemini-2.5-flash", nullable=False)
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    demo_mode_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    benchmark_cpv: Mapped[float] = mapped_column(Float, default=0.035, nullable=False)
    benchmark_cpm: Mapped[float] = mapped_column(Float, default=8.50, nullable=False)
    benchmark_ctr: Mapped[float] = mapped_column(Float, default=0.012, nullable=False)

    user: Mapped["User"] = relationship(back_populates="settings")


class ConnectedYouTubeChannel(Base, TimestampMixin):
    __tablename__ = "connected_youtube_channels"
    __table_args__ = (
        Index("ix_connected_yt_user_channel", "user_id", "channel_id", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_id: Mapped[str] = mapped_column(String(128), nullable=False)
    channel_title: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_thumbnail: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    subscriber_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    encrypted_access_token: Mapped[str] = mapped_column(Text, default="", nullable=False)
    encrypted_refresh_token: Mapped[str] = mapped_column(Text, default="", nullable=False)
    token_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_demo_connection: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="youtube_channels")

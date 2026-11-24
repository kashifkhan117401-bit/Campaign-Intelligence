"""Authentication, profile, and settings Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class CaptchaResponse(BaseModel):
    captcha_token: str
    image_data_url: str
    expires_in: int


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=150)
    company_name: str = Field(default="", max_length=150)
    captcha_token: Optional[str] = None
    captcha_answer: Optional[str] = Field(default=None, max_length=16)
    accepted_terms: bool = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    captcha_token: Optional[str] = None
    captcha_answer: Optional[str] = Field(default=None, max_length=16)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class DeleteAccountRequest(BaseModel):
    password: str
    confirm_text: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UserProfileResponse(BaseModel):
    full_name: str
    company_name: str
    job_title: str
    avatar_url: str
    bio: str
    niche: str
    primary_goal: str
    onboarding_completed: bool

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=150)
    company_name: Optional[str] = Field(default=None, max_length=150)
    job_title: Optional[str] = Field(default=None, max_length=120)
    avatar_url: Optional[str] = Field(default=None, max_length=500)
    bio: Optional[str] = Field(default=None, max_length=2000)
    niche: Optional[str] = Field(default=None, max_length=120)
    primary_goal: Optional[str] = Field(default=None, max_length=150)
    onboarding_completed: Optional[bool] = None


class UserSettingsResponse(BaseModel):
    default_tone: str
    default_currency: str
    preferred_llm_model: str
    email_notifications: bool
    demo_mode_enabled: bool
    benchmark_cpv: float
    benchmark_cpm: float
    benchmark_ctr: float

    model_config = {"from_attributes": True}


class UserSettingsUpdate(BaseModel):
    default_tone: Optional[str] = None
    default_currency: Optional[str] = None
    preferred_llm_model: Optional[str] = None
    email_notifications: Optional[bool] = None
    demo_mode_enabled: Optional[bool] = None
    benchmark_cpv: Optional[float] = Field(default=None, gt=0.001, le=5.0)
    benchmark_cpm: Optional[float] = Field(default=None, gt=0.1, le=200.0)
    benchmark_ctr: Optional[float] = Field(default=None, gt=0.0005, le=0.5)


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    profile: Optional[UserProfileResponse] = None
    settings: Optional[UserSettingsResponse] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class IntegrationStatusResponse(BaseModel):
    ai_configured: bool
    gemini_configured: bool
    openai_configured: bool
    youtube_api_configured: bool
    google_oauth_configured: bool
    ffmpeg_available: bool
    allow_demo_mode: bool
    llm_provider: str
    llm_model: str

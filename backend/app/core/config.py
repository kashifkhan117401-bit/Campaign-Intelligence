"""Core application configuration loaded from environment variables."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_BACKEND_DIR = Path(__file__).resolve().parents[2]
_ROOT_DIR = _BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_ROOT_DIR / ".env", _BACKEND_DIR / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Campaign Intelligence"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api"
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # Security & JWT
    SECRET_KEY: str = "tubemind-dev-secret-key-change-in-production-32chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CAPTCHA_ENABLED: bool = True
    OAUTH_ENCRYPTION_KEY: str = ""

    # Database
    DATABASE_URL: str = "sqlite:///./tubemind.db"

    # AI / LLM
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_BASE_URL: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_BASE_URL: str = ""
    TRANSCRIPTION_PROVIDER: str = "gemini"
    WHISPER_MODEL: str = "whisper-1"

    # YouTube & Google OAuth
    YOUTUBE_API_KEY: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_OAUTH_REDIRECT_URI: str = "http://localhost:8000/api/youtube/callback"

    # Demo Mode
    ALLOW_DEMO_MODE: bool = True

    # Storage
    UPLOAD_DIR: str = "./storage/uploads"
    REPORTS_DIR: str = "./storage/reports"
    FRAMES_DIR: str = "./storage/frames"
    MAX_VIDEO_UPLOAD_MB: int = 500

    # Rate limits & analysis settings
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 120
    ANALYSIS_MAX_COMMENTS: int = 2000
    ANALYSIS_BATCH_SIZE: int = 50

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: object) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, list):
            return [str(o) for o in v]
        return ["http://localhost:5173"]

    @property
    def has_gemini_key(self) -> bool:
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip())

    @property
    def has_openai_key(self) -> bool:
        return bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY.strip())

    @property
    def active_llm_model(self) -> str:
        provider = self.LLM_PROVIDER.lower().strip()
        if provider in ("openai", "openai_compatible", "custom"):
            return self.OPENAI_MODEL
        return self.GEMINI_MODEL

    @property
    def has_ai_key(self) -> bool:
        provider = self.LLM_PROVIDER.lower().strip()
        if provider in ("openai", "openai_compatible", "custom"):
            return self.has_openai_key
        return self.has_gemini_key

    @property
    def has_youtube_api_key(self) -> bool:
        return bool(self.YOUTUBE_API_KEY and self.YOUTUBE_API_KEY.strip())

    @property
    def has_google_oauth(self) -> bool:
        return bool(
            self.GOOGLE_CLIENT_ID
            and self.GOOGLE_CLIENT_ID.strip()
            and self.GOOGLE_CLIENT_SECRET
            and self.GOOGLE_CLIENT_SECRET.strip()
        )

    def ensure_storage_dirs(self) -> None:
        for d in (self.UPLOAD_DIR, self.REPORTS_DIR, self.FRAMES_DIR):
            Path(d).mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_storage_dirs()
    return settings

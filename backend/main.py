"""Top-level FastAPI entrypoint for Vercel Services (`entrypoint: main:app`)."""
from __future__ import annotations

import app.models  # noqa: F401 - register SQLAlchemy models
from app.core.config import get_settings
from app.core.database import Base, engine
from app.main import app  # noqa: F401 - exported for ASGI runtimes

_settings = get_settings()
_settings.ensure_storage_dirs()
Base.metadata.create_all(bind=engine)

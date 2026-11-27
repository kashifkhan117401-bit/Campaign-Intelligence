"""Vercel Python Serverless Function entrypoint exposing the FastAPI ASGI app."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.models  # noqa: E402, F401 - register SQLAlchemy models
from app.core.config import get_settings  # noqa: E402
from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402, F401 - exported for Vercel Python runtime

_settings = get_settings()
_settings.ensure_storage_dirs()
Base.metadata.create_all(bind=engine)

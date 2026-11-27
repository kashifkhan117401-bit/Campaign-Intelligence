"""SQLAlchemy 2.0 PostgreSQL database engine, session management, and Base declaration."""
from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _build_engine() -> Engine:
    settings = get_settings()
    url = settings.DATABASE_URL
    if not url.startswith("postgresql"):
        raise RuntimeError(
            "PostgreSQL is required. Set DATABASE_URL to your PostgreSQL connection string (e.g. Neon or Supabase)."
        )

    engine_kwargs: dict = {"pool_pre_ping": True}
    if settings.is_vercel:
        # Serverless functions should not hold long-lived connection pools
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20

    return create_engine(url, **engine_kwargs)


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

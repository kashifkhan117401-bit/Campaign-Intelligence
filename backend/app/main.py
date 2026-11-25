"""Campaign Intelligence FastAPI application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import app.models  # noqa: F401 - register all SQLAlchemy models
from app.api import ads, analyze, auth, content, dashboard, reports, videos, youtube
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.logging_config import configure_logging
from app.core.rate_limit import RateLimitMiddleware
from app.services.upload_scheduler import upload_scheduler

settings = get_settings()
configure_logging(debug=settings.DEBUG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.ensure_storage_dirs()
    Base.metadata.create_all(bind=engine)
    upload_scheduler.start()
    logger.info("Campaign Intelligence backend started (env=%s)", settings.APP_ENV)
    yield
    await upload_scheduler.stop()
    logger.info("Campaign Intelligence backend shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "AI-powered YouTube Marketing Intelligence, Audience Sentiment Analysis, "
        "SEO Content Automation, Video Publishing Studio, Advertising Strategy Planner, "
        "and ReportLab PDF Intelligence Platform."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    logger.exception("Unhandled server exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please check server logs."},
    )


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.APP_ENV,
    }


prefix = settings.API_V1_PREFIX
app.include_router(auth.router, prefix=prefix)
app.include_router(analyze.router, prefix=prefix)
app.include_router(content.router, prefix=prefix)
app.include_router(videos.router, prefix=prefix)
app.include_router(youtube.router, prefix=prefix)
app.include_router(ads.router, prefix=prefix)
app.include_router(reports.router, prefix=prefix)
app.include_router(dashboard.router, prefix=prefix)

# Serve built React SPA when frontend/dist exists (single-origin production deploy, e.g. PythonAnywhere)
_FRONTEND_DIST = Path(__file__).resolve().parents[2].parent / "frontend" / "dist"
if (_FRONTEND_DIST / "index.html").is_file():
    _ASSETS_DIR = _FRONTEND_DIST / "assets"
    if _ASSETS_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_ASSETS_DIR)), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend_spa(full_path: str):
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404, detail="API endpoint not found.")
        candidate = (_FRONTEND_DIST / full_path).resolve()
        if (
            full_path
            and str(candidate).startswith(str(_FRONTEND_DIST.resolve()))
            and candidate.is_file()
        ):
            return FileResponse(str(candidate))
        return FileResponse(str(_FRONTEND_DIST / "index.html"))

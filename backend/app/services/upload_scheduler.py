"""Background scheduler that automatically triggers YouTube uploads when scheduled times arrive."""
from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime, timezone
from typing import Callable, List, Optional

from app.core.database import SessionLocal
from app.models.content import PublishingJob
from app.tasks.analysis_tasks import run_youtube_publish_task

logger = logging.getLogger(__name__)


def as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalize naive or aware datetime to timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _dispatch_in_thread(job_id: str) -> None:
    thread = threading.Thread(
        target=run_youtube_publish_task,
        args=(job_id, True),
        name=f"yt-auto-upload-{job_id[:8]}",
        daemon=True,
    )
    thread.start()


def process_due_scheduled_uploads(
    *,
    now: Optional[datetime] = None,
    dispatch_fn: Callable[[str], None] = _dispatch_in_thread,
) -> List[str]:
    """Find confirmed scheduled_upload jobs whose scheduled time has been reached and launch them."""
    current_time = as_utc(now) or datetime.now(timezone.utc)
    due_ids: List[str] = []

    db = SessionLocal()
    try:
        candidates = (
            db.query(PublishingJob)
            .filter(
                PublishingJob.status == "scheduled_upload",
                PublishingJob.user_confirmed.is_(True),
                PublishingJob.scheduled_publish_at.is_not(None),
            )
            .all()
        )
        for job in candidates:
            sched_at = as_utc(job.scheduled_publish_at)
            if sched_at and sched_at <= current_time:
                job.status = "queued"
                job.error_message = None
                due_ids.append(job.id)
        if due_ids:
            db.commit()
    except Exception as exc:
        logger.exception("Scheduled upload poll failed: %s", exc)
        db.rollback()
        return []
    finally:
        db.close()

    for job_id in due_ids:
        logger.info("Scheduled upload time reached for job %s; starting automatic YouTube upload.", job_id)
        dispatch_fn(job_id)

    return due_ids


class ScheduledUploadWorker:
    """Async background loop running inside FastAPI lifespan to dispatch due YouTube uploads."""

    def __init__(self, poll_interval_seconds: float = 3.0):
        self.poll_interval_seconds = poll_interval_seconds
        self._stop_event: Optional[asyncio.Event] = None
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop(), name="youtube-upload-scheduler")
        logger.info("YouTube scheduled auto-upload worker started (poll=%ss).", self.poll_interval_seconds)

    async def stop(self) -> None:
        if self._stop_event:
            self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("YouTube scheduled auto-upload worker stopped.")

    async def _run_loop(self) -> None:
        assert self._stop_event is not None
        while not self._stop_event.is_set():
            try:
                await asyncio.to_thread(process_due_scheduled_uploads)
            except Exception as exc:
                logger.exception("Unexpected error in scheduled upload worker loop: %s", exc)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval_seconds)
            except asyncio.TimeoutError:
                continue


upload_scheduler = ScheduledUploadWorker(poll_interval_seconds=3.0)

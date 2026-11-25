"""Standalone runner for scheduled automatic YouTube uploads (for PythonAnywhere Tasks).

Usage:
  # Run once (for PythonAnywhere Scheduled Task / cron):
  python backend/run_upload_scheduler.py --once

  # Run continuously (for PythonAnywhere Always-on Task):
  python backend/run_upload_scheduler.py --loop --interval 5
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

os.chdir(str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.core.logging_config import configure_logging  # noqa: E402
from app.services.upload_scheduler import process_due_scheduled_uploads  # noqa: E402
from app.tasks.analysis_tasks import run_youtube_publish_task  # noqa: E402

logger = logging.getLogger(__name__)


def _run_sync(job_id: str) -> None:
    run_youtube_publish_task(job_id, is_scheduled_auto_upload=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process due scheduled YouTube uploads.")
    parser.add_argument("--once", action="store_true", help="Process due jobs once and exit.")
    parser.add_argument("--loop", action="store_true", help="Poll continuously (for Always-on Tasks).")
    parser.add_argument("--interval", type=float, default=5.0, help="Poll interval in seconds for --loop.")
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(debug=settings.DEBUG)
    settings.ensure_storage_dirs()

    if args.loop and not args.once:
        logger.info("Starting continuous YouTube auto-upload scheduler (interval=%ss)...", args.interval)
        while True:
            triggered = process_due_scheduled_uploads(dispatch_fn=_run_sync)
            if triggered:
                logger.info("Processed %d scheduled YouTube upload(s).", len(triggered))
            time.sleep(max(1.0, args.interval))
    else:
        triggered = process_due_scheduled_uploads(dispatch_fn=_run_sync)
        logger.info("Checked scheduled uploads; processed %d due job(s).", len(triggered))


if __name__ == "__main__":
    main()

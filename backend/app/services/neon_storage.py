"""Neon Object Storage helpers proxied cleanly via the branch's Neon Function."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from pathlib import Path
from typing import Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

NEON_S3_PREFIX = "neon-s3://videos/"


def is_neon_s3_path(file_path: Optional[str]) -> bool:
    return bool(file_path and file_path.startswith(NEON_S3_PREFIX))


def extract_object_key(file_path: str) -> str:
    return file_path[len(NEON_S3_PREFIX) :]


def _sign_hmac(message: str) -> str:
    settings = get_settings()
    secret = settings.NEON_REALTIME_SECRET.strip()
    if not secret:
        raise RuntimeError("NEON_REALTIME_SECRET is required to sign Neon storage requests.")
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def can_use_neon_storage_upload() -> bool:
    settings = get_settings()
    return bool(settings.has_neon_functions and settings.NEON_REALTIME_SECRET.strip())


def mint_upload_token(user_id: str, object_key: str, ttl_seconds: int = 900) -> str:
    payload = {
        "user_id": user_id,
        "object_key": object_key,
        "exp": int(time.time()) + ttl_seconds,
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    sig = _sign_hmac(f"upload:{payload_b64}")
    return f"{payload_b64}.{sig}"


def ensure_local_video_file(file_path: str, stored_filename: str) -> str:
    """Return a local filesystem path to the video, downloading from Neon Object Storage if needed."""
    if not is_neon_s3_path(file_path):
        return file_path

    settings = get_settings()
    local_dir = Path(settings.UPLOAD_DIR)
    local_dir.mkdir(parents=True, exist_ok=True)
    local_path = local_dir / stored_filename
    if local_path.is_file() and local_path.stat().st_size > 0:
        return str(local_path)

    fn_url = settings.neon_function_url("hello")
    if not fn_url:
        raise RuntimeError("Neon Function URL is not configured to download stored video.")

    object_key = extract_object_key(file_path)
    sig = _sign_hmac(f"download:{object_key}")
    with httpx.Client(timeout=180.0) as client:
        with client.stream(
            "GET",
            f"{fn_url}/storage/download",
            params={"key": object_key},
            headers={"X-Server-Signature": sig},
        ) as resp:
            resp.raise_for_status()
            with open(local_path, "wb") as out:
                for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                    out.write(chunk)
    return str(local_path)


def delete_remote_video_object(file_path: Optional[str]) -> None:
    if not is_neon_s3_path(file_path) or not file_path:
        return
    settings = get_settings()
    fn_url = settings.neon_function_url("hello")
    if not fn_url or not settings.NEON_REALTIME_SECRET.strip():
        return
    object_key = extract_object_key(file_path)
    try:
        sig = _sign_hmac(f"delete:{object_key}")
        with httpx.Client(timeout=15.0) as client:
            client.delete(
                f"{fn_url}/storage/object",
                params={"key": object_key},
                headers={"X-Server-Signature": sig},
            )
    except Exception as exc:
        logger.warning("Failed to delete remote Neon Object Storage file %s: %s", object_key, exc)

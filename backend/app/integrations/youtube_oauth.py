"""Google OAuth 2.0 & YouTube Data API v3 resumable video upload client."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings
from app.core.security import decrypt_secret, encrypt_secret

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


class YouTubeOAuthError(Exception):
    def __init__(self, message: str, code: str = "oauth_error", status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


def build_oauth_authorization_url(state: str) -> str:
    settings = get_settings()
    if not settings.has_google_oauth:
        raise YouTubeOAuthError(
            "Google OAuth 2.0 is not configured. Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, "
            "and GOOGLE_OAUTH_REDIRECT_URI in your .env file.",
            code="missing_oauth_config",
            status_code=503,
        )

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(YOUTUBE_OAUTH_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_tokens(code: str) -> Dict[str, Any]:
    settings = get_settings()
    if not settings.has_google_oauth:
        raise YouTubeOAuthError(
            "Google OAuth 2.0 credentials are missing from server configuration.",
            code="missing_oauth_config",
            status_code=503,
        )

    with httpx.Client(timeout=20.0) as client:
        resp = client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
    if resp.status_code != 200:
        raise YouTubeOAuthError(
            f"Google OAuth token exchange failed ({resp.status_code}): {resp.text[:300]}",
            code="token_exchange_failed",
            status_code=400,
        )

    data = resp.json()
    expires_in = int(data.get("expires_in", 3600))
    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", ""),
        "expires_at": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        "scope": data.get("scope", " ".join(YOUTUBE_OAUTH_SCOPES)),
    }


def refresh_access_token(encrypted_refresh_token: str) -> Dict[str, Any]:
    settings = get_settings()
    refresh_token = decrypt_secret(encrypted_refresh_token)
    if not refresh_token:
        raise YouTubeOAuthError(
            "No refresh token is stored for this YouTube channel. Please reconnect your channel.",
            code="missing_refresh_token",
            status_code=401,
        )
    with httpx.Client(timeout=20.0) as client:
        resp = client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
    if resp.status_code != 200:
        raise YouTubeOAuthError(
            "Failed to refresh YouTube OAuth token. Please reconnect your Google account.",
            code="token_refresh_failed",
            status_code=401,
        )
    data = resp.json()
    expires_in = int(data.get("expires_in", 3600))
    return {
        "access_token": data["access_token"],
        "encrypted_access_token": encrypt_secret(data["access_token"]),
        "expires_at": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
    }


def fetch_authenticated_channel(access_token: str) -> Dict[str, Any]:
    with httpx.Client(timeout=20.0) as client:
        resp = client.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "snippet,statistics", "mine": "true"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if resp.status_code != 200:
        raise YouTubeOAuthError(
            f"Unable to fetch YouTube channel profile ({resp.status_code}). Ensure YouTube Data API v3 is enabled.",
            code="channel_fetch_failed",
            status_code=resp.status_code,
        )
    items = resp.json().get("items", [])
    if not items:
        raise YouTubeOAuthError(
            "The authorized Google account does not have an active YouTube channel.",
            code="no_channel_found",
            status_code=404,
        )
    ch = items[0]
    snippet = ch.get("snippet", {})
    stats = ch.get("statistics", {})
    thumbs = snippet.get("thumbnails", {})
    return {
        "channel_id": ch["id"],
        "channel_title": snippet.get("title", "YouTube Channel"),
        "channel_thumbnail": thumbs.get("default", {}).get("url", ""),
        "subscriber_count": int(stats.get("subscriberCount", 0) or 0),
    }


def upload_video_to_youtube(
    *,
    access_token: str,
    file_path: str,
    mime_type: str,
    title: str,
    description: str,
    tags: List[str],
    category_id: str,
    privacy_status: str,
    scheduled_publish_at: Optional[datetime] = None,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, Any]:
    """Upload a video via the official Google API Python client using resumable chunked upload.

    Never claims success without an actual API response containing the uploaded video ID.
    """
    if not os.path.exists(file_path):
        raise YouTubeOAuthError(
            "Uploaded media file could not be located on server storage.",
            code="file_not_found",
            status_code=404,
        )

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload
    except ImportError as exc:
        raise YouTubeOAuthError(
            f"Google API client libraries are not installed: {exc}",
            code="missing_dependency",
            status_code=500,
        ) from exc

    creds = Credentials(token=access_token)
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    status_body: Dict[str, Any] = {
        "privacyStatus": "private" if scheduled_publish_at else privacy_status,
        "selfDeclaredMadeForKids": False,
    }
    if scheduled_publish_at:
        sched_utc = (
            scheduled_publish_at.replace(tzinfo=timezone.utc)
            if scheduled_publish_at.tzinfo is None
            else scheduled_publish_at.astimezone(timezone.utc)
        )
        status_body["publishAt"] = sched_utc.isoformat()

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:30],
            "categoryId": category_id or "22",
        },
        "status": status_body,
    }

    file_size = os.path.getsize(file_path)
    media = MediaFileUpload(
        file_path,
        mimetype=mime_type or "video/mp4",
        chunksize=2 * 1024 * 1024,
        resumable=True,
    )

    try:
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )
        response = None
        retries = 0
        while response is None:
            try:
                status, response = request.next_chunk()
                if status and progress_cb:
                    pct = int(status.progress() * 100)
                    progress_cb(pct, int(status.resumable_progress))
            except HttpError as err:
                if err.resp.status in (500, 502, 503, 504) and retries < 3:
                    retries += 1
                    continue
                raise YouTubeOAuthError(
                    f"YouTube upload API rejected request ({err.resp.status}): {err.content.decode('utf-8', 'ignore')[:300]}",
                    code="upload_rejected",
                    status_code=err.resp.status,
                ) from err

        if not response or not response.get("id"):
            raise YouTubeOAuthError(
                "YouTube API did not return a confirmed video ID after upload.",
                code="unconfirmed_upload",
                status_code=502,
            )

        if progress_cb:
            progress_cb(100, file_size)

        return response
    except YouTubeOAuthError:
        raise
    except Exception as exc:
        raise YouTubeOAuthError(
            f"Upload interrupted or failed: {exc}",
            code="upload_interrupted",
            status_code=500,
        ) from exc

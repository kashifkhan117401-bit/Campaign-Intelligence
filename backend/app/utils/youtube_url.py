"""YouTube URL validation and video ID extraction utilities."""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_VALID_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}


def extract_youtube_video_id(url: str) -> str:
    """Validate a public YouTube URL and return its 11-character video ID.

    Raises ValueError if the URL is invalid or does not reference a single video.
    """
    raw = (url or "").strip()
    if not raw:
        raise ValueError("Please provide a YouTube video URL.")

    if _VIDEO_ID_RE.match(raw):
        return raw

    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw

    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    if host not in _VALID_HOSTS:
        raise ValueError(
            "Invalid YouTube URL. Supported domains: youtube.com and youtu.be."
        )

    video_id = ""
    path_parts = [p for p in parsed.path.split("/") if p]

    if host in {"youtu.be", "www.youtu.be"}:
        if path_parts:
            video_id = path_parts[0]
    else:
        if path_parts and path_parts[0] == "watch":
            qs = parse_qs(parsed.query)
            video_id = (qs.get("v") or [""])[0]
        elif len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "live", "v"}:
            video_id = path_parts[1]
        else:
            qs = parse_qs(parsed.query)
            video_id = (qs.get("v") or [""])[0]

    if not _VIDEO_ID_RE.match(video_id):
        raise ValueError(
            "Could not extract a valid 11-character YouTube video ID from the provided URL."
        )

    return video_id


def canonical_youtube_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"

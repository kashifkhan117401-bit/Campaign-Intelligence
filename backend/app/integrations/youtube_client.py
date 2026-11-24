"""YouTube Data API v3 integration for video metadata and paginated comment collection."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx

from app.core.config import get_settings
from app.core.security import sanitize_untrusted_text

logger = logging.getLogger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeIntegrationError(Exception):
    """Structured error for YouTube Data API failures."""

    def __init__(self, message: str, code: str = "youtube_error", status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class YouTubeDataClient:
    """Handles YouTube Data API v3 video metadata lookup and paginated comment fetching."""

    def __init__(self, api_key: Optional[str] = None, timeout: float = 20.0):
        settings = get_settings()
        self.api_key = (api_key if api_key is not None else settings.YOUTUBE_API_KEY).strip()
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _request_with_retry(
        self, endpoint: str, params: Dict[str, Any], max_retries: int = 3
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise YouTubeIntegrationError(
                "YOUTUBE_API_KEY is not configured. Add YOUTUBE_API_KEY to your .env file "
                "or enable Demo Mode for development testing.",
                code="missing_api_key",
                status_code=503,
            )

        query = {**params, "key": self.api_key}
        url = f"{YOUTUBE_API_BASE}/{endpoint}"

        last_error: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(url, params=query)

                if resp.status_code == 200:
                    return resp.json()

                data = {}
                try:
                    data = resp.json()
                except Exception:
                    pass

                err_info = data.get("error", {})
                reasons = [e.get("reason", "") for e in err_info.get("errors", [])]
                err_msg = err_info.get("message", f"HTTP {resp.status_code}")

                if "commentsDisabled" in reasons:
                    raise YouTubeIntegrationError(
                        "Comments are disabled on this YouTube video.",
                        code="comments_disabled",
                        status_code=403,
                    )
                if "quotaExceeded" in reasons or "dailyLimitExceeded" in reasons:
                    raise YouTubeIntegrationError(
                        "YouTube Data API v3 quota has been exceeded. Try again after quota reset.",
                        code="quota_exceeded",
                        status_code=429,
                    )
                if resp.status_code == 404 or "videoNotFound" in reasons:
                    raise YouTubeIntegrationError(
                        "The YouTube video was not found, is private, or has been deleted.",
                        code="video_not_found",
                        status_code=404,
                    )
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                    time.sleep(min(2 ** attempt, 6))
                    continue

                raise YouTubeIntegrationError(
                    f"YouTube API error ({resp.status_code}): {err_msg}",
                    code="api_error",
                    status_code=resp.status_code,
                )
            except YouTubeIntegrationError:
                raise
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt < max_retries:
                    time.sleep(min(2 ** attempt, 5))
                    continue
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < max_retries:
                    time.sleep(min(2 ** attempt, 5))
                    continue

        raise YouTubeIntegrationError(
            f"Failed to contact YouTube Data API after {max_retries} attempts: {last_error}",
            code="network_error",
            status_code=504,
        )

    def fetch_video_metadata(self, video_id: str) -> Dict[str, Any]:
        payload = self._request_with_retry(
            "videos",
            {
                "part": "snippet,statistics,contentDetails",
                "id": video_id,
            },
        )
        items = payload.get("items", [])
        if not items:
            raise YouTubeIntegrationError(
                "Video not found or unavailable (it may be private, unlisted, or removed).",
                code="video_not_found",
                status_code=404,
            )

        item = items[0]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        content_details = item.get("contentDetails", {})
        thumbs = snippet.get("thumbnails", {})
        thumb_url = (
            thumbs.get("maxres", {}).get("url")
            or thumbs.get("high", {}).get("url")
            or thumbs.get("medium", {}).get("url")
            or thumbs.get("default", {}).get("url")
            or f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        )

        published_raw = snippet.get("publishedAt")
        published_at = None
        if published_raw:
            try:
                published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
            except ValueError:
                published_at = None

        return {
            "youtube_video_id": video_id,
            "title": sanitize_untrusted_text(snippet.get("title", ""), max_length=450),
            "description": sanitize_untrusted_text(snippet.get("description", ""), max_length=5000),
            "channel_id": snippet.get("channelId", ""),
            "channel_title": sanitize_untrusted_text(snippet.get("channelTitle", ""), max_length=200),
            "thumbnail_url": thumb_url,
            "published_at": published_at,
            "duration_iso": content_details.get("duration", ""),
            "view_count": int(stats.get("viewCount", 0) or 0),
            "like_count": int(stats.get("likeCount", 0) or 0),
            "comment_count": int(stats.get("commentCount", 0) or 0),
            "tags_json": snippet.get("tags", [])[:40],
            "category_id": str(snippet.get("categoryId", "")),
            "comments_disabled": False,
            "is_demo_data": False,
        }

    def fetch_top_level_comments(
        self,
        video_id: str,
        max_comments: int = 2000,
        progress_cb: Optional[Callable[[int], None]] = None,
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """Collect up to max_comments (capped at 2,000) accessible top-level comments.

        Returns (comments_list, comments_disabled_flag).
        """
        cap = max(1, min(max_comments, 2000))
        collected: List[Dict[str, Any]] = []
        seen_ids: set[str] = set()
        page_token: Optional[str] = None

        while len(collected) < cap:
            batch_size = min(100, cap - len(collected))
            params: Dict[str, Any] = {
                "part": "snippet",
                "videoId": video_id,
                "maxResults": batch_size,
                "textFormat": "plainText",
                "order": "relevance",
            }
            if page_token:
                params["pageToken"] = page_token

            try:
                payload = self._request_with_retry("commentThreads", params)
            except YouTubeIntegrationError as exc:
                if exc.code == "comments_disabled":
                    return [], True
                raise

            items = payload.get("items", [])
            if not items:
                break

            for thread in items:
                top_comment = thread.get("snippet", {}).get("topLevelComment", {})
                cid = top_comment.get("id") or thread.get("id")
                if not cid or cid in seen_ids:
                    continue
                seen_ids.add(cid)

                c_snip = top_comment.get("snippet", {})
                raw_text = c_snip.get("textOriginal") or c_snip.get("textDisplay") or ""
                sanitized = sanitize_untrusted_text(raw_text, max_length=2000)
                if not sanitized:
                    continue

                pub_raw = c_snip.get("publishedAt")
                pub_dt = None
                if pub_raw:
                    try:
                        pub_dt = datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))
                    except ValueError:
                        pub_dt = None

                collected.append(
                    {
                        "youtube_comment_id": cid,
                        "author_display_name": sanitize_untrusted_text(
                            c_snip.get("authorDisplayName", "YouTube Viewer"), max_length=150
                        ),
                        "text_original": raw_text[:4000],
                        "text_sanitized": sanitized,
                        "like_count": int(c_snip.get("likeCount", 0) or 0),
                        "reply_count": int(thread.get("snippet", {}).get("totalReplyCount", 0) or 0),
                        "published_at": pub_dt,
                    }
                )

            if progress_cb:
                progress_cb(len(collected))

            page_token = payload.get("nextPageToken")
            if not page_token:
                break

        return collected, False


def build_demo_video_and_comments(video_id: str, max_comments: int = 80) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Explicitly labeled development demo dataset used ONLY when API keys are unconfigured and demo fallback is allowed."""
    now = datetime.now(timezone.utc)
    video_meta = {
        "youtube_video_id": video_id,
        "title": f"[DEMO DATA] Complete AI Creator Workflow & Growth Playbook ({video_id})",
        "description": (
            "[DEVELOPMENT DEMO MODE] Sample video metadata generated because YOUTUBE_API_KEY "
            "is not configured. Connect a valid YouTube Data API v3 key in .env to analyze live videos."
        ),
        "channel_id": "UC_DEMO_TUBEMIND",
        "channel_title": "Campaign Intelligence Demo Lab",
        "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        "published_at": now - timedelta(days=14),
        "duration_iso": "PT16M42S",
        "view_count": 48250,
        "like_count": 2940,
        "comment_count": 124,
        "tags_json": ["youtube growth", "ai workflow", "video editing", "creator economy", "seo"],
        "category_id": "28",
        "comments_disabled": False,
        "is_demo_data": True,
    }

    sample_templates = [
        ("Alex Rivera", "This workflow breakdown saved me at least 6 hours a week. Best practical tutorial I have seen this year!", 84),
        ("Priya Nair", "Love the pacing, but the pricing tier comparison around 9:30 felt really confusing. Can you explain the monthly limits?", 52),
        ("Marcus Chen", "Where can I buy the Notion template you showed at 4:15? Take my money!", 67),
        ("Elena Petrova", "Honestly frustrated that the audio export steps skipped Windows users completely. Mac-only guides are annoying.", 41),
        ("Jordan Blake", "Does this work well for faceless channels or only talking-head videos? Would love a follow-up video on this.", 39),
        ("Sofia Morales", "Subscribed immediately! The thumbnail retention checklist alone doubled my CTR on my latest upload.", 93),
        ("Devon Brooks", "Too fast in the analytics section. I had to replay 11:20 three times to understand the retention drop graph.", 28),
        ("Hannah Kim", "Please add a downloadable PDF checklist or chapter timestamps in the description so we can jump back quickly.", 76),
        ("Liam O'Connor", "I'm skeptical about whether paid YouTube ads actually convert for small channels under 10k subscribers. Any real budget numbers?", 45),
        ("Nadia Hassan", "Finally someone explains SEO titles without clickbait fluff. Clear, honest, and trustworthy advice.", 61),
        ("Tyler Grant", "My channel is in B2B SaaS—how should we adapt the hook structure for decision-makers instead of consumers?", 33),
        ("Chloe Dubois", "The editing software keeps crashing when exporting 4K 60fps. Is there a lighter alternative you recommend?", 29),
        ("Samir Patel", "Watched all the way through! Can you do a deep dive on Shorts scripting and turning long-form videos into Reels?", 55),
        ("Rachel Foster", "Pricing feels a bit steep for solo creators just starting out. Is there a free tier or annual discount?", 37),
        ("Kenji Sato", "Great breakdown of metadata optimization. Adding chapters improved our search impressions noticeably.", 48),
        ("Olivia Bennett", "Why did you skip YouTube Analytics API setup? That's the exact part where OAuth throws permission errors for me.", 44),
        ("Diego Vargas", "Super excited to test this A/B title framework on our product launch video next Monday!", 31),
        ("Maya Lin", "Neutral take: good overview for beginners, though intermediate creators already know half of these retention tips.", 22),
        ("Ethan Wallace", "How much should I budget per day if I want to promote a 12-minute tutorial in the US and UK?", 36),
        ("Grace Okafor", "This is the exact system our agency needed. Do you offer team seats or white-label PDF reports for clients?", 71),
    ]

    count = min(max_comments, 60)
    comments: List[Dict[str, Any]] = []
    for idx in range(count):
        author, text, likes = sample_templates[idx % len(sample_templates)]
        suffix = "" if idx < len(sample_templates) else f" (Viewer follow-up #{idx + 1})"
        full_text = f"{text}{suffix}"
        comments.append(
            {
                "youtube_comment_id": f"demo_{video_id}_{idx + 1}",
                "author_display_name": author if idx < len(sample_templates) else f"{author} #{idx // len(sample_templates) + 1}",
                "text_original": full_text,
                "text_sanitized": sanitize_untrusted_text(full_text),
                "like_count": max(0, likes - (idx // len(sample_templates)) * 8),
                "reply_count": idx % 4,
                "published_at": now - timedelta(days=max(0, 13 - (idx % 14)), hours=idx % 24),
            }
        )

    return video_meta, comments

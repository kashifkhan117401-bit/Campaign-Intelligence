"""Video processing: FFmpeg/FFprobe metadata extraction, frame sampling, transcription, and AI metadata."""
from __future__ import annotations

import json
import logging
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.ai.llm_provider import BaseLLMProvider, GeminiLLMProvider, get_llm_provider
from app.core.config import get_settings

logger = logging.getLogger(__name__)

ALLOWED_VIDEO_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
    "video/mpeg",
    "application/octet-stream",  # verified via extension + header bytes
}

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".mpeg", ".mpg", ".m4v"}


def is_ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def verify_video_file_magic(file_path: str, filename: str) -> Tuple[bool, str]:
    """Validate video extension and inspect container magic header bytes."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        return False, f"Unsupported video file extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}."

    try:
        with open(file_path, "rb") as f:
            header = f.read(32)
    except OSError as exc:
        return False, f"Failed to read uploaded file: {exc}"

    if len(header) < 8:
        return False, "Uploaded file is too small to be a valid video container."

    # Check common container signatures (MP4/MOV ftyp, WebM/MKV EBML, AVI RIFF, MPEG)
    is_mp4_mov = b"ftyp" in header[4:16] or b"moov" in header or b"mdat" in header
    is_ebml = header.startswith(b"\x1a\x45\xdf\xa3")
    is_riff = header.startswith(b"RIFF") and b"AVI" in header[8:16]
    is_mpeg = header.startswith(b"\x00\x00\x01")

    if not (is_mp4_mov or is_ebml or is_riff or is_mpeg):
        return (
            False,
            "File signature does not match a recognized video container (MP4, MOV, WebM, MKV, AVI, MPEG).",
        )
    return True, "ok"


def extract_video_metadata(file_path: str) -> Dict[str, Any]:
    """Extract duration, resolution, aspect ratio, FPS, and audio info via ffprobe."""
    size_bytes = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    if not shutil.which("ffprobe"):
        logger.info("ffprobe not installed; returning basic container metadata.")
        return {
            "file_size_bytes": size_bytes,
            "duration_seconds": 0.0,
            "width": 0,
            "height": 0,
            "aspect_ratio": "unknown (install FFmpeg)",
            "frame_rate": 0.0,
            "audio_codec": "unknown (install FFmpeg)",
            "audio_channels": 0,
            "audio_sample_rate": 0,
            "metadata_source": "filesystem_only",
        }

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
        probe = json.loads(proc.stdout)
    except Exception as exc:
        logger.warning("ffprobe failed on %s: %s", file_path, exc)
        return {
            "file_size_bytes": size_bytes,
            "duration_seconds": 0.0,
            "width": 0,
            "height": 0,
            "aspect_ratio": "unknown",
            "frame_rate": 0.0,
            "audio_codec": "unknown",
            "audio_channels": 0,
            "audio_sample_rate": 0,
            "metadata_source": "ffprobe_error",
        }

    fmt = probe.get("format", {})
    streams = probe.get("streams", [])
    v_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})

    duration = float(fmt.get("duration") or v_stream.get("duration") or 0.0)
    width = int(v_stream.get("width") or 0)
    height = int(v_stream.get("height") or 0)

    aspect = "unknown"
    if width > 0 and height > 0:
        g = math.gcd(width, height)
        aspect = f"{width // g}:{height // g}"

    fps = 0.0
    r_fps = v_stream.get("avg_frame_rate") or v_stream.get("r_frame_rate") or "0/1"
    if "/" in str(r_fps):
        num, den = str(r_fps).split("/", 1)
        try:
            fps = round(float(num) / max(1.0, float(den)), 2)
        except ValueError:
            fps = 0.0

    return {
        "file_size_bytes": size_bytes,
        "duration_seconds": round(duration, 2),
        "width": width,
        "height": height,
        "aspect_ratio": aspect,
        "frame_rate": fps,
        "audio_codec": str(a_stream.get("codec_name") or "none"),
        "audio_channels": int(a_stream.get("channels") or 0),
        "audio_sample_rate": int(a_stream.get("sample_rate") or 0),
        "metadata_source": "ffprobe",
    }


def sample_representative_frames(file_path: str, media_id: str, duration_seconds: float, count: int = 4) -> List[Dict[str, Any]]:
    """Extract representative JPEG keyframes via FFmpeg for visual understanding."""
    settings = get_settings()
    if not shutil.which("ffmpeg") or duration_seconds <= 0:
        return []

    out_dir = Path(settings.FRAMES_DIR) / media_id
    out_dir.mkdir(parents=True, exist_ok=True)
    frames: List[Dict[str, Any]] = []
    step = duration_seconds / (count + 1)

    for idx in range(1, count + 1):
        ts = round(step * idx, 2)
        frame_file = out_dir / f"frame_{idx}.jpg"
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(ts),
            "-i", file_path,
            "-frames:v", "1",
            "-q:v", "4",
            str(frame_file),
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=20, check=True)
            if frame_file.exists():
                frames.append(
                    {
                        "index": idx,
                        "timestamp_seconds": ts,
                        "timestamp_label": _format_timestamp(ts),
                        "path": str(frame_file),
                    }
                )
        except Exception as exc:
            logger.warning("Frame sampling at %ss failed: %s", ts, exc)
    return frames


def _guess_media_mime_type(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    mime_map = {
        ".mp3": "audio/mp3",
        ".wav": "audio/wav",
        ".aac": "audio/aac",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".m4a": "audio/mp4",
        ".mp4": "video/mp4",
        ".m4v": "video/mp4",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
        ".mkv": "video/x-matroska",
        ".avi": "video/x-msvideo",
        ".mpeg": "video/mpeg",
        ".mpg": "video/mpeg",
    }
    return mime_map.get(ext, "audio/mp3")


def transcribe_video_audio(file_path: str, media_id: str) -> Tuple[str, List[Dict[str, Any]], bool]:
    """Extract audio and transcribe via configurable provider (Google Gemini default, OpenAI Whisper optional).

    Returns (transcript_text, segments_list, is_demo_or_fallback).
    """
    settings = get_settings()
    provider = settings.TRANSCRIPTION_PROVIDER.lower().strip()
    use_openai = provider in ("openai", "whisper")

    if use_openai:
        if not settings.has_openai_key:
            return (
                "[Transcription unavailable: OPENAI_API_KEY is not configured. Add OPENAI_API_KEY in .env "
                "to enable Whisper speech-to-text transcription and timestamped chapter extraction.]",
                [],
                True,
            )
    else:
        if not settings.has_gemini_key:
            return (
                "[Transcription unavailable: GEMINI_API_KEY is not configured. Add GEMINI_API_KEY in .env "
                "to enable Gemini audio transcription and timestamped chapter extraction.]",
                [],
                True,
            )

    audio_target = file_path
    temp_audio_path: Optional[Path] = None
    if shutil.which("ffmpeg"):
        temp_audio_path = Path(settings.FRAMES_DIR) / f"{media_id}_audio.mp3"
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", file_path,
                    "-vn", "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1", "-b:a", "64k",
                    str(temp_audio_path),
                ],
                capture_output=True,
                timeout=90,
                check=True,
            )
            if temp_audio_path.exists() and temp_audio_path.stat().st_size > 0:
                audio_target = str(temp_audio_path)
        except Exception as exc:
            logger.warning("Audio extraction failed, trying direct file upload for transcription: %s", exc)

    try:
        if use_openai:
            from openai import OpenAI

            client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=120.0)
            with open(audio_target, "rb") as audio_file:
                resp = client.audio.transcriptions.create(
                    model=settings.WHISPER_MODEL,
                    file=audio_file,
                    response_format="verbose_json",
                )
            text = getattr(resp, "text", "") or ""
            raw_segments = getattr(resp, "segments", None) or []
            segments = [
                {
                    "start": round(float(getattr(s, "start", 0.0)), 2),
                    "end": round(float(getattr(s, "end", 0.0)), 2),
                    "timestamp": _format_timestamp(float(getattr(s, "start", 0.0))),
                    "text": str(getattr(s, "text", "")).strip(),
                }
                for s in raw_segments
            ]
            return text.strip(), segments, False

        gemini = GeminiLLMProvider()
        resp_json = gemini.transcribe_audio_json(
            audio_target,
            mime_type=_guess_media_mime_type(audio_target),
        )
        text = str(resp_json.get("text") or "").strip()
        raw_segments = resp_json.get("segments") or []
        segments: List[Dict[str, Any]] = []
        for s in raw_segments:
            if not isinstance(s, dict):
                continue
            try:
                start_val = round(float(s.get("start", 0.0)), 2)
                end_val = round(float(s.get("end", start_val)), 2)
            except (TypeError, ValueError):
                start_val, end_val = 0.0, 0.0
            seg_text = str(s.get("text") or "").strip()
            if seg_text:
                segments.append(
                    {
                        "start": start_val,
                        "end": end_val,
                        "timestamp": _format_timestamp(start_val),
                        "text": seg_text,
                    }
                )
        if not text and segments:
            text = " ".join(s["text"] for s in segments)
        return text, segments, False
    except Exception as exc:
        logger.warning("Audio transcription failed (%s): %s", provider, exc)
        return f"[Audio transcription failed: {exc}]", [], True
    finally:
        if temp_audio_path and temp_audio_path.exists():
            try:
                temp_audio_path.unlink()
            except OSError:
                pass


def analyze_uploaded_video_content(
    *,
    filename: str,
    metadata: Dict[str, Any],
    transcript_text: str,
    transcript_segments: List[Dict[str, Any]],
    frames: List[Dict[str, Any]],
    custom_notes: str = "",
    provider: Optional[BaseLLMProvider] = None,
) -> Dict[str, Any]:
    llm = provider or get_llm_provider()
    clean_name = Path(filename).stem.replace("_", " ").replace("-", " ").strip() or "Uploaded Video"

    if llm.is_available():
        try:
            resp = llm.generate_json(
                system_prompt=(
                    "Analyze the provided uploaded video metadata, frame timestamps, and transcript. "
                    "Return JSON with keys: main_subject (str), topics_covered (list[str]), "
                    "important_moments (list of {timestamp: str, description: str}), "
                    "target_audience (str), video_objective (str), visual_notes (str)."
                ),
                user_prompt=(
                    f"Filename: {filename}\nDuration: {metadata.get('duration_seconds')}s\n"
                    f"Resolution: {metadata.get('width')}x{metadata.get('height')} ({metadata.get('aspect_ratio')})\n"
                    f"Frames sampled: {len(frames)}\nCreator notes: {custom_notes}\n"
                    f"<UNTRUSTED_USER_DATA>\nTranscript:\n{transcript_text[:3500]}\n</UNTRUSTED_USER_DATA>"
                ),
                temperature=0.3,
                max_tokens=1500,
            )
            if resp.get("main_subject"):
                return resp
        except Exception as exc:
            logger.warning("LLM video content analysis fallback used: %s", exc)

    duration = float(metadata.get("duration_seconds") or 0.0)
    moments = []
    if transcript_segments:
        step = max(1, len(transcript_segments) // 4)
        for seg in transcript_segments[::step][:5]:
            moments.append({"timestamp": seg["timestamp"], "description": seg["text"][:120]})
    elif duration > 0:
        moments = [
            {"timestamp": "00:00", "description": "Opening hook and core video premise"},
            {"timestamp": _format_timestamp(duration * 0.35), "description": "Primary demonstration / main concept"},
            {"timestamp": _format_timestamp(duration * 0.70), "description": "Key takeaways and actionable walkthrough"},
            {"timestamp": _format_timestamp(duration * 0.90), "description": "Summary and viewer call to action"},
        ]
    else:
        moments = [
            {"timestamp": "00:00", "description": "Opening hook (install FFmpeg & configure Gemini API for exact timestamped moments)"},
        ]

    return {
        "main_subject": custom_notes[:160] if custom_notes else f"Video presentation on {clean_name}",
        "topics_covered": [
            clean_name,
            "Step-by-step demonstration",
            "Key viewer takeaways",
            "Actionable recommendations",
        ],
        "important_moments": moments,
        "target_audience": "YouTube viewers seeking practical guidance on " + clean_name,
        "video_objective": "Educate viewers clearly and drive engagement/subscriptions",
        "visual_notes": (
            f"Sampled {len(frames)} keyframes at {metadata.get('width', 0)}x{metadata.get('height', 0)} "
            f"({metadata.get('aspect_ratio', 'unknown')})."
            if frames
            else "Keyframes will be sampled automatically when FFmpeg is installed on the host/container."
        ),
    }


def generate_video_publish_metadata(
    *,
    filename: str,
    content_analysis: Dict[str, Any],
    transcript_segments: List[Dict[str, Any]],
    tone: str = "Professional",
    target_keywords: Optional[List[str]] = None,
    provider: Optional[BaseLLMProvider] = None,
) -> Dict[str, Any]:
    llm = provider or get_llm_provider()
    subject = content_analysis.get("main_subject") or Path(filename).stem
    kws = target_keywords or content_analysis.get("topics_covered", [])[:5]

    if llm.is_available():
        try:
            resp = llm.generate_json(
                system_prompt=(
                    "Generate YouTube publishing metadata strictly aligned to the analyzed video content. "
                    "Never guarantee rankings. Return JSON with keys: titles (list of 5 strings <= 100 chars), "
                    "description (str), hashtags (list of 12 strings starting with #), tags (list of 15 strings), "
                    "chapters (list of {timestamp: str, title: str}), thumbnail_concepts (list of 3 {concept: str, overlay_text: str}), "
                    "pinned_comment (str), call_to_action (str), category_suggestion ({id: str, name: str}), "
                    "audience_targeting (list[str])."
                ),
                user_prompt=(
                    f"Subject: {subject}\nTone: {tone}\nKeywords: {kws}\n"
                    f"Important moments: {content_analysis.get('important_moments', [])}\n"
                    f"Transcript segments available: {len(transcript_segments)}"
                ),
                temperature=0.45,
                max_tokens=2200,
            )
            if resp.get("titles"):
                return resp
        except Exception as exc:
            logger.warning("LLM video metadata generation fallback used: %s", exc)

    chapters = []
    if transcript_segments:
        step = max(1, len(transcript_segments) // 5)
        for idx, seg in enumerate(transcript_segments[::step][:6]):
            chapters.append(
                {
                    "timestamp": "00:00" if idx == 0 else seg["timestamp"],
                    "title": seg["text"][:60] or f"Section {idx + 1}",
                }
            )
    else:
        for idx, m in enumerate(content_analysis.get("important_moments", [])[:5]):
            chapters.append(
                {
                    "timestamp": "00:00" if idx == 0 else m.get("timestamp", "00:00"),
                    "title": m.get("description", f"Part {idx + 1}")[:60],
                }
            )

    chapter_lines = "\n".join(f"{c['timestamp']} {c['title']}" for c in chapters)
    clean_subject = subject[:70]
    tags = list(dict.fromkeys([*(str(k) for k in kws), clean_subject, "youtube tutorial", "how to", "creator guide"]))[:15]
    hashtags = ["#" + "".join(ch for ch in t.title() if ch.isalnum()) for t in tags[:10] if len(t) > 2]

    return {
        "titles": [
            f"{clean_subject} — Complete Step-by-Step Guide",
            f"How to Master {clean_subject} (Practical Walkthrough)",
            f"{clean_subject}: Everything You Need to Know",
            f"The Honest Breakdown of {clean_subject}",
            f"{clean_subject} Explained Clearly for Beginners & Pros",
        ],
        "description": (
            f"Watch this {tone.lower()} walkthrough covering {subject}.\n\n"
            f"Chapters:\n{chapter_lines}\n\n"
            f"Topics Covered:\n"
            + "\n".join(f"- {t}" for t in content_analysis.get("topics_covered", [])[:5])
            + "\n\n"
            + " ".join(hashtags[:6])
        ),
        "hashtags": hashtags,
        "tags": tags,
        "chapters": chapters,
        "thumbnail_concepts": [
            {"concept": "High-contrast creator close-up with clean result metric card", "overlay_text": "STEP-BY-STEP"},
            {"concept": "Before vs. After split screen highlighting the core transformation", "overlay_text": "FIX THIS FIRST"},
            {"concept": "Minimalist UI screenshot callout with bold directional arrow", "overlay_text": "FULL WORKFLOW"},
        ],
        "pinned_comment": (
            f"Quick question for everyone watching: Which part of {clean_subject} do you want us to dive deeper into next? "
            "Drop a timestamp or question below!"
        ),
        "call_to_action": "Subscribe for weekly practical breakdowns and check the chapter timestamps in the description.",
        "category_suggestion": {"id": "27", "name": "Education / Science & Technology"},
        "audience_targeting": [
            content_analysis.get("target_audience", "Creators & practitioners"),
            "Viewers searching step-by-step tutorials in this niche",
            "Returning subscribers interested in practical workflows",
        ],
    }


def _format_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hrs, rem = divmod(total, 3600)
    mins, secs = divmod(rem, 60)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

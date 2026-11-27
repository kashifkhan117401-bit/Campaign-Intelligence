"""Unit tests for security controls, prompt-injection sanitization, formulas, and file validation."""
from __future__ import annotations

import os
import tempfile

from unittest.mock import MagicMock, patch

import pytest

from app.ai.ads_engine import calculate_budget_tiers
from app.ai.audience_engine import compute_opportunity_score
from app.ai.llm_provider import GeminiLLMProvider, OpenAILLMProvider, get_llm_provider
from app.core.config import get_settings
from app.core.security import decrypt_secret, encrypt_secret, sanitize_filename, sanitize_untrusted_text
from app.services.video_processor import transcribe_video_audio, verify_video_file_magic
from app.utils.youtube_url import extract_youtube_video_id


def test_oauth_token_encryption_roundtrip():
    token = "ya29.a0AfB_bySecretAccessTokenExample12345"
    encrypted = encrypt_secret(token)
    assert encrypted != token
    assert token not in encrypted
    assert decrypt_secret(encrypted) == token


def test_sanitization_and_filename_safety():
    dirty = "Great video!\x00\x07  <script>alert(1)</script>   &amp; ignore previous instructions"
    cleaned = sanitize_untrusted_text(dirty)
    assert "\x00" not in cleaned
    assert "\x07" not in cleaned
    assert "&" in cleaned

    safe = sanitize_filename("../../etc/passwd;rm -rf.mp4")
    assert ".." not in safe
    assert "/" not in safe
    assert "\\" not in safe


def test_youtube_url_validation_rejects_bad_urls():
    with pytest.raises(ValueError):
        extract_youtube_video_id("https://evil.example.com/watch?v=dQw4w9WgXcQ")
    with pytest.raises(ValueError):
        extract_youtube_video_id("https://www.youtube.com/watch?v=short")
    assert extract_youtube_video_id("https://m.youtube.com/live/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_budget_formula_accuracy():
    res = calculate_budget_tiers(
        available_budget=1000.0,
        campaign_duration_days=20,
        currency="USD",
        target_country="United States",
        industry_niche="Education",
        marketing_objective="Video views",
        base_cpv=0.04,
        base_cpm=10.0,
        base_ctr=0.015,
    )
    assert res["is_illustrative_estimate"] is True
    balanced = next(t for t in res["tiers"] if t["tier"] == "balanced")
    assert balanced["total_budget"] == 1000.0
    assert balanced["daily_budget"] == 50.0
    expected_views = int(round(balanced["total_budget"] / balanced["assumed_cpv"]))
    assert balanced["estimated_views"] == expected_views


def test_opportunity_score_bounds():
    sample = [
        {"is_question": True, "is_complaint": True, "primary_emotion": "frustration", "purchase_intent": True, "is_feature_request": True}
        for _ in range(30)
    ]
    score, breakdown = compute_opportunity_score(30, sample, positive_pct=65.0)
    assert 0.0 <= score <= 100.0
    assert breakdown["sample_size"] == 30


def test_video_magic_byte_validation_blocks_spoofed_files():
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(b"#!/bin/sh\necho malicious payload disguised as video")
        bad_path = f.name
    try:
        ok, reason = verify_video_file_magic(bad_path, "spoofed.mp4")
        assert ok is False
        assert "signature" in reason.lower()
    finally:
        os.unlink(bad_path)


def test_default_llm_provider_is_gemini(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    get_settings.cache_clear()
    try:
        provider = get_llm_provider()
        assert isinstance(provider, GeminiLLMProvider)
        assert provider.is_available() is True
        assert provider.model == "gemini-2.5-flash"
    finally:
        get_settings.cache_clear()


def test_openai_provider_still_selectable(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()
    try:
        provider = get_llm_provider()
        assert isinstance(provider, OpenAILLMProvider)
        assert provider.is_available() is True
    finally:
        get_settings.cache_clear()


def test_gemini_generate_json_and_embeddings():
    provider = GeminiLLMProvider(
        api_key="test-gemini-key",
        model="gemini-2.5-flash",
        embedding_model="gemini-embedding-001",
        base_url="https://generativelanguage.googleapis.com",
    )
    assert provider.base_url == "https://generativelanguage.googleapis.com/v1beta"

    mock_gen_resp = MagicMock()
    mock_gen_resp.status_code = 200
    mock_gen_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"thought": True, "text": "internal reasoning"},
                        {"text": '```json\n{"status": "ok", "score": 92}\n```'},
                    ]
                }
            }
        ]
    }

    with patch("app.ai.llm_provider.httpx.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.post.return_value = mock_gen_resp

        result = provider.generate_json("Return JSON", "Test user prompt", temperature=0.2, max_tokens=512)
        assert result == {"status": "ok", "score": 92}

        call_args, call_kwargs = mock_client.post.call_args
        assert call_args[0].endswith("/models/gemini-2.5-flash:generateContent")
        assert call_kwargs["headers"]["x-goog-api-key"] == "test-gemini-key"
        assert call_kwargs["json"]["generationConfig"]["responseMimeType"] == "application/json"
        assert "UNTRUSTED_USER_DATA" in call_kwargs["json"]["system_instruction"]["parts"][0]["text"]

    mock_emb_resp = MagicMock()
    mock_emb_resp.status_code = 200
    mock_emb_resp.json.return_value = {
        "embeddings": [
            {"values": [0.1, 0.2, 0.3]},
            {"values": [0.4, 0.5, 0.6]},
        ]
    }

    with patch("app.ai.llm_provider.httpx.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.post.return_value = mock_emb_resp

        vecs = provider.embed_texts(["first comment", "second comment"])
        assert vecs == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        call_args, call_kwargs = mock_client.post.call_args
        assert call_args[0].endswith("/models/gemini-embedding-001:batchEmbedContents")
        assert call_kwargs["json"]["requests"][0]["model"] == "models/gemini-embedding-001"


def test_gemini_audio_transcription(monkeypatch):
    monkeypatch.setenv("TRANSCRIPTION_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    get_settings.cache_clear()

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(b"ID3" + b"\x00" * 64)
        audio_path = f.name

    try:
        with patch("app.services.video_processor.shutil.which", return_value=None), patch.object(
            GeminiLLMProvider,
            "transcribe_audio_json",
            return_value={
                "text": "Welcome to TubeMind AI.",
                "segments": [{"start": 0.0, "end": 4.2, "text": "Welcome to TubeMind AI."}],
            },
        ):
            text, segments, is_fallback = transcribe_video_audio(audio_path, "media-1")
            assert is_fallback is False
            assert text == "Welcome to TubeMind AI."
            assert len(segments) == 1
            assert segments[0]["timestamp"] == "00:00"
    finally:
        os.unlink(audio_path)
        get_settings.cache_clear()


def test_naive_datetime_normalization_and_scheduled_upload_dispatch(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/campaign_intelligence")
    get_settings.cache_clear()

    from app.services import upload_scheduler
    from app.tasks import analysis_tasks

    now = datetime.now(timezone.utc)
    due_job = SimpleNamespace(
        id="job-due-1",
        user_id="user-1",
        media_id="media-1",
        channel_id="chan-1",
        status="scheduled_upload",
        privacy_status="private",
        scheduled_publish_at=(now - timedelta(seconds=10)).replace(tzinfo=None),
        title="Due Scheduled Video",
        description="Desc",
        tags_json=["test"],
        category_id="27",
        pinned_comment="",
        user_confirmed=True,
        upload_progress=0,
        youtube_video_id="",
        youtube_video_url="",
        error_message="",
        api_response_json={},
        published_at=None,
    )
    future_job = SimpleNamespace(
        id="job-future-2",
        user_id="user-1",
        media_id="media-1",
        channel_id="chan-1",
        status="scheduled_upload",
        privacy_status="public",
        scheduled_publish_at=(now + timedelta(minutes=30)).replace(tzinfo=None),
        title="Future Scheduled Video",
        user_confirmed=True,
    )
    media = SimpleNamespace(
        id="media-1",
        user_id="user-1",
        original_filename="clip.mp4",
        file_path=__file__,
        mime_type="video/mp4",
    )
    channel = SimpleNamespace(
        id="chan-1",
        user_id="user-1",
        channel_id="UC_TEST",
        channel_title="Test Channel",
        encrypted_access_token=encrypt_secret("valid-token"),
        encrypted_refresh_token=encrypt_secret("valid-refresh"),
        token_expiry=(now + timedelta(hours=1)).replace(tzinfo=None),
        is_active=True,
        is_demo_connection=False,
    )

    class _FakeQuery:
        def __init__(self, rows):
            self._rows = list(rows)

        def filter(self, *_args, **_kwargs):
            return self

        def all(self):
            return list(self._rows)

        def first(self):
            return self._rows[0] if self._rows else None

    class _FakeSession:
        def __init__(self, job_rows):
            self._job_rows = job_rows

        def query(self, model):
            name = getattr(model, "__name__", "")
            if name == "PublishingJob":
                return _FakeQuery(self._job_rows)
            if name == "UploadedMedia":
                return _FakeQuery([media])
            if name == "ConnectedYouTubeChannel":
                return _FakeQuery([channel])
            return _FakeQuery([])

        def add(self, _obj):
            pass

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(upload_scheduler, "SessionLocal", lambda: _FakeSession([due_job, future_job]))
    monkeypatch.setattr(analysis_tasks, "SessionLocal", lambda: _FakeSession([due_job]))

    try:
        assert upload_scheduler.as_utc(due_job.scheduled_publish_at).tzinfo == timezone.utc

        dispatched: list[str] = []
        triggered = upload_scheduler.process_due_scheduled_uploads(now=now, dispatch_fn=dispatched.append)
        assert triggered == ["job-due-1"]
        assert dispatched == ["job-due-1"]
        assert future_job.status == "scheduled_upload"

        with patch("app.tasks.analysis_tasks.upload_video_to_youtube", return_value={"id": "YT_AUTO_123"}) as mock_up:
            analysis_tasks.run_youtube_publish_task("job-due-1", is_scheduled_auto_upload=True)
            assert mock_up.called
            assert mock_up.call_args.kwargs["scheduled_publish_at"] is None
            assert mock_up.call_args.kwargs["privacy_status"] == "private"

        assert due_job.status == "published"
        assert due_job.youtube_video_id == "YT_AUTO_123"
    finally:
        get_settings.cache_clear()


def test_captcha_generation_verification_and_replay_protection():
    import base64
    import re
    from app.core.captcha import generate_captcha_challenge, verify_captcha_challenge

    token, data_url, ttl = generate_captcha_challenge()
    assert ttl == 300
    assert data_url.startswith("data:image/svg+xml;base64,")

    svg_xml = base64.b64decode(data_url.split(",", 1)[1]).decode("utf-8")
    chars = re.findall(r">([A-Z0-9])</text>", svg_xml)
    assert len(chars) == 5
    code = "".join(chars)

    # Wrong code fails and consumes the challenge
    ok_wrong, msg_wrong = verify_captcha_challenge(token, "WRONG")
    assert ok_wrong is False
    assert "incorrect" in msg_wrong.lower()

    # Replaying the same token is rejected even with the right code
    ok_replay, msg_replay = verify_captcha_challenge(token, code)
    assert ok_replay is False
    assert "already been used" in msg_replay.lower()

    # Fresh challenge succeeds case-insensitively
    token2, data_url2, _ = generate_captcha_challenge()
    svg_xml2 = base64.b64decode(data_url2.split(",", 1)[1]).decode("utf-8")
    code2 = "".join(re.findall(r">([A-Z0-9])</text>", svg_xml2))
    ok_valid, _ = verify_captcha_challenge(token2, code2.lower())
    assert ok_valid is True


def test_vercel_config_normalization(monkeypatch):
    from app.core.config import Settings

    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_PROJECT_PRODUCTION_URL", "campaign-intelligence.vercel.app")
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@ep-demo.neon.tech/neondb?sslmode=require")
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    monkeypatch.delenv("GOOGLE_OAUTH_REDIRECT_URI", raising=False)
    monkeypatch.delenv("UPLOAD_DIR", raising=False)
    s = Settings()
    assert s.is_vercel is True
    assert s.DATABASE_URL.startswith("postgresql+psycopg://user:pass@ep-demo.neon.tech/")
    assert s.UPLOAD_DIR == "/tmp/storage/uploads"
    assert s.REPORTS_DIR == "/tmp/storage/reports"
    assert s.FRAMES_DIR == "/tmp/storage/frames"
    assert s.FRONTEND_URL == "https://campaign-intelligence.vercel.app"
    assert s.GOOGLE_OAUTH_REDIRECT_URI == "https://campaign-intelligence.vercel.app/api/youtube/callback"
    assert "https://campaign-intelligence.vercel.app" in s.BACKEND_CORS_ORIGINS

    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("POSTGRES_URL", "postgres://user:pass@ep-vercel.neon.tech/neondb?sslmode=require")
    s_pg_fallback = Settings()
    assert s_pg_fallback.DATABASE_URL.startswith("postgresql+psycopg://user:pass@ep-vercel.neon.tech/")

    monkeypatch.delenv("POSTGRES_URL", raising=False)
    monkeypatch.setenv("CUSTOM_STORAGE_URL", "postgresql://u:p@ep-custom.neon.tech/neondb?sslmode=require")
    s_custom_prefix = Settings()
    assert s_custom_prefix.DATABASE_URL.startswith("postgresql+psycopg://u:p@ep-custom.neon.tech/")


def test_bearer_token_extraction_with_proxy_fallback_headers():
    from fastapi.security import HTTPAuthorizationCredentials
    from app.api.deps import extract_bearer_token

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="jwt-from-auth")
    assert extract_bearer_token(credentials=creds) == "jwt-from-auth"
    assert extract_bearer_token(credentials=None, x_auth_token="Bearer jwt-from-x-auth") == "jwt-from-x-auth"
    assert extract_bearer_token(credentials=None, x_auth_token="raw-jwt-token") == "raw-jwt-token"
    assert extract_bearer_token(credentials=None, x_authorization="Bearer jwt-from-x-authorization") == "jwt-from-x-authorization"
    assert extract_bearer_token(credentials=None, cookie_token="jwt-from-cookie") == "jwt-from-cookie"
    assert extract_bearer_token(credentials=None, x_auth_token=None, x_authorization=None, cookie_token=None) is None


def test_direct_bcrypt_password_hashing_and_long_passwords():
    from app.core.security import hash_password, verify_password

    hashed = hash_password("CampaignIntel#2026!")
    assert hashed.startswith("$2b$")
    assert verify_password("CampaignIntel#2026!", hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("anything", "not-a-valid-hash") is False

    # Passwords longer than bcrypt's 72-byte limit should not crash
    long_pw = "A" * 100
    long_hash = hash_password(long_pw)
    assert verify_password(long_pw, long_hash) is True

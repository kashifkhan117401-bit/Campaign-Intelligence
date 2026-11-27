"""End-to-end integration tests covering all TubeMind AI backend workflows."""
from __future__ import annotations

import os
import tempfile

# Configure isolated test environment BEFORE importing app modules
_tmp_dir = tempfile.mkdtemp(prefix="campaign_intelligence_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_dir}/test_campaign_intelligence.db"
os.environ["UPLOAD_DIR"] = os.path.join(_tmp_dir, "uploads")
os.environ["REPORTS_DIR"] = os.path.join(_tmp_dir, "reports")
os.environ["FRAMES_DIR"] = os.path.join(_tmp_dir, "frames")
os.environ["ALLOW_DEMO_MODE"] = "true"
os.environ["CAPTCHA_ENABLED"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-for-tubemind-integration-suite-32c"
os.environ["YOUTUBE_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""

from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app
from app.utils.youtube_url import extract_youtube_video_id

Base.metadata.create_all(bind=engine)
client = TestClient(app)


def test_health_and_url_validation():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    assert extract_youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_youtube_video_id("https://youtu.be/dQw4w9WgXcQ?t=42") == "dQw4w9WgXcQ"
    assert extract_youtube_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_full_saas_workflow_e2e():
    # 1. Register user
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "architect@tubemind.ai",
            "password": "StrongPassword123!",
            "full_name": "Elena Vance",
            "company_name": "GrowthLab Media",
        },
    )
    assert reg.status_code == 201, reg.text
    tokens = reg.json()
    access = tokens["access_token"]
    refresh = tokens["refresh_token"]
    headers = {"Authorization": f"Bearer {access}"}

    # 2. Refresh token rotation
    ref = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert ref.status_code == 200, ref.text
    access = ref.json()["access_token"]
    refresh = ref.json()["refresh_token"]
    headers = {"Authorization": f"Bearer {access}"}

    # 3. Profile & settings update
    prof = client.put(
        "/api/auth/profile",
        headers=headers,
        json={"niche": "AI & SaaS Tutorials", "primary_goal": "Grow B2B leads", "onboarding_completed": True},
    )
    assert prof.status_code == 200
    assert prof.json()["onboarding_completed"] is True

    # 3b. Integration status reports Gemini as default AI provider
    integ = client.get("/api/auth/integrations", headers=headers)
    assert integ.status_code == 200
    integ_json = integ.json()
    assert integ_json["llm_provider"] == "gemini"
    assert integ_json["llm_model"] == "gemini-2.5-flash"
    assert integ_json["gemini_configured"] is False
    assert integ_json["ai_configured"] is False

    # 4. Analysis without demo fallback should clearly explain missing YOUTUBE_API_KEY
    blocked = client.post(
        "/api/analyze",
        headers=headers,
        json={"youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "max_comments": 40, "use_demo_fallback": False},
    )
    assert blocked.status_code == 503
    assert "YOUTUBE_API_KEY" in blocked.json()["detail"]

    # 5. Run analysis with explicit development demo fallback
    ana = client.post(
        "/api/analyze",
        headers=headers,
        json={"youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "max_comments": 40, "use_demo_fallback": True},
    )
    assert ana.status_code == 202, ana.text
    analysis_id = ana.json()["id"]

    # TestClient executes FastAPI BackgroundTasks synchronously before returning
    detail = client.get(f"/api/analyze/{analysis_id}", headers=headers)
    assert detail.status_code == 200
    d_json = detail.json()
    assert d_json["status"] == "completed"
    assert d_json["is_demo_data"] is True
    assert d_json["analyzed_comments_count"] == 40
    assert round(d_json["positive_pct"] + d_json["negative_pct"] + d_json["neutral_pct"], 1) >= 99.8

    # 6. Paginated comments & filtering
    cmts = client.get(f"/api/analyze/{analysis_id}/comments?page=1&page_size=10&sentiment=positive", headers=headers)
    assert cmts.status_code == 200
    assert len(cmts.json()["items"]) > 0
    assert all(c["sentiment"] == "positive" for c in cmts.json()["items"])

    # 7. Audience Intelligence & transparent Opportunity Score
    ins = client.get(f"/api/analyze/{analysis_id}/insights", headers=headers)
    assert ins.status_code == 200
    ins_json = ins.json()
    assert 0 <= ins_json["opportunity_score"] <= 100
    assert len(ins_json["top_10_questions_json"]) == 10
    assert "0.25" in ins_json["opportunity_formula_doc"]

    # 8. AI Content Generation Studio (create, edit, list)
    gen = client.post(
        "/api/content/generate",
        headers=headers,
        json={"analysis_id": analysis_id, "tone": "Educational", "target_audience": "SaaS Founders"},
    )
    assert gen.status_code == 201, gen.text
    content_id = gen.json()["id"]
    assert len(gen.json()["youtube_content_json"]["title_options"]) == 5
    assert len(gen.json()["seo_json"]["hashtags"]) >= 12
    assert len(gen.json()["content_strategy_json"]["future_video_ideas"]) == 10

    upd = client.put(
        f"/api/content/{content_id}",
        headers=headers,
        json={"status": "saved", "title": "Updated Educational Playbook"},
    )
    assert upd.status_code == 200
    assert upd.json()["status"] == "saved"

    # 9. Video Upload Studio (upload valid MP4 header, analyze, generate metadata, draft publish)
    fake_mp4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + (b"\x00" * 2048)
    up = client.post(
        "/api/videos/upload",
        headers=headers,
        files={"file": ("creator_demo.mp4", fake_mp4, "video/mp4")},
    )
    assert up.status_code == 201, up.text
    media_id = up.json()["id"]

    vid_ana = client.post(
        "/api/videos/analyze",
        headers=headers,
        json={"video_id": media_id, "custom_notes": "Step-by-step SaaS onboarding tutorial"},
    )
    assert vid_ana.status_code == 200, vid_ana.text

    vid_meta = client.post(
        f"/api/videos/{media_id}/generate-metadata",
        headers=headers,
        json={"tone": "Professional", "target_keywords": ["saas onboarding", "youtube tutorial"]},
    )
    assert vid_meta.status_code == 200, vid_meta.text
    assert len(vid_meta.json()["generated_metadata_json"]["titles"]) == 5

    # Reject live publish without confirmation
    unconfirmed = client.post(
        "/api/youtube/publish",
        headers=headers,
        json={
            "media_id": media_id,
            "title": "Test Video Title",
            "publish_action": "upload",
            "privacy_status": "private",
            "user_confirmed": False,
        },
    )
    assert unconfirmed.status_code == 400

    # Save as draft succeeds cleanly
    draft = client.post(
        "/api/youtube/publish",
        headers=headers,
        json={
            "media_id": media_id,
            "title": "SaaS Onboarding Playbook",
            "description": "Full walkthrough",
            "publish_action": "draft",
            "privacy_status": "private",
            "user_confirmed": False,
        },
    )
    assert draft.status_code == 201
    job_id = draft.json()["id"]
    job_status = client.get(f"/api/youtube/publishing-status/{job_id}", headers=headers)
    assert job_status.status_code == 200
    assert job_status.json()["status"] == "draft"

    # 10. Advertising Strategy & Budget Calculator
    b_est = client.post(
        "/api/ads/budget-estimate",
        headers=headers,
        json={
            "available_budget": 1500,
            "campaign_duration_days": 30,
            "currency": "USD",
            "target_country": "United States",
            "industry_niche": "SaaS",
            "marketing_objective": "Video views",
        },
    )
    assert b_est.status_code == 200
    assert len(b_est.json()["tiers"]) == 3
    assert b_est.json()["is_illustrative_estimate"] is True

    strat = client.post(
        "/api/ads/strategy",
        headers=headers,
        json={
            "campaign_name": "Q4 Creator Launch",
            "analysis_id": analysis_id,
            "video_context": "Educational walkthrough solving viewer onboarding friction",
            "target_country": "United States",
            "target_audience": "SaaS founders and digital marketers",
            "industry_niche": "B2B SaaS",
            "marketing_objective": "Lead generation",
            "campaign_duration_days": 30,
            "available_budget": 2500,
            "currency": "USD",
        },
    )
    assert strat.status_code == 201, strat.text
    strategy_id = strat.json()["id"]
    assert len(strat.json()["budget_estimates"]) == 3

    # 11. PDF Report Generation, Download, and Regeneration
    rep = client.post(
        "/api/reports/generate",
        headers=headers,
        json={"analysis_id": analysis_id, "content_id": content_id, "strategy_id": strategy_id},
    )
    assert rep.status_code == 201, rep.text
    report_id = rep.json()["id"]
    assert rep.json()["file_size_bytes"] > 2000
    assert rep.json()["page_count"] >= 3

    dl = client.get(f"/api/reports/{report_id}/download", headers=headers)
    assert dl.status_code == 200
    assert dl.headers["content-type"] == "application/pdf"
    assert dl.content.startswith(b"%PDF")

    regen = client.post(f"/api/reports/{report_id}/regenerate", headers=headers)
    assert regen.status_code == 200
    assert regen.json()["version"] == 2

    # 12. Dashboard Overview & Activity + User Data Isolation
    dash = client.get("/api/dashboard/overview", headers=headers)
    assert dash.status_code == 200
    dash_json = dash.json()
    assert dash_json["total_videos_analyzed"] == 1
    assert dash_json["total_comments_analyzed"] == 40
    assert dash_json["content_generated_count"] == 1
    assert dash_json["reports_created_count"] == 1

    act = client.get("/api/dashboard/activity", headers=headers)
    assert act.status_code == 200
    assert act.json()["total"] >= 4

    # Verify second user cannot access first user's analysis
    reg2 = client.post(
        "/api/auth/register",
        json={"email": "other@tubemind.ai", "password": "OtherPassword123!", "full_name": "Other User"},
    )
    headers2 = {"Authorization": f"Bearer {reg2.json()['access_token']}"}
    isolated = client.get(f"/api/analyze/{analysis_id}", headers=headers2)
    assert isolated.status_code == 404

    # Logout
    lo = client.post("/api/auth/logout", headers=headers, json={"refresh_token": refresh})
    assert lo.status_code == 200

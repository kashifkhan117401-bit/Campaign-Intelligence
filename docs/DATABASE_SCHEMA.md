# Campaign Intelligence — Database Schema Documentation

Campaign Intelligence uses a normalized relational schema managed via **SQLAlchemy 2.0** and **Alembic** migrations targeting **PostgreSQL** (via `psycopg` — e.g. Neon, Supabase, or local PostgreSQL 16).

## Tables Overview (18 Tables)

1. **`users`**: Core authentication credentials (`id`, `email` unique index, `hashed_password`, `role`, `is_active`, password reset token hash + expiry, timestamps).
2. **`user_profiles`**: 1:1 profile & onboarding metadata (`full_name`, `company_name`, `job_title`, `niche`, `primary_goal`, `onboarding_completed`).
3. **`refresh_tokens`**: SHA-256 hashed rotating JWT refresh tokens (`token_hash` unique index, `expires_at`, `revoked`).
4. **`user_settings`**: 1:1 user workspace preferences & configurable ad benchmarks (`default_tone`, `default_currency`, `preferred_llm_model`, `benchmark_cpv`, `benchmark_cpm`, `benchmark_ctr`).
5. **`connected_youtube_channels`**: Per-user OAuth 2.0 YouTube channels with Fernet-encrypted `encrypted_access_token` and `encrypted_refresh_token` at rest.
6. **`youtube_videos`**: Metadata for analyzed YouTube videos (`youtube_video_id`, `url`, `title`, `view_count`, `like_count`, `comment_count`, `comments_disabled`, `is_demo_data`).
7. **`video_analyses`**: Analysis job status, progress percentage, collected/analyzed counts, sentiment breakdown, emotion counts, ranked topics/keywords/pain points, qualitative arrays, sentiment trends, and AI disclaimer.
8. **`comments`**: Collected top-level YouTube comments (`text_original`, `text_sanitized`, `author_display_name`, `like_count`, `reply_count`, `published_at`).
9. **`comment_sentiment_results`**: 1:1 per-comment AI classification (`sentiment`, `confidence`, `primary_emotion`, `purchase_intent`, `is_complaint`, `is_feature_request`, `is_question`, `topics_json`, `keywords_json`).
10. **`audience_insights`**: 1:1 strategic intelligence per analysis including Top 10 questions, `opportunity_score`, `opportunity_score_breakdown_json`, and transparent `opportunity_formula_doc`.
11. **`generated_content`**: Saved AI Content Studio packs (`youtube_content_json`, `seo_json`, `social_media_json`, `content_strategy_json`, `tone`, `status`).
12. **`uploaded_media`**: Uploaded video files, FFprobe technical specs, sampled keyframe paths, audio transcript & segments, AI video content analysis, and generated publishing metadata.
13. **`publishing_jobs`**: Drafts, queued uploads, scheduled publications, explicit `user_confirmed` audit timestamp, upload progress percentage, and verified YouTube API response.
14. **`advertising_strategies`**: Complete 12-area YouTube Ads strategy records linked optionally to an analysis or uploaded video.
15. **`budget_estimates`**: Normalized Low, Balanced, and Aggressive budget tier projections attached to an advertising strategy.
16. **`pdf_reports`**: Generated 18-section ReportLab PDF metadata, storage path, file size, page count, and version counter.
17. **`campaign_records`**: Unified user activity timeline linking analyses, content packs, ad strategies, publishing jobs, and PDF reports.
18. **`api_usage_logs`**: Audit log tracking external provider calls (`youtube_data`, `youtube_upload`, `gemini`, `openai`, `whisper`), status codes, quota units, and latency.

## Data Isolation & Migrations

- Every user-owned table includes a `user_id` foreign key (`ON DELETE CASCADE`) and index. Every API route scopes queries strictly to `current_user.id`.
- Generate a new migration after model edits:
  ```bash
  cd backend
  alembic revision --autogenerate -m "describe_change"
  alembic upgrade head
  ```

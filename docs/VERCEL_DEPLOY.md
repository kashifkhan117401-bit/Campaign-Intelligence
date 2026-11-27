# Deploying Campaign Intelligence on Vercel

This repository is pre-configured to deploy **both** the React/Vite frontend and the FastAPI Python backend together on **Vercel** from a single GitHub repository (`https://github.com/kashifkhan117401-bit/Campaign-Intelligence`).

---

## Architecture on Vercel

- **Frontend (React + Vite)**: Built via `vercel.json` (`cd frontend && npm run build`) and served globally from Vercel's CDN (`frontend/dist`).
- **Backend (FastAPI)**: Served via Vercel Python Serverless Function at `api/index.py` using root `requirements.txt`.
- **Routing**: `/api/*`, `/health`, `/docs`, `/redoc`, and `/openapi.json` route to `api/index.py`; all other paths rewrite to `/index.html` for React Router.
- **Database**: Use a free hosted PostgreSQL database (**Neon**, **Supabase**, or **Vercel Postgres**) via `DATABASE_URL` so user accounts, analyses, and history persist across serverless invocations. *(If `DATABASE_URL` is omitted, the backend falls back to ephemeral `/tmp/tubemind.db` for quick testing.)*
- **Scheduled Uploads Cron**: `vercel.json` includes a Vercel Cron calling `GET /api/youtube/cron/process-scheduled`.

---

## Step 1: Create a Free PostgreSQL Database (Recommended)

SQLite on Vercel `/tmp` is ephemeral and resets on cold starts. Create a free PostgreSQL database in ~1 minute:
- **Neon** (https://neon.tech) or **Vercel Storage → Marketplace → Neon Postgres** or **Supabase** (https://supabase.com).
- Copy the PostgreSQL connection string (`postgresql://...`). The backend automatically converts `postgres://` / `postgresql://` to `postgresql+psycopg://` for SQLAlchemy.

---

## Step 2: Import Project in Vercel

1. Go to [Vercel Dashboard → Add New → Project](https://vercel.com/new).
2. Import **`kashifkhan117401-bit/Campaign-Intelligence`**.
3. Leave **Root Directory** as `./` (repository root). `vercel.json` automatically configures install, build, output directory, and API routing.
4. Expand **Environment Variables** and add:

| Variable | Value |
|---|---|
| `APP_NAME` | `Campaign Intelligence` |
| `APP_ENV` | `production` |
| `DEBUG` | `false` |
| `DATABASE_URL` | Your Neon / Supabase PostgreSQL URL (`postgresql://...`) |
| `SECRET_KEY` | Random 64-char hex string (`python -c "import secrets; print(secrets.token_hex(32))"`) |
| `OAUTH_ENCRYPTION_KEY` | Fernet key (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) |
| `CAPTCHA_ENABLED` | `true` |
| `LLM_PROVIDER` | `gemini` |
| `GEMINI_API_KEY` | Your Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` |
| `GEMINI_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta` |
| `TRANSCRIPTION_PROVIDER` | `gemini` |
| `YOUTUBE_API_KEY` | Your YouTube Data API v3 key |
| `GOOGLE_CLIENT_ID` | Your Google OAuth 2.0 Web Client ID |
| `GOOGLE_CLIENT_SECRET` | Your Google OAuth 2.0 Web Client Secret |
| `ALLOW_DEMO_MODE` | `false` |
| `CRON_SECRET` | *(Optional)* Random secret string so Vercel Cron authenticates `/api/youtube/cron/process-scheduled` |

> `FRONTEND_URL`, `BACKEND_CORS_ORIGINS`, and `GOOGLE_OAUTH_REDIRECT_URI` are automatically detected from Vercel's `VERCEL_PROJECT_PRODUCTION_URL`, or you can set them explicitly to `https://<your-app>.vercel.app`.

5. Click **Deploy**.

---

## Step 3: Add Your Vercel Domain to Google Cloud Console OAuth

After Vercel gives you your live URL (e.g., `https://campaign-intelligence.vercel.app`):

1. Open [Google Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials).
2. Click your **OAuth 2.0 Web Client ID**.
3. Add under **Authorized JavaScript origins**:
   ```text
   https://<your-app>.vercel.app
   ```
4. Add under **Authorized redirect URIs**:
   ```text
   https://<your-app>.vercel.app/api/youtube/callback
   ```
5. Click **Save**.

---

## Important Vercel Serverless Limits to Know

- **Request body limit (4.5 MB)**: Vercel Serverless Functions cap HTTP request bodies at **4.5 MB**, so large video file uploads in **Video Publishing Studio** will exceed Vercel's limit (small clips under 4.5 MB work; for 100–500 MB video uploads and FFmpeg processing, host the backend on Render/Railway/VPS and set `VITE_API_URL` in Vercel to point to that backend).
- **Function timeout**: Configured to `maxDuration: 60` seconds in `vercel.json`.
- **Cron frequency**: Configured to `0 9 * * *` (daily) for Hobby plan compatibility; on Vercel Pro you can change `schedule` in `vercel.json` to `* * * * *` (every minute).

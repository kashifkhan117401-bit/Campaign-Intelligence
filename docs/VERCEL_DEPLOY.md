# Deploying Campaign Intelligence on Vercel (Services)

This repository uses Vercel's **Services** architecture (`vercel.json`) to deploy **both** services together in a single Vercel project on one domain:

- **`frontend` (Vite + React)** → served at `/`
- **`backend` (FastAPI)** → served at `/api`, `/health`, `/docs`, `/redoc`, `/openapi.json`

---

## Step 1: Create a Free PostgreSQL Database (Recommended)

SQLite on Vercel `/tmp` is ephemeral and resets between cold starts. Create a free PostgreSQL database in ~1 minute:
- **Neon** (https://neon.tech) or **Vercel Dashboard → Storage → Neon Postgres** or **Supabase** (https://supabase.com).
- Copy the connection string (`postgresql://...`). The backend automatically converts `postgres://` / `postgresql://` to `postgresql+psycopg://` for SQLAlchemy and uses `NullPool` on Vercel serverless.

---

## Step 2: Import into Vercel

1. Go to [Vercel Dashboard → Add New → Project](https://vercel.com/new).
2. Import **`kashifkhan117401-bit/Campaign-Intelligence`** (keep **Root Directory** as `./`).
3. You should see **2 grouped services**:
   - `frontend` (Vite) → `/`
   - `backend` (FastAPI) → `/api`
   *(Do **not** click "Import single project" on an individual folder—keep both grouped together in one project.)*
4. Expand **Environment Variables** and add:

| Variable | Value |
|---|---|
| `APP_NAME` | `Campaign Intelligence` |
| `APP_ENV` | `production` |
| `DEBUG` | `false` |
| `ALLOW_DEMO_MODE` | `false` |
| `CAPTCHA_ENABLED` | `true` |
| `DATABASE_URL` | Your Neon / Supabase PostgreSQL URL (`postgresql://...`) |
| `SECRET_KEY` | Random 64-char hex string (`python -c "import secrets; print(secrets.token_hex(32))"`) |
| `OAUTH_ENCRYPTION_KEY` | Fernet key (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) |
| `LLM_PROVIDER` | `gemini` |
| `GEMINI_API_KEY` | Your Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` |
| `GEMINI_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta` |
| `TRANSCRIPTION_PROVIDER` | `gemini` |
| `YOUTUBE_API_KEY` | Your YouTube Data API v3 key |
| `GOOGLE_CLIENT_ID` | Your Google OAuth 2.0 Web Client ID |
| `GOOGLE_CLIENT_SECRET` | Your Google OAuth 2.0 Web Client Secret |

> `FRONTEND_URL`, `BACKEND_CORS_ORIGINS`, and `GOOGLE_OAUTH_REDIRECT_URI` are automatically populated from Vercel's `VERCEL_PROJECT_PRODUCTION_URL`, or you can set them explicitly to `https://<your-app>.vercel.app`.

5. Click **Deploy**.

---

## Step 3: Add Your Vercel Domain to Google Cloud Console OAuth

1. Open [Google Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials) → click your **OAuth 2.0 Web Client ID**.
2. Add under **Authorized JavaScript origins**: `https://<your-app>.vercel.app`
3. Add under **Authorized redirect URIs**: `https://<your-app>.vercel.app/api/youtube/callback`
4. Click **Save**.

---

## Vercel Serverless Limits to Keep in Mind

- **Request body limit (4.5 MB)**: Large video uploads (>4.5 MB) in Video Studio exceed Vercel's serverless body limit; all other features (YouTube comment analysis, Gemini AI Content Studio, Ads Planner, PDF Reports, CAPTCHA auth, History deletion) work directly on Vercel.

# External API Configuration Guide (YouTube Data API v3, Google OAuth 2.0 & Google Gemini)

Never commit real credentials to Git. Always place API keys in `.env` (server-side only).

---

## 1. YouTube Data API v3 Setup (For Live Video & Comment Analysis)

1. Open [Google Cloud Console](https://console.cloud.google.com/) and create or select a project.
2. Navigate to **APIs & Services → Library**, search for **YouTube Data API v3**, and click **Enable**.
3. Optionally enable **YouTube Analytics API** if you intend to pull channel analytics for authorized channels.
4. Go to **APIs & Services → Credentials → Create Credentials → API Key**.
5. Restrict the API key to **YouTube Data API v3** and set it in `.env`:
   ```env
   YOUTUBE_API_KEY=AIzaSy...
   ```

**Quota Note:** Default YouTube Data API v3 quota is 10,000 units/day. `videos.list` uses 1 unit and each page of 100 comments via `commentThreads.list` uses 1 unit (2,000 comments ≈ 20 units).

---

## 2. Google OAuth 2.0 Setup (For Video Publishing Studio)

1. In Google Cloud Console, open **APIs & Services → OAuth consent screen**.
2. Choose **External** (or Internal for Google Workspace) and fill in App Name (`TubeMind AI`), support email, and developer email.
3. Add the required scopes:
   - `https://www.googleapis.com/auth/youtube.upload`
   - `https://www.googleapis.com/auth/youtube.readonly`
   - `https://www.googleapis.com/auth/yt-analytics.readonly`
4. Add your test Google accounts under **Test Users** while in Testing mode.
5. Navigate to **Credentials → Create Credentials → OAuth client ID → Web application**.
6. Under **Authorized redirect URIs**, add:
   - Development: `http://localhost:8000/api/youtube/callback`
   - Production: `https://api.yourdomain.com/api/youtube/callback`
7. Copy the Client ID and Client Secret into `.env`:
   ```env
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-...
   GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/youtube/callback
   ```
8. Generate a dedicated Fernet encryption key for OAuth tokens stored in the database:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
   Set `OAUTH_ENCRYPTION_KEY=<generated_key>` in `.env`.

**Publishing Policy Note:** Google requires OAuth app verification before unverified apps can upload public videos for arbitrary users (unverified apps upload as `private` until verified).

---

## 3. Google Gemini API Configuration (LLM, Embeddings & Audio Transcription)

1. Sign in to [Google AI Studio](https://aistudio.google.com/apikey) and create an API key.
2. Configure `.env`:
   ```env
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=AIza...
   GEMINI_MODEL=gemini-2.5-flash
   GEMINI_EMBEDDING_MODEL=gemini-embedding-001
   TRANSCRIPTION_PROVIDER=gemini
   ```
3. Optional: to use OpenAI or an OpenAI-compatible gateway instead, set `LLM_PROVIDER=openai`, `TRANSCRIPTION_PROVIDER=openai`, `OPENAI_API_KEY=sk-...`, and optionally `OPENAI_BASE_URL`.

---

## 4. Development Demo Mode

When `ALLOW_DEMO_MODE=true` and `YOUTUBE_API_KEY` is not yet configured, users may explicitly opt into **Development Demo Mode** in the YouTube Analyzer to test all charts, insights, content generation, and PDF exports with visibly labeled demo data. Always set `ALLOW_DEMO_MODE=false` in production.

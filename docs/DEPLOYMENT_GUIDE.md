# Production Deployment Guide

## Pre-Deployment Checklist

1. **Secrets & Cryptography**:
   - Set `APP_ENV=production`, `DEBUG=false`, and `ALLOW_DEMO_MODE=false`.
   - Generate a high-entropy `SECRET_KEY` (at least 64 random hex characters).
   - Generate a dedicated Fernet `OAUTH_ENCRYPTION_KEY` for OAuth token encryption at rest.
2. **PostgreSQL**:
   - Use managed PostgreSQL (Cloud SQL, RDS, Supabase, Neon) or the bundled `db` container with automated volume backups.
   - Set `DATABASE_URL=postgresql+psycopg://<user>:<pass>@<host>:5432/<db>`.
3. **Storage Persistence**:
   - Mount durable storage (or S3/GCS bucket) for `UPLOAD_DIR`, `REPORTS_DIR`, and `FRAMES_DIR`.
4. **HTTPS & CORS**:
   - Terminate TLS via Nginx, Caddy, Cloudflare, or a cloud load balancer.
   - Update `FRONTEND_URL`, `BACKEND_CORS_ORIGINS`, and `GOOGLE_OAUTH_REDIRECT_URI` to match your HTTPS domains.
5. **FFmpeg**:
   - The backend `Dockerfile` installs `ffmpeg` automatically so FFprobe metadata extraction, keyframe sampling, and audio extraction for Gemini/Whisper transcription work out of the box.

## Deploying with Docker Compose

```bash
cp .env.example .env
# Populate production secrets in .env
docker compose up -d --build
docker compose logs -f backend
```

The backend container automatically runs `alembic upgrade head` on startup before launching Uvicorn.

## Health Monitoring

- Backend health check: `GET /health` → returns `{"status": "ok", "service": "TubeMind AI", ...}`
- Database readiness check: Built into `docker-compose.yml` (`pg_isready`).

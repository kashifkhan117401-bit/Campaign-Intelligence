# Campaign Intelligence — Audience & YouTube Marketing Intelligence Platform

Campaign Intelligence (*"Know Pakistan's audience before you spend a rupee."*) is a full-stack, production-oriented AI SaaS platform built with **React + TypeScript + Vite + Tailwind CSS** on the frontend, **FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL** on the backend, **Google Gemini API** (with optional OpenAI fallback) for reasoning, embeddings, and audio transcription, **YouTube Data API v3 + OAuth 2.0** for live comment collection and confirmed video publishing, **FFmpeg** for video metadata and keyframe extraction, and **ReportLab** for 18-section executive PDF reports.

---

## Key Capabilities

1. **Authentication & User Management**
   - Registration, login, logout, bcrypt password hashing, JWT access tokens, rotating refresh tokens, password reset flow, user profiles, onboarding wizard, and user-level data isolation.
2. **YouTube Sentiment Analysis Engine**
   - Public YouTube URL validation (`watch`, `youtu.be`, `shorts`, `embed`, `live`), YouTube Data API v3 video metadata & paginated collection of up to **2,000 accessible top-level comments**, graceful handling of disabled comments, unavailable videos, and quota limits.
   - Untrusted comment sanitization & prompt-injection defense (`<UNTRUSTED_USER_DATA>` delimiters).
   - Batch AI sentiment (`Positive`, `Negative`, `Neutral`), emotions (`Frustration`, `Satisfaction`, `Confusion`, `Excitement`, `Trust`), purchase intent, complaints, feature requests, FAQs, buying objections, repeated keywords, emerging topic clusters, interactive Recharts dashboards, and filterable comment table.
3. **Audience Intelligence**
   - Interests, expectations, common problems, unanswered questions, agreement/disagreement drivers, frustrations, content gaps, product opportunities, objections, marketing angles, Top 10 future video questions, and a documented, transparent **Audience Opportunity Score (0–100)**.
4. **AI Content Generation Studio**
   - Context-aware generation in 5 tones (`Professional`, `Educational`, `Conversational`, `Persuasive`, `Entertaining`): 5 titles, 3 hooks, full structured script, SEO description, 15–25 hashtags, YouTube tags, Shorts/Reels/Facebook/LinkedIn/X copy, 10 future video ideas, 4-week calendar, inline editing, draft saving, and Markdown export.
5. **AI Video Upload & YouTube Publishing Studio**
   - Validated video uploads (MIME + container header checks + size limits), FFprobe technical metadata extraction, FFmpeg keyframe sampling, Gemini audio transcription (or optional Whisper), automated SEO metadata & timestamped chapters, editable preview, Google OAuth 2.0 channel connection (Fernet-encrypted tokens at rest), explicit user confirmation gate, and resumable YouTube Data API upload tracking.
6. **AI Advertising Strategy & Budget Planner**
   - 7 YouTube marketing objectives, 12-area campaign blueprint, and 3-tier Budget Calculator (`Low`, `Balanced`, `Aggressive`) using transparent configurable benchmark formulas (`Estimated Views = Campaign Budget / Assumed CPV`) with clear illustrative-estimate disclosures.
7. **Professional PDF Report Generator**
   - 18-section ReportLab multi-page executive PDF reports with vector sentiment & emotion charts, headers, footers, page numbers, download, and regeneration.

---

## Project Structure

```text
tubemind-ai/
├── frontend/               # React + TypeScript + Vite + Tailwind + Framer Motion + Recharts
│   └── src/
│       ├── components/
│       ├── contexts/
│       ├── hooks/
│       ├── layouts/
│       ├── pages/
│       ├── services/
│       ├── types/
│       └── utils/
├── backend/                # Python FastAPI + SQLAlchemy 2.0 + Alembic + ReportLab
│   ├── alembic/
│   ├── app/
│   │   ├── ai/
│   │   ├── api/
│   │   ├── core/
│   │   ├── integrations/
│   │   ├── models/
│   │   ├── reports/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── tasks/
│   │   └── utils/
│   └── tests/
├── database/               # PostgreSQL init scripts
├── docs/                   # API, Schema, OAuth, Gemini AI & Deployment guides
├── docker-compose.yml
└── .env.example
```

---

## Quick Start (Docker Compose — Recommended)

```bash
cd tubemind-ai
cp .env.example .env
# Edit .env with your GEMINI_API_KEY, YOUTUBE_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
docker compose up --build
```

- **Frontend SaaS UI**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **Interactive Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Local Development Setup (Without Docker)

### 1. Backend (Python 3.11+)
```bash
cd tubemind-ai/backend
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate

pip install -r requirements.txt
cp ../.env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend (Node.js 20+)
```bash
cd tubemind-ai/frontend
npm install
npm run dev
```

---

## Running Tests

```bash
cd tubemind-ai/backend
.\.venv\Scripts\pytest.exe -v tests/
```

---

## Documentation

- [API Reference](./docs/API_REFERENCE.md)
- [Database Schema Documentation](./docs/DATABASE_SCHEMA.md)
- [YouTube API, Google OAuth & Gemini AI Setup Guide](./docs/YOUTUBE_OAUTH_SETUP.md)
- [Production Deployment Guide](./docs/DEPLOYMENT_GUIDE.md)

---

© 2026 Kashif Hafeez. All rights reserved.

#!/usr/bin/env bash
# One-command setup script to run inside a PythonAnywhere Bash console
# Usage: bash scripts/pythonanywhere_setup.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USERNAME="${USER:-$(whoami)}"
DOMAIN="${USERNAME}.pythonanywhere.com"
VENV_DIR="${PROJECT_DIR}/backend/.venv"

echo "=== Campaign Intelligence — PythonAnywhere Setup ==="
echo "Project dir : ${PROJECT_DIR}"
echo "Domain      : https://${DOMAIN}"

# 1. Create virtualenv & install dependencies
PYTHON_BIN="$(command -v python3.11 || command -v python3.10 || command -v python3)"
echo "Using Python: ${PYTHON_BIN}"
if [ ! -d "${VENV_DIR}" ]; then
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
pip install --no-cache-dir --upgrade pip
pip install --no-cache-dir -r "${PROJECT_DIR}/backend/requirements.txt"

# 2. Generate .env if not already present
ENV_FILE="${PROJECT_DIR}/.env"
if [ ! -f "${ENV_FILE}" ]; then
  SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
  FERNET_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
  cat > "${ENV_FILE}" <<EOF
APP_NAME=Campaign Intelligence
APP_ENV=production
DEBUG=false
API_V1_PREFIX=/api
FRONTEND_URL=https://${DOMAIN}
BACKEND_CORS_ORIGINS=["https://${DOMAIN}"]

SECRET_KEY=${SECRET_KEY}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
CAPTCHA_ENABLED=true
OAUTH_ENCRYPTION_KEY=${FERNET_KEY}

DATABASE_URL=sqlite:////${PROJECT_DIR#/}/campaign_intelligence.db

LLM_PROVIDER=gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
TRANSCRIPTION_PROVIDER=gemini

YOUTUBE_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=https://${DOMAIN}/api/youtube/callback

ALLOW_DEMO_MODE=false

UPLOAD_DIR=${PROJECT_DIR}/storage/uploads
REPORTS_DIR=${PROJECT_DIR}/storage/reports
FRAMES_DIR=${PROJECT_DIR}/storage/frames
MAX_VIDEO_UPLOAD_MB=500

RATE_LIMIT_REQUESTS_PER_MINUTE=60
ANALYSIS_MAX_COMMENTS=2000
ANALYSIS_BATCH_SIZE=50
EOF
  echo "Created ${ENV_FILE} with generated SECRET_KEY and OAUTH_ENCRYPTION_KEY."
  echo "IMPORTANT: Edit ${ENV_FILE} to paste your GEMINI_API_KEY, YOUTUBE_API_KEY, GOOGLE_CLIENT_ID, and GOOGLE_CLIENT_SECRET."
else
  echo "${ENV_FILE} already exists — leaving untouched."
fi

# 3. Create storage dirs & run Alembic migrations
mkdir -p "${PROJECT_DIR}/storage/uploads" "${PROJECT_DIR}/storage/reports" "${PROJECT_DIR}/storage/frames"
cd "${PROJECT_DIR}/backend"
alembic upgrade head

echo ""
echo "=== Setup Complete! ==="
echo "Next steps in PythonAnywhere Web tab:"
echo "  1. Virtualenv path : ${VENV_DIR}"
echo "  2. WSGI file       :"
echo "       import sys"
echo "       sys.path.insert(0, \"${PROJECT_DIR}/backend\")"
echo "       from pythonanywhere_wsgi import application"
echo "  3. Static mapping  : /assets/ -> ${PROJECT_DIR}/frontend/dist/assets"
echo "  4. Google OAuth redirect URI: https://${DOMAIN}/api/youtube/callback"
echo "  5. Reload your web app and visit https://${DOMAIN}/health"

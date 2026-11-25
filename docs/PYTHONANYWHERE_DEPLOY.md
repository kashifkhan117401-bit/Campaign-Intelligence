# Deploying Campaign Intelligence on PythonAnywhere

This guide deploys both the **React frontend** and **FastAPI backend** together on a single PythonAnywhere domain (`https://<YOUR_USERNAME>.pythonanywhere.com`) using PythonAnywhere's standard WSGI Web App (`a2wsgi`) — **no separate frontend host required**.

---

## Step 1: Clone the Repo & Install Backend Dependencies

Open a **Bash console** on PythonAnywhere and run (replace `<YOUR_USERNAME>` with your PythonAnywhere username):

```bash
cd ~
git clone https://github.com/kashifkhan117401-bit/tubemind-ai-.git
cd ~/tubemind-ai-

# Create Python 3.11+ virtualenv
python3.11 -m venv ~/tubemind-ai-/backend/.venv
source ~/tubemind-ai-/backend/.venv/bin/activate

# Install backend dependencies (includes a2wsgi for PythonAnywhere WSGI)
pip install --upgrade pip
pip install -r backend/requirements.txt
```

> **Note:** On PythonAnywhere free accounts, disk quota is 512 MB. If `pip install` hits quota, run `pip install --no-cache-dir -r backend/requirements.txt`.

---

## Step 2: Build or Upload the Frontend (`frontend/dist`)

FastAPI automatically serves `frontend/dist` on `/` whenever `frontend/dist/index.html` exists.

**Option A — Upload from your Windows PC (Recommended on PythonAnywhere Free Tier):**
1. On your local PC, run:
   ```powershell
   cd C:\Users\me\Desktop\Project\tubemind-ai\frontend
   npm.cmd run build
   ```
2. Zip the `frontend/dist` folder and upload it to `/home/<YOUR_USERNAME>/tubemind-ai-/frontend/` via the PythonAnywhere **Files** tab, then unzip in Bash:
   ```bash
   cd ~/tubemind-ai-/frontend
   unzip -o dist.zip
   rm dist.zip
   ```
   Verify `/home/<YOUR_USERNAME>/tubemind-ai-/frontend/dist/index.html` exists.

**Option B — Build directly on PythonAnywhere (if Node 20+ is installed):**
```bash
cd ~/tubemind-ai-/frontend
npm install
npm run build
```

---

## Step 3: Create Production `.env` on PythonAnywhere

```bash
cd ~/tubemind-ai-
cp .env.example .env
nano .env
```

Set these production values (replace `<YOUR_USERNAME>` and populate your real API keys):

```env
APP_NAME=Campaign Intelligence
APP_ENV=production
DEBUG=false
API_V1_PREFIX=/api
FRONTEND_URL=https://<YOUR_USERNAME>.pythonanywhere.com
BACKEND_CORS_ORIGINS=["https://<YOUR_USERNAME>.pythonanywhere.com"]

# Generate strong secrets:
# python -c "import secrets; print(secrets.token_hex(32))"
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
SECRET_KEY=<PASTE_64_CHAR_HEX_SECRET>
OAUTH_ENCRYPTION_KEY=<PASTE_FERNET_KEY>
CAPTCHA_ENABLED=true

# Use absolute SQLite path on PythonAnywhere (or PostgreSQL on paid plans)
DATABASE_URL=sqlite:////home/<YOUR_USERNAME>/tubemind-ai-/tubemind.db

# AI / Google Gemini
LLM_PROVIDER=gemini
GEMINI_API_KEY=<YOUR_GEMINI_API_KEY>
GEMINI_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
TRANSCRIPTION_PROVIDER=gemini

# YouTube Data API v3 & Google OAuth 2.0
YOUTUBE_API_KEY=<YOUR_YOUTUBE_API_KEY>
GOOGLE_CLIENT_ID=<YOUR_GOOGLE_CLIENT_ID>
GOOGLE_CLIENT_SECRET=<YOUR_GOOGLE_CLIENT_SECRET>
GOOGLE_OAUTH_REDIRECT_URI=https://<YOUR_USERNAME>.pythonanywhere.com/api/youtube/callback

ALLOW_DEMO_MODE=false

# Absolute storage paths
UPLOAD_DIR=/home/<YOUR_USERNAME>/tubemind-ai-/storage/uploads
REPORTS_DIR=/home/<YOUR_USERNAME>/tubemind-ai-/storage/reports
FRAMES_DIR=/home/<YOUR_USERNAME>/tubemind-ai-/storage/frames
```

Run database migrations:
```bash
cd ~/tubemind-ai-/backend
source ~/tubemind-ai-/backend/.venv/bin/activate
alembic upgrade head
```

---

## Step 4: Update Google Cloud Console Redirect URI

1. Open [Google Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials).
2. Click your **OAuth 2.0 Web Client ID**.
3. Under **Authorized redirect URIs**, add:
   ```text
   https://<YOUR_USERNAME>.pythonanywhere.com/api/youtube/callback
   ```
4. Under **Authorized JavaScript origins**, add:
   ```text
   https://<YOUR_USERNAME>.pythonanywhere.com
   ```
5. Click **Save**.

---

## Step 5: Configure the PythonAnywhere Web App

1. Open the **Web** tab in PythonAnywhere → click **Add a new web app**.
2. Choose **Manual configuration** → select **Python 3.11** (matching the venv you created).
3. Under **Virtualenv**, enter:
   ```text
   /home/<YOUR_USERNAME>/tubemind-ai-/backend/.venv
   ```
4. Under **Code → WSGI configuration file**, click the link to open it, replace its entire contents with:
   ```python
   import sys

   path = "/home/<YOUR_USERNAME>/tubemind-ai-/backend"
   if path not in sys.path:
       sys.path.insert(0, path)

   from pythonanywhere_wsgi import application
   ```
5. *(Recommended for faster static loading)* Under **Static files**, add:
   - URL: `/assets/` → Directory: `/home/<YOUR_USERNAME>/tubemind-ai-/frontend/dist/assets`
6. Enable **Force HTTPS** under the **Security** section.
7. Click the green **Reload `<YOUR_USERNAME>.pythonanywhere.com`** button.
8. Verify:
   - Health check: `https://<YOUR_USERNAME>.pythonanywhere.com/health`
   - Web app: `https://<YOUR_USERNAME>.pythonanywhere.com`

---

## Step 6: Automatic Scheduled YouTube Uploads on PythonAnywhere

Under classic WSGI, background threads do not stay running continuously when idle. Use the included standalone scheduler script in the **Tasks** tab:

- **Paid account (Always-on Task — triggers within ~5 seconds):**
  ```bash
  /home/<YOUR_USERNAME>/tubemind-ai-/backend/.venv/bin/python /home/<YOUR_USERNAME>/tubemind-ai-/backend/run_upload_scheduler.py --loop --interval 5
  ```
- **Free account (Scheduled Task — runs once per scheduled slot):**
  ```bash
  /home/<YOUR_USERNAME>/tubemind-ai-/backend/.venv/bin/python /home/<YOUR_USERNAME>/tubemind-ai-/backend/run_upload_scheduler.py --once
  ```

---

## Important Notes for PythonAnywhere Free vs. Paid Accounts

- **Outbound API Access:** Free accounts route outbound HTTP through PythonAnywhere's whitelist proxy; `googleapis.com`, `generativelanguage.googleapis.com`, `accounts.google.com`, and `oauth2.googleapis.com` are Google endpoints, but if any outbound call returns a proxy `403` on a free account, upgrading to a Hacker/paid plan removes all outbound restrictions.
- **Video Uploads & FFmpeg:** Free accounts have a 512 MB total disk quota and shorter request timeouts, so keep uploaded test videos small (or upgrade for larger uploads and Always-on auto-upload tasks).
- **Native ASGI (Beta Alternative):** Paid accounts with PythonAnywhere's ASGI beta enabled can alternatively deploy Uvicorn directly via the `pa` CLI (`uvicorn app.main:app --app-dir backend`).

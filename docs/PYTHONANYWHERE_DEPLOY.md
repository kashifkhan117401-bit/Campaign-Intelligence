# Deploying Campaign Intelligence on PythonAnywhere

This guide deploys both the **React frontend** and **FastAPI backend** together on a single PythonAnywhere domain (`https://<YOUR_USERNAME>.pythonanywhere.com`) using PythonAnywhere's standard WSGI Web App (`a2wsgi`) — **no separate frontend host required**.

---

## Step 1: Clone & Run the Automated Setup Script (PythonAnywhere Bash Console)

Open a **Bash console** on PythonAnywhere and run:

```bash
cd ~
git clone https://github.com/kashifkhan117401-bit/Campaign-Intelligence.git
cd ~/Campaign-Intelligence
bash scripts/pythonanywhere_setup.sh
```

This automatically:
- Creates `~/Campaign-Intelligence/backend/.venv` and installs `backend/requirements.txt` (including `a2wsgi`).
- Generates a production `.env` with strong `SECRET_KEY`, `OAUTH_ENCRYPTION_KEY`, absolute SQLite & storage paths, and your `https://<YOUR_USERNAME>.pythonanywhere.com` URLs.
- Runs `alembic upgrade head` to initialize the database.

---

## Step 2: Add Your API Keys to `.env`

```bash
nano ~/Campaign-Intelligence/.env
```

Fill in:
- `GEMINI_API_KEY`
- `YOUTUBE_API_KEY`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`

Save & exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

---

## Step 3: Upload Built Frontend (`frontend/dist`)

FastAPI automatically serves `frontend/dist` on `/` whenever `frontend/dist/index.html` exists.

1. On your Windows PC, `frontend/dist.zip` is already packaged (or rebuild anytime with `cd frontend && npm.cmd run build`).
2. In PythonAnywhere's **Files** tab, open `/home/<YOUR_USERNAME>/Campaign-Intelligence/frontend/` and upload `dist.zip`.
3. In the PythonAnywhere Bash console, unzip it:
   ```bash
   cd ~/Campaign-Intelligence/frontend
   unzip -o dist.zip
   rm dist.zip
   ls -la dist/index.html
   ```

---

## Step 4: Add Redirect URI in Google Cloud Console

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

## Step 5: Configure the PythonAnywhere **Web** Tab

1. Open the **Web** tab → **Add a new web app** → **Manual configuration** → **Python 3.11** (matching the venv Python version).
2. **Virtualenv**:
   ```text
   /home/<YOUR_USERNAME>/Campaign-Intelligence/backend/.venv
   ```
3. **WSGI configuration file** (click the link and replace its entire contents with):
   ```python
   import sys

   path = "/home/<YOUR_USERNAME>/Campaign-Intelligence/backend"
   if path not in sys.path:
       sys.path.insert(0, path)

   from pythonanywhere_wsgi import application
   ```
4. **Static files** *(recommended for fast asset delivery)*:
   - URL: `/assets/` → Directory: `/home/<YOUR_USERNAME>/Campaign-Intelligence/frontend/dist/assets`
5. Enable **Force HTTPS** under **Security**.
6. Click **Reload `<YOUR_USERNAME>.pythonanywhere.com`**.
7. Test:
   - `https://<YOUR_USERNAME>.pythonanywhere.com/health`
   - `https://<YOUR_USERNAME>.pythonanywhere.com`

---

## Step 6: Automatic Scheduled YouTube Uploads (**Tasks** Tab)

- **Paid account (Always-on Task — checks every 5 seconds):**
  ```bash
  /home/<YOUR_USERNAME>/Campaign-Intelligence/backend/.venv/bin/python /home/<YOUR_USERNAME>/Campaign-Intelligence/backend/run_upload_scheduler.py --loop --interval 5
  ```
- **Free account (Scheduled Task):**
  ```bash
  /home/<YOUR_USERNAME>/Campaign-Intelligence/backend/.venv/bin/python /home/<YOUR_USERNAME>/Campaign-Intelligence/backend/run_upload_scheduler.py --once
  ```

---

## Notes for PythonAnywhere Free vs. Paid Plans

- **Outbound API Access:** Free accounts route outbound HTTP through PythonAnywhere's whitelist proxy; if Gemini or YouTube API calls hit a proxy `403`, upgrading to a Hacker/paid plan removes all outbound restrictions.
- **Disk & Always-on Tasks:** Free accounts have a 512 MB disk limit and no Always-on tasks (upgrade for larger video uploads and continuous 5-second auto-upload scheduling).

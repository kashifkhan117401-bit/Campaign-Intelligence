"""PythonAnywhere WSGI entrypoint wrapping the FastAPI ASGI app via a2wsgi.

In PythonAnywhere's Web tab WSGI configuration file, simply add:

    import sys
    sys.path.insert(0, "/home/<YOUR_USERNAME>/Campaign-Intelligence/backend")
    from pythonanywhere_wsgi import application
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

# Ensure relative paths in .env (SQLite DB, storage dirs) resolve from project root
os.chdir(str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from a2wsgi import ASGIMiddleware  # noqa: E402

import app.models  # noqa: E402, F401 - register SQLAlchemy models
from app.core.config import get_settings  # noqa: E402
from app.core.database import Base, engine  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402

# Classic WSGI does not run ASGI lifespan hooks, so initialize storage & tables eagerly
_settings = get_settings()
_settings.ensure_storage_dirs()
Base.metadata.create_all(bind=engine)

application = ASGIMiddleware(fastapi_app)

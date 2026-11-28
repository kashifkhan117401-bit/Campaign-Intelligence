"""Neon cloud primitives routes: public config, live service health, and Realtime query sealing."""
from __future__ import annotations

import hashlib
import hmac
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User

router = APIRouter(prefix="/neon", tags=["Neon Services"])


@router.get("/config")
def get_neon_public_config() -> Dict[str, Any]:
    """Return ONLY browser-safe Neon service URLs (never secrets)."""
    settings = get_settings()
    return {
        "branch": settings.NEON_BRANCH or None,
        "branch_id": settings.NEON_BRANCH_ID or None,
        "auth_url": settings.NEON_AUTH_BASE_URL or None,
        "realtime_url": settings.NEON_REALTIME_URL or None,
        "function_hello_url": settings.neon_function_url("hello"),
        "services": {
            "postgres": settings.DATABASE_URL.startswith("postgresql"),
            "auth": settings.has_neon_auth,
            "functions": settings.has_neon_functions,
            "realtime": settings.has_neon_realtime,
        },
    }


@router.get("/status")
def get_neon_services_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Live diagnostic check across free Neon services (Postgres, Auth, Functions, Realtime)."""
    settings = get_settings()
    result: Dict[str, Any] = {
        "branch": settings.NEON_BRANCH or None,
        "branch_id": settings.NEON_BRANCH_ID or None,
    }

    # 1. Lakebase Postgres
    try:
        row = db.execute(text("SELECT current_database(), current_user")).first()
        result["postgres"] = {
            "ok": True,
            "database": row[0] if row else None,
            "pooled": "-pooler" in settings.DATABASE_URL,
            "unpooled_configured": bool(settings.DATABASE_URL_UNPOOLED),
        }
    except Exception as exc:
        result["postgres"] = {"ok": False, "error": str(exc)}

    # 2. Neon Auth JWKS
    if settings.has_neon_auth:
        jwks_url = settings.NEON_AUTH_JWKS_URL.strip() or f"{settings.NEON_AUTH_BASE_URL.rstrip('/')}/.well-known/jwks.json"
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.get(jwks_url)
                keys = r.json().get("keys", []) if r.status_code == 200 else []
            result["auth"] = {"ok": r.status_code == 200 and len(keys) > 0, "status_code": r.status_code, "jwks_keys": len(keys)}
        except Exception as exc:
            result["auth"] = {"ok": False, "error": str(exc)}
    else:
        result["auth"] = {"ok": False, "detail": "Not configured"}

    # 3. Neon Function (hello)
    fn_url = settings.neon_function_url("hello")
    if fn_url:
        try:
            with httpx.Client(timeout=15.0) as client:
                r = client.get(fn_url)
                payload = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"text": r.text[:200]}
            result["functions"] = {"ok": r.status_code == 200, "url": fn_url, "status_code": r.status_code, "response": payload}
        except Exception as exc:
            result["functions"] = {"ok": False, "url": fn_url, "error": str(exc)}
    else:
        result["functions"] = {"ok": False, "detail": "Not configured"}

    # 4. Neon Realtime
    result["realtime"] = {
        "ok": settings.has_neon_realtime,
        "url_configured": bool(settings.NEON_REALTIME_URL),
        "secret_configured": bool(settings.NEON_REALTIME_SECRET),
    }
    return result


@router.post("/realtime/seal")
def seal_campaign_activity_query(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Seal a user-scoped live SQL query via the branch's Neon Function using NEON_REALTIME_SECRET."""
    settings = get_settings()
    fn_url = settings.neon_function_url("hello")
    if not settings.has_neon_realtime or not fn_url:
        raise HTTPException(status_code=503, detail="Neon Realtime or Neon Functions is not configured.")

    signature = hmac.new(
        settings.NEON_REALTIME_SECRET.encode("utf-8"),
        f"seal:{current_user.id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{fn_url}/realtime/seal",
                json={"user_id": current_user.id},
                headers={"X-Server-Signature": signature},
            )
            if resp.status_code >= 400:
                raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
            return resp.json()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to seal Neon Realtime query: {exc}")

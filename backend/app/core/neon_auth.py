"""Neon Managed Better Auth JWKS (EdDSA / Ed25519) JWT verifier."""
from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_JWKS_CACHE: Dict[str, Any] = {"url": "", "keys": [], "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 300.0


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _fetch_jwks(jwks_url: str, force_refresh: bool = False) -> List[Dict[str, Any]]:
    now = time.monotonic()
    if (
        not force_refresh
        and _JWKS_CACHE["url"] == jwks_url
        and _JWKS_CACHE["keys"]
        and (now - _JWKS_CACHE["fetched_at"]) < _JWKS_TTL_SECONDS
    ):
        return _JWKS_CACHE["keys"]

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(jwks_url)
        resp.raise_for_status()
        payload = resp.json()
    keys = payload.get("keys") if isinstance(payload, dict) else []
    if not isinstance(keys, list):
        keys = []
    _JWKS_CACHE["url"] = jwks_url
    _JWKS_CACHE["keys"] = keys
    _JWKS_CACHE["fetched_at"] = now
    return keys


def _verify_eddsa_with_keys(
    signing_input: bytes,
    signature: bytes,
    kid: Optional[str],
    keys: List[Dict[str, Any]],
) -> bool:
    candidates = [k for k in keys if not kid or k.get("kid") == kid]
    if not candidates:
        candidates = keys
    for jwk in candidates:
        if jwk.get("kty") != "OKP" or jwk.get("crv") != "Ed25519" or not jwk.get("x"):
            continue
        try:
            pub = Ed25519PublicKey.from_public_bytes(_b64url_decode(str(jwk["x"])))
            pub.verify(signature, signing_input)
            return True
        except (InvalidSignature, ValueError):
            continue
    return False


def verify_neon_auth_jwt(token: str) -> Optional[Dict[str, Any]]:
    """Verify a Neon Managed Better Auth EdDSA JWT against NEON_AUTH_JWKS_URL."""
    settings = get_settings()
    base_url = settings.NEON_AUTH_BASE_URL.strip().rstrip("/")
    jwks_url = settings.NEON_AUTH_JWKS_URL.strip() or (f"{base_url}/.well-known/jwks.json" if base_url else "")
    if not jwks_url or not base_url:
        return None

    parts = token.split(".")
    if len(parts) != 3:
        return None

    try:
        header = json.loads(_b64url_decode(parts[0]).decode("utf-8"))
        payload = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
        signature = _b64url_decode(parts[2])
    except Exception:
        return None

    if header.get("alg") != "EdDSA":
        return None

    now = time.time()
    exp = payload.get("exp")
    if exp is not None and float(exp) <= now:
        return None

    parsed_base = urlparse(base_url)
    expected_origin = f"{parsed_base.scheme}://{parsed_base.netloc}"
    iss = str(payload.get("iss") or "")
    if iss and iss.rstrip("/") not in (expected_origin, base_url):
        return None

    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    kid = header.get("kid")

    try:
        keys = _fetch_jwks(jwks_url, force_refresh=False)
        verified = _verify_eddsa_with_keys(signing_input, signature, kid, keys)
        if not verified:
            keys = _fetch_jwks(jwks_url, force_refresh=True)
            verified = _verify_eddsa_with_keys(signing_input, signature, kid, keys)
        if not verified:
            return None
    except Exception as exc:
        logger.warning("Neon Auth JWKS verification failed: %s", exc)
        return None

    if not payload.get("sub"):
        return None
    return payload

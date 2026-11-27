"""Security utilities: password hashing, JWT tokens, Fernet encryption, sanitization."""
from __future__ import annotations

import base64
import hashlib
import html
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from app.core.config import get_settings

# Patterns commonly used in prompt injection inside untrusted comments
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WHITESPACE_RE = re.compile(r"\s+")
_FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]")


def _password_bytes(password: str) -> bytes:
    """Encode password as UTF-8, bounded to bcrypt's 72-byte input limit."""
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(_password_bytes(password), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(_password_bytes(plain_password), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def hash_token(token: str) -> str:
    """SHA-256 hash for storing refresh/reset tokens securely."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    subject: str,
    role: str = "user",
    expires_delta: Optional[timedelta] = None,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_hex(12),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> tuple[str, datetime]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_hex(16),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expire


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


def _get_fernet() -> Fernet:
    settings = get_settings()
    raw_key = settings.OAUTH_ENCRYPTION_KEY.strip()
    if raw_key:
        return Fernet(raw_key.encode("utf-8"))
    # Deterministic derivation from SECRET_KEY when explicit Fernet key not set
    digest = hashlib.sha256(f"tubemind-oauth:{settings.SECRET_KEY}".encode("utf-8")).digest()
    derived = base64.urlsafe_b64encode(digest)
    return Fernet(derived)


def encrypt_secret(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""


def sanitize_untrusted_text(text: str, max_length: int = 2000) -> str:
    """Sanitize untrusted UGC (e.g. YouTube comments) before storage or LLM input.

    Strips control characters, unescapes HTML entities cleanly, normalizes whitespace,
    and truncates to a bounded length so untrusted text cannot overwhelm prompts.
    """
    if not text:
        return ""
    cleaned = html.unescape(text)
    cleaned = _CONTROL_CHARS_RE.sub("", cleaned)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "..."
    return cleaned


def sanitize_filename(filename: str) -> str:
    """Produce a safe basename preventing path traversal."""
    base = filename.replace("\\", "/").split("/")[-1]
    base = _FILENAME_SAFE_RE.sub("_", base).strip("._")
    if not base:
        base = "upload.mp4"
    return base[:140]


def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)

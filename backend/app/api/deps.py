"""FastAPI authentication and authorization dependencies."""
from __future__ import annotations

from typing import Optional

from fastapi import Cookie, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

ACCESS_COOKIE_NAME = "ci_access_token"
REFRESH_COOKIE_NAME = "ci_refresh_token"

bearer_scheme = HTTPBearer(auto_error=False)


def _strip_bearer_prefix(raw_value: Optional[str]) -> Optional[str]:
    if not raw_value:
        return None
    value = raw_value.strip()
    if not value:
        return None
    if value.lower().startswith("bearer "):
        token = value[7:].strip()
        return token or None
    return value


def extract_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = None,
    x_auth_token: Optional[str] = None,
    x_authorization: Optional[str] = None,
    cookie_token: Optional[str] = None,
) -> Optional[str]:
    """Extract JWT access token from Authorization header, fallback headers, or HttpOnly cookie."""
    if credentials and credentials.scheme.lower() == "bearer" and credentials.credentials:
        token = credentials.credentials.strip()
        if token:
            return token
    for fallback in (x_auth_token, x_authorization, cookie_token):
        token = _strip_bearer_prefix(fallback)
        if token:
            return token
    return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    x_authorization: Optional[str] = Header(default=None, alias="X-Authorization"),
    cookie_token: Optional[str] = Cookie(default=None, alias=ACCESS_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> User:
    token = extract_bearer_token(
        credentials=credentials,
        x_auth_token=x_auth_token,
        x_authorization=x_authorization,
        cookie_token=cookie_token,
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Bearer access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    user = (
        db.query(User)
        .options(joinedload(User.profile), joinedload(User.settings))
        .filter(User.id == user_id)
        .first()
    )
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated.",
        )
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role is required for this endpoint.",
        )
    return current_user

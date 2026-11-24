"""Server-side signed visual SVG CAPTCHA generator and single-use verifier."""
from __future__ import annotations

import base64
import hashlib
import hmac
import random
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple

from jose import JWTError, jwt

from app.core.config import get_settings

# Exclude ambiguous characters (0, O, 1, I, l)
_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
_CAPTCHA_TTL_SECONDS = 300
_USED_JTIS: Dict[str, float] = {}
_LOCK = threading.Lock()


def _prune_used_jtis(now_ts: float) -> None:
    expired = [k for k, exp in _USED_JTIS.items() if exp <= now_ts]
    for k in expired:
        _USED_JTIS.pop(k, None)


def _answer_digest(answer: str, jti: str, secret: str) -> str:
    normalized = answer.strip().upper()
    msg = f"{jti}:{normalized}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def _render_captcha_svg(code: str) -> str:
    rng = random.SystemRandom()
    width, height = 180, 56

    lines = []
    for _ in range(6):
        x1 = rng.randint(4, 50)
        y1 = rng.randint(6, height - 6)
        x2 = rng.randint(130, width - 4)
        y2 = rng.randint(6, height - 6)
        stroke = rng.choice(["#168A57", "#E9A22E", "#2D6A4F", "#40916C"])
        opacity = f"{rng.uniform(0.28, 0.55):.2f}"
        lines.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{stroke}" stroke-width="1.4" opacity="{opacity}" />'
        )

    dots = []
    for _ in range(28):
        cx = rng.randint(6, width - 6)
        cy = rng.randint(6, height - 6)
        r = f"{rng.uniform(0.9, 2.0):.1f}"
        fill = rng.choice(["#F7F6F0", "#E9A22E", "#52B788"])
        dots.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" opacity="0.35" />')

    chars = []
    step = 30
    start_x = 24
    for idx, ch in enumerate(code):
        x = start_x + idx * step + rng.randint(-3, 3)
        y = 37 + rng.randint(-5, 5)
        rot = rng.randint(-18, 18)
        fill = "#E9A22E" if idx % 2 == 1 else "#F7F6F0"
        font_size = rng.randint(24, 28)
        chars.append(
            f'<text x="{x}" y="{y}" fill="{fill}" font-family="monospace, sans-serif" '
            f'font-size="{font_size}" font-weight="800" '
            f'transform="rotate({rot} {x} {y})">{ch}</text>'
        )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        f'<rect width="{width}" height="{height}" rx="10" fill="#0B2A22" />'
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="9" '
        f'fill="none" stroke="#168A57" stroke-opacity="0.45" stroke-width="1.5" />'
        f'{"".join(lines)}{"".join(dots)}{"".join(chars)}'
        f"</svg>"
    )
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def generate_captcha_challenge() -> Tuple[str, str, int]:
    """Generate a signed CAPTCHA token and its base64 SVG data URL."""
    settings = get_settings()
    rng = random.SystemRandom()
    code = "".join(rng.choice(_ALPHABET) for _ in range(5))
    jti = secrets.token_hex(12)
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=_CAPTCHA_TTL_SECONDS)

    payload = {
        "type": "captcha",
        "jti": jti,
        "ans": _answer_digest(code, jti, settings.SECRET_KEY),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, _render_captcha_svg(code), _CAPTCHA_TTL_SECONDS


def verify_captcha_challenge(captcha_token: str | None, captcha_answer: str | None) -> Tuple[bool, str]:
    """Verify a signed single-use CAPTCHA challenge."""
    if not captcha_token or not captcha_answer or not captcha_answer.strip():
        return False, "Please complete the security CAPTCHA verification."

    settings = get_settings()
    try:
        decoded = jwt.decode(
            captcha_token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        return False, "CAPTCHA has expired or is invalid. Please refresh and try again."

    if decoded.get("type") != "captcha":
        return False, "Invalid CAPTCHA challenge token."

    jti = str(decoded.get("jti") or "")
    expected = str(decoded.get("ans") or "")
    exp_ts = float(decoded.get("exp") or 0)
    if not jti or not expected:
        return False, "Malformed CAPTCHA challenge."

    now_ts = time.time()
    with _LOCK:
        _prune_used_jtis(now_ts)
        if jti in _USED_JTIS:
            return False, "CAPTCHA challenge has already been used. Please refresh."
        _USED_JTIS[jti] = max(exp_ts, now_ts + _CAPTCHA_TTL_SECONDS)

    actual = _answer_digest(captcha_answer, jti, settings.SECRET_KEY)
    if not hmac.compare_digest(actual, expected):
        return False, "Incorrect CAPTCHA code. Please try again."

    return True, "ok"

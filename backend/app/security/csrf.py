"""
CSRF token generation and validation — P2 security module.

Design decisions (WB-03):
- Per-session CSRF secret stored server-side in PostgreSQL Session row.
- CSRF token is HMAC-SHA256(session.csrf_secret, session.id) sent in X-CSRF-Token header.
- Never stored in localStorage. Frontend fetches it from GET /auth/me response.
- Checked on all authenticated mutations (POST/PATCH/DELETE) except session creation.
"""
from __future__ import annotations

import hashlib
import hmac

from fastapi import Request

from backend.app.core.errors import ErrorCode, make_error


def generate_csrf_token(session_csrf_secret: str, session_id: str) -> str:
    """
    Deterministic CSRF token from per-session secret and session ID.
    The same session always produces the same token (for frontend convenience).
    """
    mac = hmac.new(
        session_csrf_secret.encode(),
        session_id.encode(),
        hashlib.sha256,
    )
    return mac.hexdigest()


def verify_csrf_token(
    token_from_header: str,
    session_csrf_secret: str,
    session_id: str,
) -> bool:
    """Constant-time comparison of submitted CSRF token against expected."""
    if not isinstance(token_from_header, str):
        return False
    expected = generate_csrf_token(session_csrf_secret, session_id)
    return hmac.compare_digest(expected, token_from_header)


def require_csrf(request: Request, session_csrf_secret: str, session_id: str):
    """
    Validate Origin + CSRF token on mutating requests.
    Raises JSONResponse (via return) if invalid — caller must return it.
    Returns None if valid.
    """
    # Origin validation is done separately in middleware/router
    csrf_header = request.headers.get("X-CSRF-Token", "")
    if not csrf_header:
        return make_error(
            code=ErrorCode.CSRF_REJECTED,
            message="X-CSRF-Token header is required for this operation.",
            http_status=403,
        )
    if not verify_csrf_token(csrf_header, session_csrf_secret, session_id):
        return make_error(
            code=ErrorCode.CSRF_REJECTED,
            message="CSRF token is invalid or expired.",
            http_status=403,
        )
    return None

"""
Durable opaque session management — P2 security module.

Design decisions (WB-03):
- Random 32-byte session token issued as HttpOnly cookie, never in response body.
- Only SHA-256(token) stored in PostgreSQL — raw token never touches the DB.
- Per-session CSRF secret generated at session creation time.
- 24-hour absolute lifetime, no sliding extension.
- Multiple sessions per user allowed (multiple devices); same account = one entry.
- Redis failure does NOT erase sessions (PostgreSQL is authoritative).
- Revocation marks revoked_at; expired/revoked sessions return 401.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.clock import utc_now
from backend.app.core.config import get_settings
from backend.app.persistence.models import Session, User

COOKIE_NAME = "fd_session"


def _token_digest(raw_token: str) -> str:
    """SHA-256 of the raw session token, stored server-side."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _session_digest_hmac(raw_token: str, key: str) -> str:
    """
    Keyed HMAC-SHA256(SESSION_DIGEST_KEY, raw_token).
    Used as the DB lookup key instead of plain SHA-256 for key-committed storage.
    """
    mac = hmac.new(
        key.encode(),
        raw_token.encode(),
        hashlib.sha256,
    )
    return mac.hexdigest()


async def create_session(
    db: AsyncSession,
    user_id: str,
    request_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> tuple[str, "Session"]:
    """
    Create a new durable session.
    Returns (raw_token, Session ORM object).
    The raw_token is sent to the browser as an HttpOnly cookie.
    It is NOT stored in the database.
    """
    settings = get_settings()
    raw_token = secrets.token_hex(32)  # 64 hex chars, 256 bits of entropy
    digest = _session_digest_hmac(raw_token, settings.SESSION_DIGEST_KEY)
    csrf_secret = secrets.token_hex(32)

    now = utc_now()
    expires_at = now + timedelta(seconds=settings.SESSION_LIFETIME_SECONDS)

    # Hash UA for audit without storing raw UA
    ua_hash = None
    if user_agent:
        ua_hash = hashlib.sha256(user_agent.encode()).hexdigest()[:16]

    session = Session(
        user_id=user_id,
        token_digest=digest,
        csrf_secret=csrf_secret,
        expires_at=expires_at,
        created_ip=request_ip,  # Trusted proxy IP only (set by caller)
        user_agent_hash=ua_hash,
    )
    db.add(session)
    await db.flush()  # Assigns session.id
    return raw_token, session


async def get_session_by_token(
    db: AsyncSession,
    raw_token: str,
) -> Optional["Session"]:
    """
    Look up and validate a session by raw token.
    Returns None if not found, expired, or revoked.
    """
    settings = get_settings()
    digest = _session_digest_hmac(raw_token, settings.SESSION_DIGEST_KEY)
    result = await db.execute(
        select(Session)
        .where(Session.token_digest == digest)
    )
    session = result.scalar_one_or_none()
    if session is None:
        return None
    if not session.is_valid:
        return None
    return session


async def revoke_session(
    db: AsyncSession,
    session: "Session",
) -> None:
    """Mark a session as revoked. Committed by caller."""
    session.revoked_at = utc_now()
    db.add(session)


def set_session_cookie(
    response: Response,
    raw_token: str,
) -> None:
    """Set the HttpOnly session cookie on the response."""
    settings = get_settings()
    response.set_cookie(
        key=COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.cookie_samesite,
        max_age=settings.SESSION_LIFETIME_SECONDS,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    """Clear the session cookie (on logout)."""
    settings = get_settings()
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.cookie_samesite,
        path="/",
    )


def get_raw_token_from_request(request: Request) -> Optional[str]:
    """Extract raw session token from cookie."""
    return request.cookies.get(COOKIE_NAME)


async def get_session_from_request(
    db: AsyncSession,
    request: Request,
) -> Optional["Session"]:
    """Convenience: extract cookie and look up session."""
    raw_token = get_raw_token_from_request(request)
    if not raw_token:
        return None
    return await get_session_by_token(db, raw_token)

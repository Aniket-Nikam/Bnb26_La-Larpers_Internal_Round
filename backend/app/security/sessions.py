"""Opaque P2 sessions on the shared PostgreSQL transaction system."""

import hashlib
import hmac
import secrets
from datetime import timedelta

from sqlalchemy import select

from app.core.clock import db_now
from app.core.config import get_settings
from app.persistence.models import AccessCredential, Session, User

COOKIE_NAME = "fd_session"


def _session_digest_hmac(raw_token, key):
    return hmac.new(key.encode(), raw_token.encode(), hashlib.sha256).hexdigest()


def create_session(db, user_id, credential_id, **_):
    cfg = get_settings()
    raw = secrets.token_hex(32)
    now = db_now(db)
    session = Session(
        user_id=user_id,
        credential_id=credential_id,
        token_digest=_session_digest_hmac(raw, cfg.session_digest_key.get_secret_value()),
        csrf_secret=secrets.token_hex(32),
        created_at=now,
        expires_at=now + timedelta(hours=24),
    )
    db.add(session)
    db.flush()
    return raw, session


def get_session_by_token(db, raw_token):
    if not raw_token or len(raw_token) > 256:
        return None
    digest = _session_digest_hmac(raw_token, get_settings().session_digest_key.get_secret_value())
    now = db_now(db)
    return db.scalar(
        select(Session)
        .join(AccessCredential, Session.credential_id == AccessCredential.id)
        .join(User, User.id == Session.user_id)
        .where(
            Session.token_digest == digest,
            Session.revoked_at.is_(None),
            Session.expires_at > now,
            AccessCredential.user_id == Session.user_id,
            AccessCredential.revoked_at.is_(None),
            (AccessCredential.expires_at.is_(None) | (AccessCredential.expires_at > now)),
            User.is_active,
        )
    )


def get_session_from_request(db, request):
    return get_session_by_token(db, request.cookies.get(COOKIE_NAME))


def revoke_session(db, session):
    session.revoked_at = db_now(db)


def set_session_cookie(response, raw_token):
    response.set_cookie(
        COOKIE_NAME,
        raw_token,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="lax",
        max_age=86400,
        path="/",
    )


def clear_session_cookie(response):
    response.delete_cookie(
        COOKIE_NAME, httponly=True, secure=get_settings().cookie_secure, samesite="lax", path="/"
    )

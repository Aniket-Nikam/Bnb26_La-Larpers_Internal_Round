"""Offline credential provisioning; raw credentials never persist in PostgreSQL."""

import hashlib
import hmac

from sqlalchemy import select

from app.core.clock import db_now
from app.core.config import get_settings
from app.persistence.models import AccessCredential, User


def _credential_digest(raw_code):
    return hmac.new(
        get_settings().credential_digest_key.get_secret_value().encode(),
        raw_code.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_credential(db, raw_code):
    now = db_now(db)
    credential = db.scalar(
        select(AccessCredential).where(
            AccessCredential.digest == _credential_digest(raw_code),
            AccessCredential.revoked_at.is_(None),
            AccessCredential.expires_at.is_(None) | (AccessCredential.expires_at > now),
        )
    )
    if credential is None:
        return None
    user = db.get(User, credential.user_id)
    return (user, credential) if user and user.is_active else None


def provision_credential(db, user_id, raw_code, label=None, expires_at=None, **_):
    if len(raw_code) < 16 or len(raw_code) > 256:
        raise ValueError("Access codes must be 16..256 characters")
    credential = AccessCredential(
        user_id=user_id, digest=_credential_digest(raw_code), expires_at=expires_at, label=label
    )
    db.add(credential)
    db.flush()
    return credential


def provision_user_with_credential(db, display_name, role, raw_code, label=None, expires_at=None):
    if get_settings().app_profile == "normal":
        raise RuntimeError("Fixture provisioning requires demo/test profile")
    if role not in {"participant", "organizer", "admin"} or not 1 <= len(display_name) <= 100:
        raise ValueError("Invalid provisioned identity")
    user = User(display_name=display_name, role=role)
    db.add(user)
    db.flush()
    return user, provision_credential(db, user.id, raw_code, label, expires_at)


def revoke_credential(db, credential_id, **_):
    credential = db.get(AccessCredential, credential_id)
    if credential is None:
        return False
    credential.revoked_at = db_now(db)
    return True

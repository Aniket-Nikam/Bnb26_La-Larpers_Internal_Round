"""
Credential provisioning — P2 security module.

Design decisions (WB-03):
- Access codes are provisioned externally (organizer/admin setup only).
- Store HMAC-SHA256(CREDENTIAL_DIGEST_KEY, raw_code) — never raw codes.
- Login does NOT create a new user or eligibility grant.
- Multiple logins with same credential map to same stable user.
- Organizer/admin roles are provisioned here, not self-assignable.
- Demo credentials only usable in demo/test profile.
- Raw credentials never appear in logs, errors, or responses.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.clock import utc_now
from backend.app.core.config import AppProfile, get_settings
from backend.app.persistence.models import AccessCredential, User

logger = logging.getLogger(__name__)

# Redact sentinel for credential logging
_REDACTED = "[REDACTED]"


def _credential_digest(raw_code: str) -> str:
    """HMAC-SHA256(CREDENTIAL_DIGEST_KEY, raw_code) as hex."""
    settings = get_settings()
    mac = hmac.new(
        settings.CREDENTIAL_DIGEST_KEY.encode(),
        raw_code.encode(),
        hashlib.sha256,
    )
    return mac.hexdigest()


def _credential_redis_key(raw_code: str) -> str:
    """
    Redis key for rate-limiting credential attempts.
    Uses digest-derived key — raw code never goes into Redis keys.
    """
    digest = _credential_digest(raw_code)
    # Use first 16 chars of digest as the key fragment
    return f"cred_attempt:{digest[:16]}"


async def verify_credential(
    db: AsyncSession,
    raw_code: str,
) -> Optional[User]:
    """
    Verify a raw access code and return the associated User if valid.
    Returns None if invalid, revoked, or expired.
    Never logs the raw code.
    """
    if not raw_code or len(raw_code) > 256:
        logger.warning("Credential attempt with invalid length")
        return None

    digest = _credential_digest(raw_code)

    result = await db.execute(
        select(AccessCredential)
        .where(AccessCredential.credential_digest == digest)
    )
    credential = result.scalar_one_or_none()

    if credential is None:
        logger.info("Credential attempt: no matching digest found")
        return None

    if not credential.is_valid:
        logger.info(
            "Credential attempt: credential id=%s is invalid (revoked or expired)",
            credential.id,
        )
        return None

    # Load the user
    result2 = await db.execute(
        select(User).where(User.id == credential.user_id)
    )
    user = result2.scalar_one_or_none()

    if user is None or not user.is_active:
        logger.info("Credential attempt: user not found or inactive for credential id=%s", credential.id)
        return None

    logger.info("Credential verified for user_id=%s", user.id)
    return user


async def provision_credential(
    db: AsyncSession,
    user_id: str,
    raw_code: str,
    label: Optional[str] = None,
    expires_at=None,
    issuer_user_id: Optional[str] = None,
) -> AccessCredential:
    """
    Internal provisioning utility — creates a credential for a user.
    Only callable from admin/organizer setup scripts, never from public API.
    Raw code is never stored; only the digest is persisted.
    """
    settings = get_settings()

    # Reject fixture credentials in normal profile
    if settings.APP_PROFILE == AppProfile.normal:
        raise RuntimeError(
            "Credential provisioning is not available in normal profile. "
            "Use the demo_seed script with demo profile."
        )

    if not raw_code or len(raw_code) < 16:
        raise ValueError("Access code must be at least 16 characters")

    digest = _credential_digest(raw_code)

    # Check for duplicate
    existing = await db.execute(
        select(AccessCredential).where(AccessCredential.credential_digest == digest)
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError("A credential with this code already exists")

    credential = AccessCredential(
        user_id=user_id,
        credential_digest=digest,
        issued_at=utc_now(),
        expires_at=expires_at,
        label=label,
    )
    db.add(credential)
    await db.flush()

    logger.info(
        "Provisioned credential id=%s for user_id=%s label=%s by issuer=%s",
        credential.id,
        user_id,
        label or "(none)",
        issuer_user_id or "system",
    )
    return credential


async def provision_user_with_credential(
    db: AsyncSession,
    display_name: str,
    role: str,
    raw_code: str,
    label: Optional[str] = None,
    expires_at=None,
) -> tuple[User, AccessCredential]:
    """
    Create a new user and immediately provision a credential for them.
    Demo/test profile only. Never callable from public API.
    """
    settings = get_settings()
    if settings.APP_PROFILE == AppProfile.normal:
        raise RuntimeError("User provisioning only available in demo/test profile.")

    import uuid

    user = User(
        display_name=display_name,
        role=role,
        timezone="UTC",
    )
    db.add(user)
    await db.flush()

    credential = await provision_credential(
        db=db,
        user_id=user.id,
        raw_code=raw_code,
        label=label,
        expires_at=expires_at,
    )

    return user, credential


async def revoke_credential(
    db: AsyncSession,
    credential_id: str,
    revoked_by: Optional[str] = None,
) -> bool:
    """Revoke a credential by ID. Returns True if found and revoked."""
    result = await db.execute(
        select(AccessCredential).where(AccessCredential.id == credential_id)
    )
    credential = result.scalar_one_or_none()
    if credential is None:
        return False
    credential.revoked_at = utc_now()
    db.add(credential)
    logger.info(
        "Credential id=%s revoked by=%s",
        credential_id,
        revoked_by or "system",
    )
    return True

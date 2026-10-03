"""
Authorization helpers — P2 security module.

Exposes the mounted interfaces specified in architecture.md section 11:
  - get_principal(request) -> Principal
  - require_organizer(request) -> Principal
  - require_drop_access(principal, drop_id) -> None (raises on fail)
  - enforce_limit(request, principal, action) -> LimitResult

Design decisions:
- Deny by default: no principal = 401.
- Role checks are server-side; no frontend route guard substitution.
- Cross-account access to receipts/reservations returns 404 (non-disclosure).
- Organizer role + drop ownership both required for admin operations.
- Admin role bypasses ownership check.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.errors import ErrorCode, make_error
from backend.app.persistence.database import get_db
from backend.app.persistence.models import EligibilityGrant, Session, User
from backend.app.security.sessions import get_session_from_request

logger = logging.getLogger(__name__)


class Principal(BaseModel):
    """
    Exact contracted principal type per architecture.md section 12.2.
    Returned in SessionResponse and used throughout security.
    """
    id: str
    public_id: str
    role: str  # participant | organizer | admin
    display_name: str
    timezone: str

    model_config = {"from_attributes": True}


class AuthContext(BaseModel):
    """Full authentication context carried through request handling."""
    principal: Principal
    session_id: str
    csrf_secret: str  # Server-side only — never sent to client
    expires_at: str   # ISO 8601 UTC

    model_config = {"arbitrary_types_allowed": True}


def _build_principal(user: User) -> Principal:
    return Principal(
        id=user.id,
        public_id=user.public_id,
        role=user.role,
        display_name=user.display_name,
        timezone=user.timezone,
    )


async def get_optional_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[AuthContext]:
    """
    Dependency: returns AuthContext if a valid session cookie is present, else None.
    Does NOT raise on missing/invalid session.
    """
    session = await get_session_from_request(db, request)
    if session is None:
        return None

    result = await db.execute(select(User).where(User.id == session.user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None

    return AuthContext(
        principal=_build_principal(user),
        session_id=session.id,
        csrf_secret=session.csrf_secret,
        expires_at=session.expires_at.isoformat().replace("+00:00", "Z"),
    )


async def get_principal(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    """
    Dependency: requires an authenticated session.
    Returns AuthContext or raises 401 SESSION_REQUIRED.
    """
    ctx = await get_optional_auth(request, db)
    if ctx is None:
        raise make_error_exception(
            code=ErrorCode.SESSION_REQUIRED,
            message="Authentication required. Please log in.",
            http_status=401,
        )
    return ctx


async def require_organizer(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    """
    Dependency: requires organizer or admin role.
    Returns AuthContext or raises 403 FORBIDDEN.
    """
    ctx = await get_principal(request, db)
    if ctx.principal.role not in ("organizer", "admin"):
        raise make_error_exception(
            code=ErrorCode.FORBIDDEN,
            message="Organizer access required.",
            http_status=403,
        )
    return ctx


async def require_drop_access(
    principal: Principal,
    drop_id: str,
    db: AsyncSession,
) -> None:
    """
    Verify that principal is the organizer who owns this drop, or admin.
    Raises 403 FORBIDDEN on failure. Caller must import this and invoke explicitly.
    """
    if principal.role == "admin":
        return  # Admin bypasses ownership

    try:
        from backend.app.persistence.models import Drop  # P1 model
        result = await db.execute(select(Drop).where(Drop.id == drop_id))
        drop = result.scalar_one_or_none()
        if drop is None:
            raise make_error_exception(
                code=ErrorCode.NOT_FOUND,
                message="Drop not found.",
                http_status=404,
            )
        if drop.owner_id != principal.id:
            raise make_error_exception(
                code=ErrorCode.FORBIDDEN,
                message="You do not have permission to manage this drop.",
                http_status=403,
            )
    except (ImportError, AttributeError):
        raise make_error_exception(
            code=ErrorCode.NOT_IMPLEMENTED,
            message="Drop domain model not yet integrated by P1.",
            http_status=501,
        )


async def check_drop_grant(
    principal: Principal,
    drop_id: str,
    db: AsyncSession,
) -> bool:
    """
    Returns True if principal has an active EligibilityGrant for this drop.
    Used by P1's entry routes.
    """
    result = await db.execute(
        select(EligibilityGrant)
        .where(
            EligibilityGrant.drop_id == drop_id,
            EligibilityGrant.user_id == principal.id,
            EligibilityGrant.revoked_at.is_(None),
        )
    )
    return result.scalar_one_or_none() is not None


# ---- HTTP exception helper ------------------------------------------------

class HTTPSecurityError(Exception):
    """Raised by authorization helpers; caught by FastAPI exception handler."""
    def __init__(self, response):
        self.response = response
        super().__init__(str(response))


def make_error_exception(code: str, message: str, http_status: int) -> HTTPSecurityError:
    response = make_error(code=code, message=message, http_status=http_status)
    return HTTPSecurityError(response)

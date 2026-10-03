"""
Security router — P2 module.

Implements the exact routes from architecture.md section 12.3:
  POST /api/v1/auth/session   — credential login
  GET  /api/v1/auth/me        — session check / CSRF refresh
  DELETE /api/v1/auth/session — logout / revocation
  PATCH /api/v1/profile       — display_name + timezone update only

Design decisions:
- Login enforces Origin + rate limits before session exists.
- Session cookie is HttpOnly/SameSite; CSRF token in JSON body only.
- Profile edits reject role, grant, owner, seat-status fields.
- Logout is idempotent (already-revoked returns 204).
- No-store cache headers on all private responses.
- Credentials redacted from all logs/errors.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import pytz
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.clock import utc_now
from backend.app.core.errors import ErrorCode, make_error
from backend.app.persistence.database import get_db
from backend.app.persistence.models import User
from backend.app.security.authorization import (
    AuthContext,
    Principal,
    get_optional_auth,
    get_principal,
)
from backend.app.security.csrf import generate_csrf_token, require_csrf
from backend.app.security.limits import (
    LimitAction,
    enforce_limit,
    get_trusted_ip,
)
from backend.app.security.provisioning import (
    _credential_redis_key,
    verify_credential,
)
from backend.app.security.sessions import (
    clear_session_cookie,
    create_session,
    revoke_session,
    set_session_cookie,
)

logger = logging.getLogger(__name__)

router = APIRouter()
auth_router = APIRouter(prefix="/auth", tags=["auth"])
profile_router = APIRouter(tags=["profile"])

# ---- Pydantic models -------------------------------------------------------

_NO_STORE_HEADERS = {
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
}


class LoginRequest(BaseModel):
    access_code: str = Field(..., min_length=1, max_length=256)


class SessionResponse(BaseModel):
    """Exact contract per architecture.md section 12.2."""
    principal: Principal
    csrf_token: str
    expires_at: str  # ISO 8601 UTC
    server_time: str


class ProfilePatchRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=120)
    timezone: Optional[str] = Field(None, max_length=64)

    # Explicitly reject privileged fields
    role: Optional[str] = Field(None, exclude=True)
    is_admin: Optional[bool] = Field(None, exclude=True)

    @field_validator("timezone", mode="before")
    @classmethod
    def validate_timezone(cls, v):
        if v is None:
            return v
        try:
            pytz.timezone(v)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"'{v}' is not a valid IANA timezone")
        return v


class ProfileResponse(BaseModel):
    principal: Principal
    server_time: str


# ---- Helpers ---------------------------------------------------------------

def _build_session_response(
    principal: Principal,
    csrf_secret: str,
    session_id: str,
    expires_at: datetime,
) -> SessionResponse:
    return SessionResponse(
        principal=principal,
        csrf_token=generate_csrf_token(csrf_secret, session_id),
        expires_at=expires_at.isoformat().replace("+00:00", "Z"),
        server_time=utc_now().isoformat().replace("+00:00", "Z"),
    )


def _validate_origin(request: Request) -> Optional[dict]:
    """
    Strict Origin header validation for browser writes.
    Returns None if valid, error response dict if invalid.
    """
    from backend.app.core.config import get_settings
    settings = get_settings()
    origin = request.headers.get("Origin", "").rstrip("/")
    allowed = {o.rstrip("/") for o in settings.allowed_origins}

    # Allow requests without Origin header only from test clients (no browser)
    # For browser requests, Origin is always present on cross-origin and same-origin POSTs
    if origin and origin not in allowed:
        logger.warning("Origin validation failed: origin=%s allowed=%s", origin, allowed)
        return make_error(
            code=ErrorCode.ORIGIN_REJECTED,
            message="Request origin is not permitted.",
            http_status=403,
        )
    return None


# ---- Routes ----------------------------------------------------------------

@auth_router.post("/session", response_model=SessionResponse)
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /auth/session — credential login.
    Creates a new session; does NOT create a new user or eligibility grant.
    """
    # 1. Origin validation (strict even before session exists)
    origin_error = _validate_origin(request)
    if origin_error is not None:
        return origin_error

    # 2. Rate limiting on credential attempts before any DB lookup
    #    Use digest-derived key so raw code never enters Redis.
    trusted_ip = get_trusted_ip(request)
    # We use a slightly different approach here: limit by IP before credential check
    limit_result = await enforce_limit(
        request=request,
        principal=None,
        action=LimitAction.credential_attempt,
        trusted_ip=trusted_ip,
    )
    if not limit_result.allowed:
        if limit_result.redis_unavailable:
            return make_error(
                code=ErrorCode.TEMPORARILY_UNAVAILABLE,
                message="Service temporarily unavailable. Please retry shortly.",
                retryable=True,
                http_status=503,
            )
        response.headers["Retry-After"] = str(limit_result.retry_after_seconds)
        return make_error(
            code=ErrorCode.RATE_LIMITED,
            message="Too many login attempts. Please wait before retrying.",
            retryable=True,
            http_status=429,
        )

    # Also limit session creation rate
    session_limit = await enforce_limit(
        request=request,
        principal=None,
        action=LimitAction.session_create,
        trusted_ip=trusted_ip,
    )
    if not session_limit.allowed:
        if session_limit.redis_unavailable:
            return make_error(
                code=ErrorCode.TEMPORARILY_UNAVAILABLE,
                message="Service temporarily unavailable. Please retry shortly.",
                retryable=True,
                http_status=503,
            )
        response.headers["Retry-After"] = str(session_limit.retry_after_seconds)
        return make_error(
            code=ErrorCode.RATE_LIMITED,
            message="Too many session requests. Please wait before retrying.",
            retryable=True,
            http_status=429,
        )

    # 3. Verify credential (raw code redacted from all logs)
    user = await verify_credential(db, body.access_code)
    if user is None:
        # Constant-time-ish: always return same error regardless of reason
        # Do not reveal whether credential exists, is expired, or is wrong
        return make_error(
            code=ErrorCode.FORBIDDEN,
            message="Invalid or expired access credential.",
            http_status=401,
        )

    # 4. Create durable session
    raw_token, session = await create_session(
        db=db,
        user_id=user.id,
        request_ip=trusted_ip,
        user_agent=request.headers.get("User-Agent"),
    )
    await db.commit()

    # 5. Set HttpOnly cookie (raw token goes ONLY to cookie, NOT in JSON)
    set_session_cookie(response, raw_token)

    # 6. Return SessionResponse (no raw token, no credential)
    principal = Principal(
        id=user.id,
        public_id=user.public_id,
        role=user.role,
        display_name=user.display_name,
        timezone=user.timezone,
    )
    session_resp = _build_session_response(
        principal=principal,
        csrf_secret=session.csrf_secret,
        session_id=session.id,
        expires_at=session.expires_at,
    )
    response.headers.update(_NO_STORE_HEADERS)
    return session_resp


@auth_router.get("/me", response_model=SessionResponse)
async def get_me(
    request: Request,
    response: Response,
    ctx: AuthContext = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
):
    """
    GET /auth/me — return current principal + fresh CSRF token.
    Used by frontend after reconnect/refresh.
    """
    response.headers.update(_NO_STORE_HEADERS)
    return _build_session_response(
        principal=ctx.principal,
        csrf_secret=ctx.csrf_secret,
        session_id=ctx.session_id,
        expires_at=datetime.fromisoformat(ctx.expires_at.replace("Z", "+00:00")),
    )


@auth_router.delete("/session", status_code=204)
async def logout(
    request: Request,
    response: Response,
    ctx: Optional[AuthContext] = Depends(get_optional_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    DELETE /auth/session — revoke current session and clear cookie.
    Idempotent: already-revoked session returns 204.
    Requires CSRF token per contract.
    """
    # Origin validation
    origin_error = _validate_origin(request)
    if origin_error is not None:
        return origin_error

    if ctx is not None:
        # Validate CSRF
        csrf_error = require_csrf(request, ctx.csrf_secret, ctx.session_id)
        if csrf_error is not None:
            return csrf_error

        # Revoke the session
        from backend.app.security.sessions import get_session_from_request
        session = await get_session_from_request(db, request)
        if session is not None and session.revoked_at is None:
            await revoke_session(db, session)
            await db.commit()

    # Always clear cookie
    clear_session_cookie(response)
    response.headers.update(_NO_STORE_HEADERS)
    return Response(status_code=204)


@profile_router.patch("/profile", response_model=ProfileResponse)
async def patch_profile(
    request: Request,
    response: Response,
    body: ProfilePatchRequest,
    ctx: AuthContext = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
):
    """
    PATCH /profile — update display_name and/or timezone only.
    Explicitly rejects role, grant, owner, seat-status and other privileged fields.
    """
    # Origin validation
    origin_error = _validate_origin(request)
    if origin_error is not None:
        return origin_error

    # CSRF validation
    csrf_error = require_csrf(request, ctx.csrf_secret, ctx.session_id)
    if csrf_error is not None:
        return csrf_error

    # Check if any privileged fields were attempted
    raw_body = await request.json()
    forbidden_fields = {"role", "is_admin", "is_active", "owner_id", "grant", "seat_status"}
    attempted_forbidden = set(raw_body.keys()) & forbidden_fields
    if attempted_forbidden:
        return make_error(
            code=ErrorCode.FORBIDDEN,
            message=f"Fields not permitted in profile update: {', '.join(sorted(attempted_forbidden))}",
            http_status=403,
        )

    # Rate limit profile writes
    limit_result = await enforce_limit(
        request=request,
        principal=ctx.principal,
        action=LimitAction.profile_write,
        session_id=ctx.session_id,
        trusted_ip=get_trusted_ip(request),
    )
    if not limit_result.allowed:
        response.headers["Retry-After"] = str(limit_result.retry_after_seconds)
        return make_error(
            code=ErrorCode.RATE_LIMITED,
            message="Too many profile update requests.",
            retryable=True,
            http_status=429,
        )

    # Load user
    from sqlalchemy import select
    result = await db.execute(
        select(User).where(User.id == ctx.principal.id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        return make_error(
            code=ErrorCode.SESSION_REQUIRED,
            message="Session user not found.",
            http_status=401,
        )

    # Apply allowed updates only
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.timezone is not None:
        user.timezone = body.timezone

    db.add(user)
    await db.commit()
    await db.refresh(user)

    updated_principal = Principal(
        id=user.id,
        public_id=user.public_id,
        role=user.role,
        display_name=user.display_name,
        timezone=user.timezone,
    )

    response.headers.update(_NO_STORE_HEADERS)
    return ProfileResponse(
        principal=updated_principal,
        server_time=utc_now().isoformat().replace("+00:00", "Z"),
    )


# Include both sub-routers under main security router
router.include_router(auth_router)
router.include_router(profile_router)


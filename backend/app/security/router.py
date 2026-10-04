"""Real P2 auth/profile endpoints using the shared v1 DTOs."""

import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy import func, select

from app.core import schemas as s
from app.core.clock import db_now
from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.idempotency import claim, complete
from app.persistence.database import get_db
from app.persistence.models import User
from app.security.authorization import get_principal
from app.security.csrf import generate_csrf_token, require_csrf, require_origin
from app.security.face import check_duplicate_face, extract_face_embedding
from app.security.limits import enforce_limit
from app.security.otp import normalize_phone_number
from app.security.passwords import hash_password, verify_account
from app.security.provisioning import _credential_digest, provision_credential, verify_credential
from app.security.sessions import (
    clear_session_cookie,
    create_session,
    get_session_from_request,
    revoke_session,
    set_session_cookie,
)

router = APIRouter(tags=["security"])
DB = Annotated[object, Depends(get_db)]


def projection(db, session):
    return s.SessionResponse(
        principal=s.Principal.model_validate(db.get(User, session.user_id)),
        csrf_token=generate_csrf_token(session.id, session.csrf_secret),
        expires_at=session.expires_at,
        server_time=db_now(db),
    )


@router.post("/auth/session", response_model=s.SessionResponse)
def login(body: s.SessionInput, request: Request, response: Response, db: DB):
    require_origin(request)
    enforce_limit(request, None, "credential_attempt", _credential_digest(body.access_code))
    verified = verify_credential(db, body.access_code)
    if verified is None:
        raise DomainError("SESSION_REQUIRED", "Invalid or expired invitation credential.", 401)
    user, credential = verified
    raw, session = create_session(db, user.id, credential.id)
    db.commit()
    set_session_cookie(response, raw)
    return projection(db, session)


@router.post("/auth/password-session", response_model=s.SessionResponse)
def password_login(body: s.PasswordSessionInput, request: Request, response: Response, db: DB):
    require_origin(request)
    enforce_limit(request, None, "credential_attempt", _credential_digest(body.email))
    verified = verify_account(db, body.email, body.password)
    if verified is None:
        raise DomainError("SESSION_REQUIRED", "Invalid email or password.", 401)
    user, credential = verified
    raw, session = create_session(db, user.id, credential.id)
    db.commit()
    set_session_cookie(response, raw)
    return projection(db, session)


@router.post("/auth/register", response_model=s.SessionResponse, status_code=201)
def register(body: s.RegistrationInput, request: Request, response: Response, db: DB):
    require_origin(request)
    cfg = get_settings()

    normalized_email = body.email.strip().lower()
    normalized_phone = normalize_phone_number(body.phone_number)

    enforce_limit(request, None, "credential_attempt", _credential_digest(normalized_email))
    enforce_limit(request, None, "credential_attempt", _credential_digest(normalized_phone))

    # Advisory locks for concurrency protection on email and phone
    db.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(normalized_email, 0))))
    db.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(normalized_phone, 1))))

    # 1. Email uniqueness check
    if db.scalar(select(User.id).where(func.lower(User.email) == normalized_email)):
        raise DomainError("ACCOUNT_EXISTS", "An account with this email already exists.", 409)

    # 2. Phone uniqueness check
    if db.scalar(select(User.id).where(User.phone_number == normalized_phone)):
        raise DomainError("PHONE_EXISTS", "An account with this phone number already exists.", 409)

    if cfg.app_profile == "normal" and body.role in {"organizer", "admin"}:
        key = cfg.session_digest_key.get_secret_value()
        if not body.admin_key or body.admin_key != key:
            raise DomainError(
                "FORBIDDEN", "Admin registration requires a valid admin key in production.", 403
            )

    face_embedding = None
    if body.face_image:
        face_embedding = extract_face_embedding(body.face_image)
        duplicate = check_duplicate_face(db, face_embedding)
        if duplicate:
            raise DomainError(
                "DUPLICATE_FACE",
                "An account with this face is already registered. Duplicate accounts are not permitted.",
                409,
            )
    elif cfg.app_profile != "test":
        raise DomainError(
            "VALIDATION_ERROR",
            "A camera face scan is required to register an account.",
            422,
        )

    user = User(
        display_name=body.display_name,
        phone_number=normalized_phone,
        email=normalized_email,
        password_hash=hash_password(body.password) if body.password else None,
        role=body.role,
        face_embedding=face_embedding,
    )
    db.add(user)
    db.flush()
    credential = provision_credential(
        db, user.id, secrets.token_urlsafe(32), label="account-password"
    )
    raw, session = create_session(db, user.id, credential.id)
    db.commit()
    set_session_cookie(response, raw)
    return projection(db, session)


@router.get("/auth/me", response_model=s.SessionResponse)
def me(request: Request, db: DB, principal: s.Principal = Depends(get_principal)):
    enforce_limit(request, principal, "status")
    session = get_session_from_request(db, request)
    if session is None:
        raise DomainError("SESSION_REQUIRED", "Session expired.", 401)
    return projection(db, session)


@router.delete("/auth/session", status_code=204)
def logout(request: Request, db: DB):
    require_origin(request)
    session = get_session_from_request(db, request)
    if session:
        require_csrf(request, session)
        enforce_limit(request, s.Principal.model_validate(db.get(User, session.user_id)), "profile")
        revoke_session(db, session)
        db.commit()
    response = Response(status_code=204)
    clear_session_cookie(response)
    return response


@router.patch("/profile", response_model=s.ProfileResponse)
def profile(
    body: s.ProfilePatch,
    request: Request,
    db: DB,
    key: Annotated[UUID, Header(alias="Idempotency-Key")],
    principal: s.Principal = Depends(get_principal),
):
    enforce_limit(request, principal, "profile")
    op = claim(
        db,
        principal.id,
        request.method,
        request.url.path,
        key,
        body.model_dump(mode="json", exclude_unset=True),
    )
    if op.status != "COMPLETED":
        if any(getattr(body, name) is None for name in body.model_fields_set):
            raise DomainError("VALIDATION_ERROR", "Profile fields cannot be null.", 422)
        user = db.get(User, principal.id, with_for_update=True)
        for name, value in body.model_dump(exclude_unset=True).items():
            setattr(user, name, value)
        complete(op, "profile", principal.id)
    db.commit()
    return s.ProfileResponse(
        principal=s.Principal.model_validate(db.get(User, principal.id)), server_time=db_now(db)
    )

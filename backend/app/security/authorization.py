"""Mounted P2 hooks: authoritative PostgreSQL sessions and ownership."""

from fastapi import Request

from app.core.errors import DomainError
from app.core.schemas import Principal
from app.persistence.database import session_factory
from app.persistence.models import Drop, User
from app.security.csrf import require_csrf
from app.security.sessions import get_session_from_request

SECURITY_IMPLEMENTED = True


def get_principal(request: Request) -> Principal:
    with session_factory()() as db:
        session = get_session_from_request(db, request)
        if session is None:
            raise DomainError("SESSION_REQUIRED", "Sign in with your invitation credential.", 401)
        if request.method in {"POST", "PATCH", "DELETE"}:
            require_csrf(request, session)
        request.state.session_id = session.id
        return Principal.model_validate(db.get(User, session.user_id))


def require_organizer(request: Request) -> Principal:
    principal = get_principal(request)
    if principal.role not in {"organizer", "admin"}:
        raise DomainError("FORBIDDEN", "Organizer access required.", 403)
    return principal


def require_drop_access(principal, drop_id):
    with session_factory()() as db:
        drop = db.get(Drop, drop_id)
        if (
            principal.role not in {"organizer", "admin"}
            or drop is None
            or (principal.role != "admin" and drop.owner_id != principal.id)
        ):
            raise DomainError("NOT_FOUND", "Drop not found.", 404)

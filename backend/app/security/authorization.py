"""P2 handoff: replace these deny-by-default hooks, keeping signatures.
get_principal validates durable session/credential, and CSRF+Origin on writes.
require_organizer validates role; require_drop_access checks owner/admin using DB.
"""

from fastapi import Request

from app.core.errors import DomainError
from app.core.schemas import Principal

SECURITY_IMPLEMENTED = False


def get_principal(request: Request) -> Principal:
    raise DomainError("NOT_IMPLEMENTED", "Session authentication awaits Member 2.", 501)


def require_organizer(request: Request) -> Principal:
    principal = get_principal(request)
    if principal.role not in {"organizer", "admin"}:
        raise DomainError("FORBIDDEN", "Organizer access required.", 403)
    return principal


def require_drop_access(principal: Principal, drop_id):
    raise DomainError("NOT_IMPLEMENTED", "Drop authorization awaits Member 2.", 501)

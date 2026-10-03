from __future__ import annotations

from .errors import forbidden, not_found
from .protocols import DropAccessRepository, Principal


VALID_ROLES = {"participant", "organizer", "admin"}


def require_organizer(principal: Principal) -> Principal:
    if principal.role not in {"organizer", "admin"}:
        raise forbidden()
    return principal


def require_drop_access(
    principal: Principal,
    drop_id: str,
    repository: DropAccessRepository,
) -> Principal:
    if principal.role not in VALID_ROLES:
        raise forbidden()
    if principal.role == "admin":
        return principal
    if principal.role == "organizer" and repository.organizer_owns_drop(principal.id, drop_id):
        return principal
    if principal.role == "participant" and repository.participant_has_drop_access(principal.id, drop_id):
        return principal
    raise forbidden()


def require_owned_private_resource(principal: Principal, owner_user_id: str) -> Principal:
    if principal.role == "admin" or principal.id == owner_user_id:
        return principal
    # Hide whether another participant's receipt/reservation exists.
    raise not_found()

from fastapi import Request

from app.core.errors import DomainError
from app.core.schemas import Principal


def enforce_limit(request: Request, principal: Principal, action: str):
    raise DomainError("NOT_IMPLEMENTED", "Shared admission limits await Member 2.", 501)

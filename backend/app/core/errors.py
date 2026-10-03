"""
Shared safe error envelope — P1 area.
All members use these error codes and the standard envelope.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str
    retryable: bool = False
    fields: Optional[dict[str, list[str]]] = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


# Stable error codes per architecture.md
class ErrorCode:
    SESSION_REQUIRED = "SESSION_REQUIRED"
    FORBIDDEN = "FORBIDDEN"
    CSRF_REJECTED = "CSRF_REJECTED"
    NOT_FOUND = "NOT_FOUND"
    ENTRY_CLOSED = "ENTRY_CLOSED"
    ENTRY_NOT_OPEN = "ENTRY_NOT_OPEN"
    OFFER_EXPIRED = "OFFER_EXPIRED"
    INVALID_STATE = "INVALID_STATE"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    TEMPORARILY_UNAVAILABLE = "TEMPORARILY_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    INVITATION_REQUIRED = "INVITATION_REQUIRED"
    ORIGIN_REJECTED = "ORIGIN_REJECTED"


def make_error(
    code: str,
    message: str,
    request_id: Optional[str] = None,
    retryable: bool = False,
    fields: Optional[dict[str, list[str]]] = None,
    http_status: int = 400,
) -> JSONResponse:
    rid = request_id or str(uuid.uuid4())
    body = ErrorEnvelope(
        error=ErrorDetail(
            code=code,
            message=message,
            request_id=rid,
            retryable=retryable,
            fields=fields,
        )
    )
    return JSONResponse(
        status_code=http_status,
        content=body.model_dump(),
        headers={"X-Request-ID": rid},
    )


def get_request_id(request: Request) -> str:
    """Return existing request ID header or generate one."""
    return request.headers.get("X-Request-ID", str(uuid.uuid4()))

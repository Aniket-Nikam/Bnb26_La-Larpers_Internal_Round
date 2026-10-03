from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class SecurityError(Exception):
    code: str
    message: str
    status_code: int
    retryable: bool = False
    fields: dict[str, list[str]] | None = None
    retry_after: int | None = None

    def __str__(self) -> str:
        return self.message

    def envelope(self, request_id: str) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "request_id": request_id,
                "retryable": self.retryable,
                "fields": self.fields,
            }
        }


def session_required() -> SecurityError:
    return SecurityError("SESSION_REQUIRED", "A valid session is required.", 401)


def invalid_credentials() -> SecurityError:
    # Deliberately identical for unknown, expired, and revoked credentials.
    return SecurityError("INVALID_CREDENTIALS", "The access credential is invalid or unavailable.", 401)


def forbidden() -> SecurityError:
    return SecurityError("FORBIDDEN", "You are not authorized to perform this action.", 403)


def not_found() -> SecurityError:
    return SecurityError("NOT_FOUND", "The requested resource was not found.", 404)


def csrf_rejected() -> SecurityError:
    return SecurityError("CSRF_REJECTED", "The request could not be verified.", 403)


def validation_error(fields: dict[str, list[str]]) -> SecurityError:
    return SecurityError("VALIDATION_ERROR", "The request contains invalid fields.", 422, fields=fields)


def rate_limited(retry_after: int) -> SecurityError:
    return SecurityError(
        "RATE_LIMITED",
        "Too many requests. Retry after the indicated delay.",
        429,
        retryable=True,
        retry_after=max(1, retry_after),
    )


def temporarily_unavailable() -> SecurityError:
    return SecurityError(
        "TEMPORARILY_UNAVAILABLE",
        "This protected action is temporarily unavailable. Please retry.",
        503,
        retryable=True,
    )


def security_misconfigured() -> SecurityError:
    return SecurityError("INTERNAL_ERROR", "Security services are unavailable.", 500)

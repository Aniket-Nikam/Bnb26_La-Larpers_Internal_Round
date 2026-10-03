from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError
from starlette.exceptions import HTTPException


class DomainError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status: int = 409,
        retryable: bool = False,
        fields=None,
        headers=None,
    ):
        self.code, self.message, self.status = code, message, status
        self.retryable, self.fields, self.headers = retryable, fields, headers


def error_response(request, code, message, status, retryable=False, fields=None, headers=None):
    return JSONResponse(
        status_code=status,
        headers=headers,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request.state.request_id,
                "retryable": retryable,
                "fields": fields,
            }
        },
    )


def install_errors(app):
    @app.exception_handler(DomainError)
    async def domain(request: Request, exc: DomainError):
        return error_response(
            request, exc.code, exc.message, exc.status, exc.retryable, exc.fields, exc.headers
        )

    @app.exception_handler(RequestValidationError)
    async def validation(request: Request, exc):
        fields = {}
        for item in exc.errors():
            name = ".".join(str(p) for p in item["loc"])
            # Never echo inputs, credential values or validation exception contexts.
            fields.setdefault(name, []).append("Invalid or missing value.")
        return error_response(
            request, "VALIDATION_ERROR", "Check the supplied fields.", 422, fields=fields
        )

    @app.exception_handler(HTTPException)
    async def http(request: Request, exc):
        return error_response(
            request,
            "NOT_FOUND" if exc.status_code == 404 else "FORBIDDEN",
            "Resource not found." if exc.status_code == 404 else "Request denied.",
            exc.status_code,
        )

    @app.exception_handler(DBAPIError)
    async def database(request: Request, exc):
        code = getattr(exc.orig, "sqlstate", None)
        if (
            exc.connection_invalidated
            or code in {"55P03", "57014", "40P01", "40001"}
            or code is None
        ):
            return error_response(
                request, "TEMPORARILY_UNAVAILABLE", "Database temporarily unavailable.", 503, True
            )
        return error_response(request, "INTERNAL_ERROR", "Unexpected database error.", 500)

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc):
        return error_response(request, "INTERNAL_ERROR", "Unexpected service error.", 500)

"""
FastAPI application entrypoint — P1 area.
P2 provides: security.router, security exception handler.
"""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.core.config import get_settings
from backend.app.core.errors import ErrorCode, make_error
from backend.app.security.authorization import HTTPSecurityError
from backend.app.security.router import router as security_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    settings = get_settings()
    logger.info("FairDrop API starting. Profile=%s", settings.APP_PROFILE)
    yield
    logger.info("FairDrop API shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="FairDrop API",
        version="1.0.0",
        docs_url="/api/docs" if settings.is_demo else None,
        redoc_url="/api/redoc" if settings.is_demo else None,
        lifespan=lifespan,
    )

    # CORS — no broad credentialed wildcard; same-origin proxy in production
    # This is secondary defence; Nginx enforces same-origin in production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-ID", "Idempotency-Key"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )

    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    # Exception handler for security errors
    @app.exception_handler(HTTPSecurityError)
    async def security_error_handler(request: Request, exc: HTTPSecurityError):
        return exc.response

    # Validation error handler — 422 standard envelope
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        field_errors: dict[str, list[str]] = {}
        for err in exc.errors():
            loc = ".".join(str(x) for x in err.get("loc", []) if x not in ("body",))
            msg = err.get("msg", "Invalid value")
            field_errors.setdefault(loc or "detail", []).append(msg)
        return make_error(
            code=ErrorCode.VALIDATION_ERROR,
            message="Request validation failed.",
            request_id=request_id,
            fields=field_errors or None,
            http_status=422,
        )

    # HTTP exception handler
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        code_map = {
            401: ErrorCode.SESSION_REQUIRED,
            403: ErrorCode.FORBIDDEN,
            404: ErrorCode.NOT_FOUND,
            429: ErrorCode.RATE_LIMITED,
            503: ErrorCode.TEMPORARILY_UNAVAILABLE,
        }
        code = code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
        return make_error(
            code=code,
            message=str(exc.detail) if exc.detail else "Error",
            request_id=request_id,
            http_status=exc.status_code,
        )

    # Global exception handler — no stack traces in responses
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        logger.exception("Unhandled exception request_id=%s", request_id)
        return make_error(
            code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred.",
            request_id=request_id,
            http_status=500,
        )

    # Mount unified security router (includes /auth/* and /profile)
    app.include_router(security_router, prefix="/api/v1")

    # Health endpoints
    @app.get("/api/health/live")
    async def health_live():
        return {"status": "alive"}

    @app.get("/api/health/ready")
    async def health_ready():
        """Check PostgreSQL and Redis readiness."""
        checks = {"postgresql": "unknown", "redis": "unknown"}
        capabilities = {
            "session_auth": True,
            "rate_limiting": False,
            "lab": False,
        }
        overall = "ready"

        # Check PostgreSQL
        try:
            from backend.app.persistence.database import get_db_session
            from sqlalchemy import text
            async with get_db_session() as db:
                await db.execute(text("SELECT 1"))
            checks["postgresql"] = "healthy"
        except Exception as e:
            logger.warning("PostgreSQL health check failed: %s", e)
            checks["postgresql"] = "unavailable"
            overall = "degraded"

        # Check Redis
        try:
            from backend.app.security.limits import get_redis
            r = get_redis()
            await r.ping()
            checks["redis"] = "healthy"
            capabilities["rate_limiting"] = True
        except Exception as e:
            logger.warning("Redis health check failed: %s", e)
            checks["redis"] = "unavailable"
            # Redis down: rate limiting disabled, protected writes degraded

        return {
            "status": overall,
            "checks": checks,
            "capabilities": capabilities,
            "profile": settings.APP_PROFILE.value,
        }

    return app


app = create_app()

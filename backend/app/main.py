from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy import text

from app.audit.router import router as audit_router
from app.core import schemas as s
from app.core.config import get_settings
from app.core.errors import error_response, install_errors
from app.drops.router import router as drops_router
from app.lab import router as lab_module
from app.lab.router import router as lab_router
from app.persistence.database import get_engine
from app.security import authorization
from app.security.router import router as security_router


@asynccontextmanager
async def lifespan(app):
    get_settings()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="FairDrop",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
install_errors(app)
ERRORS = {
    code: {"model": s.ErrorResponse} for code in (401, 403, 404, 409, 422, 429, 500, 501, 503)
}
for router in (security_router, drops_router, audit_router, lab_router):
    app.include_router(router, prefix="/api/v1", responses=ERRORS)


@app.middleware("http")
async def request_context(request: Request, call_next):
    try:
        request.state.request_id = str(UUID(request.headers.get("X-Request-ID", "")))
    except ValueError:
        request.state.request_id = str(uuid4())
    if request.method in {"POST", "PATCH", "DELETE"}:
        # Enforce a real bounded read, including chunked bodies, before JSON parsing.
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 65536:
                response = error_response(
                    request, "VALIDATION_ERROR", "Request body is too large.", 413
                )
                response.headers["X-Request-ID"] = request.state.request_id
                return response
        request._body = bytes(body)
    try:
        response = await call_next(request)
    except Exception:
        response = error_response(request, "INTERNAL_ERROR", "Unexpected service error.", 500)
    response.headers["X-Request-ID"] = request.state.request_id
    # Safe default for all responses; explicit public caching can be added later.
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health/live", response_model=s.LiveHealth)
def live():
    return s.LiveHealth()


@app.get(
    "/api/health/ready", response_model=s.ReadyHealth, responses={503: {"model": s.ReadyHealth}}
)
def ready():
    cfg = get_settings()
    db_ok = redis_ok = False
    try:
        with get_engine().connect() as conn:
            version = conn.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))
            db_ok = version == "c2f4a1230001"
    except Exception:
        pass
    try:
        with Redis.from_url(cfg.redis_url, socket_timeout=1, socket_connect_timeout=1) as client:
            redis_ok = client.ping()
    except Exception:
        pass
    security_ok = authorization.SECURITY_IMPLEMENTED
    result = s.ReadyHealth(
        status="unavailable"
        if not db_ok
        else ("ready" if redis_ok and security_ok else "degraded"),
        dependencies=s.Dependencies(
            database="ready" if db_ok else "unavailable",
            redis="ready" if redis_ok else "unavailable",
            security="ready" if security_ok else "not_implemented",
        ),
        capabilities=s.Capabilities(
            safe_reads=db_ok,
            protected_writes=db_ok and redis_ok and security_ok,
            lab=cfg.app_profile == "demo" and lab_module.LAB_IMPLEMENTED and security_ok,
            fcfs_demo=cfg.app_profile == "demo" and security_ok,
        ),
    )
    # Redis degradation must not discard safe read traffic. DB failure returns 503.
    return JSONResponse(result.model_dump(mode="json"), status_code=200 if db_ok else 503)


def contract_openapi():
    schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
    schema["info"]["x-contract-version"] = "v1.0"
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            if method not in {"post", "patch", "delete"}:
                continue
            headers = []
            if path != "/api/v1/auth/session":
                headers = [
                    {
                        "name": "X-CSRF-Token",
                        "in": "header",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ]
                if path != "/api/v1/auth/session":
                    headers.append(
                        {
                            "name": "Idempotency-Key",
                            "in": "header",
                            "required": True,
                            "schema": {"type": "string", "format": "uuid"},
                        }
                    )
            elif method == "delete":
                headers = [
                    {
                        "name": "X-CSRF-Token",
                        "in": "header",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ]
            headers.append(
                {"name": "Origin", "in": "header", "required": True, "schema": {"type": "string"}}
            )
            existing = operation.setdefault("parameters", [])
            existing_names = {p.get("name") for p in existing}
            existing.extend(h for h in headers if h["name"] not in existing_names)
    return schema


app.openapi = contract_openapi

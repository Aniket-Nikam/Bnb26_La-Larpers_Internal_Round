from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

from .authorization import require_drop_access as authorize_drop
from .authorization import require_organizer as authorize_organizer
from .config import SecurityConfig
from .crypto import session_digest
from .errors import security_misconfigured
from .limits import LimitAction, LimitDecision, RateLimiter
from .protocols import DropAccessRepository, Principal
from .sessions import AuthenticatedSession, SessionService
from .source import resolve_source_address


@dataclass(frozen=True, slots=True)
class SecurityDependencies:
    sessions: SessionService
    drop_access: DropAccessRepository
    limiter: RateLimiter
    config: SecurityConfig


_runtime: SecurityDependencies | None = None
_runtime_lock = threading.Lock()


def configure_security_dependencies(dependencies: SecurityDependencies) -> None:
    """Called once by P1's application bootstrap after DB/Redis adapters exist."""
    global _runtime
    with _runtime_lock:
        if _runtime is not None and _runtime is not dependencies:
            raise RuntimeError("security dependencies are already configured")
        _runtime = dependencies


def get_principal(request: Any) -> Principal:
    authenticated = get_authenticated_session(request)
    return authenticated.principal


def get_authenticated_session(request: Any) -> AuthenticatedSession:
    runtime = _require_runtime()
    token = request.cookies.get(runtime.config.cookie_name)
    authenticated = runtime.sessions.authenticate(token)
    state = getattr(request, "state", None)
    if state is not None:
        state.authenticated_session = authenticated
    return authenticated


def require_organizer(request: Any) -> Principal:
    return authorize_organizer(get_principal(request))


def require_drop_access(principal: Principal, drop_id: str) -> Principal:
    runtime = _require_runtime()
    return authorize_drop(principal, drop_id, runtime.drop_access)


def enforce_limit(request: Any, principal: Principal, action: LimitAction | str) -> LimitDecision:
    runtime = _require_runtime()
    action = LimitAction(action)
    token = request.cookies.get(runtime.config.cookie_name) or ""
    return runtime.limiter.enforce(
        action=action,
        account_id=principal.id,
        session_digest_value=session_digest(runtime.config.session_digest_key, token),
        source_address=_request_source(request, runtime.config),
    )


def enforce_login_limit(request: Any, access_code: str) -> LimitDecision:
    runtime = _require_runtime()
    return runtime.limiter.enforce(
        action=LimitAction.LOGIN,
        account_id=None,
        session_digest_value=None,
        source_address=_request_source(request, runtime.config),
        credential_value=access_code,
    )


def _request_source(request: Any, config: SecurityConfig) -> str:
    client = getattr(request, "client", None)
    peer = getattr(client, "host", None)
    if not peer:
        raise security_misconfigured()
    return resolve_source_address(
        peer_address=peer,
        forwarded_for=request.headers.get("x-forwarded-for"),
        trusted_proxy_cidrs=config.trusted_proxy_cidrs,
    )


def _require_runtime() -> SecurityDependencies:
    if _runtime is None:
        raise security_misconfigured()
    return _runtime


def _reset_security_dependencies_for_tests() -> None:
    global _runtime
    with _runtime_lock:
        _runtime = None

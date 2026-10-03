"""
Security package exports — P2.

These are the mounted interfaces that P1 imports in main.py:
  - router: FastAPI router for auth/profile routes
  - get_principal: dependency returning AuthContext or raising 401
  - require_organizer: dependency returning AuthContext or raising 403
  - require_drop_access: async function for drop ownership check
  - enforce_limit: async function for rate limiting
"""
from backend.app.security.authorization import (
    AuthContext,
    Principal,
    check_drop_grant,
    get_optional_auth,
    get_principal,
    require_drop_access,
    require_organizer,
)
from backend.app.security.csrf import generate_csrf_token, require_csrf
from backend.app.security.limits import LimitAction, LimitResult, enforce_limit, get_trusted_ip
from backend.app.security.provisioning import (
    provision_credential,
    provision_user_with_credential,
    revoke_credential,
    verify_credential,
)
from backend.app.security.router import router
from backend.app.security.sessions import (
    clear_session_cookie,
    create_session,
    get_session_from_request,
    revoke_session,
    set_session_cookie,
)

__all__ = [
    # Router
    "router",
    # Auth dependencies
    "get_principal",
    "get_optional_auth",
    "require_organizer",
    "require_drop_access",
    "check_drop_grant",
    # Types
    "Principal",
    "AuthContext",
    # CSRF
    "generate_csrf_token",
    "require_csrf",
    # Limits
    "enforce_limit",
    "get_trusted_ip",
    "LimitAction",
    "LimitResult",
    # Sessions
    "create_session",
    "revoke_session",
    "get_session_from_request",
    "set_session_cookie",
    "clear_session_cookie",
    # Provisioning
    "verify_credential",
    "provision_credential",
    "provision_user_with_credential",
    "revoke_credential",
]

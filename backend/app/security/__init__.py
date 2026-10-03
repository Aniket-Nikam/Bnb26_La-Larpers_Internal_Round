"""FairDrop security services.

The shared FastAPI router and SQLAlchemy adapters are connected after P1's
bootstrap lands.  This package intentionally owns security policy and protocols,
not a second persistence model.
"""

from .config import SecurityConfig
from .credentials import CredentialService
from .csrf import derive_csrf_token, require_csrf, require_origin
from .dependencies import (
    configure_security_dependencies,
    enforce_limit,
    enforce_login_limit,
    get_principal,
    require_drop_access,
    require_organizer,
)
from .limits import LimitAction, RateLimiter
from .sessions import SessionService

__all__ = [
    "CredentialService",
    "LimitAction",
    "RateLimiter",
    "SecurityConfig",
    "SessionService",
    "derive_csrf_token",
    "configure_security_dependencies",
    "enforce_limit",
    "enforce_login_limit",
    "get_principal",
    "require_csrf",
    "require_drop_access",
    "require_origin",
    "require_organizer",
]

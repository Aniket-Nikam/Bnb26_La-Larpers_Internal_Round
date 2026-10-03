import hashlib
import hmac

from app.core.config import get_settings
from app.core.errors import DomainError


def generate_csrf_token(session_id, csrf_secret):
    return hmac.new(csrf_secret.encode(), str(session_id).encode(), hashlib.sha256).hexdigest()


def require_origin(request):
    if request.headers.get("Origin") != get_settings().public_origin:
        raise DomainError("CSRF_REJECTED", "A matching Origin is required.", 403)


def require_csrf(request, session):
    require_origin(request)
    supplied = request.headers.get("X-CSRF-Token", "")
    expected = generate_csrf_token(session.id, session.csrf_secret)
    if not hmac.compare_digest(supplied, expected):
        raise DomainError("CSRF_REJECTED", "Refresh the session and retry.", 403)

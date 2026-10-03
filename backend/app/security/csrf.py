import hashlib
import hmac
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.errors import DomainError


def generate_csrf_token(session_id, csrf_secret):
    return hmac.new(csrf_secret.encode(), str(session_id).encode(), hashlib.sha256).hexdigest()


def require_origin(request):
    origin = request.headers.get("Origin")
    if not origin:
        raise DomainError("CSRF_REJECTED", "A matching Origin is required.", 403)
    public_origin = get_settings().public_origin
    if origin == public_origin:
        return
    if get_settings().app_profile in {"demo", "test"}:
        origin_parsed = urlparse(origin)
        public_parsed = urlparse(public_origin)
        dev_ports = {5173, 8000, 8080, public_parsed.port}
        if (
            origin_parsed.scheme in {"http", "https"}
            and origin_parsed.port in dev_ports
            and {origin_parsed.hostname, public_parsed.hostname}.issubset({"localhost", "127.0.0.1"})
        ):
            return
    raise DomainError("CSRF_REJECTED", "A matching Origin is required.", 403)


def require_csrf(request, session):
    require_origin(request)
    supplied = request.headers.get("X-CSRF-Token", "")
    expected = generate_csrf_token(session.id, session.csrf_secret)
    if not hmac.compare_digest(supplied, expected):
        raise DomainError("CSRF_REJECTED", "Refresh the session and retry.", 403)

from __future__ import annotations

from urllib.parse import urlsplit

from .crypto import constant_time_equal, csrf_token
from .errors import csrf_rejected


def derive_csrf_token(session_digest_key: bytes, session_token: str) -> str:
    return csrf_token(session_digest_key, session_token)


def require_origin(received_origin: str | None, configured_origin: str) -> None:
    if received_origin is None:
        raise csrf_rejected()
    try:
        received = _canonical_origin(received_origin)
        configured = _canonical_origin(configured_origin)
    except ValueError as exc:
        raise csrf_rejected() from exc
    if not constant_time_equal(received, configured):
        raise csrf_rejected()


def require_csrf(session_digest_key: bytes, session_token: str, submitted_token: str | None) -> None:
    expected = derive_csrf_token(session_digest_key, session_token)
    candidate = submitted_token or ""
    if not candidate or not constant_time_equal(expected, candidate):
        raise csrf_rejected()


def _canonical_origin(value: str) -> str:
    if len(value) > 512:
        raise ValueError("origin is too long")
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("invalid origin")
    if parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("invalid origin")
    host = parsed.hostname
    if not host:
        raise ValueError("invalid origin")
    port = parsed.port
    default_port = 443 if parsed.scheme == "https" else 80
    authority = host.lower() if port in {None, default_port} else f"{host.lower()}:{port}"
    return f"{parsed.scheme.lower()}://{authority}"

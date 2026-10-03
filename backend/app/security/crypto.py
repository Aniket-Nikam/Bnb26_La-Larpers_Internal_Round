from __future__ import annotations

import base64
import hashlib
import hmac
import secrets


MAX_SECRET_INPUT_LENGTH = 512


def generate_access_code() -> str:
    return secrets.token_urlsafe(32)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def keyed_digest(key: bytes, purpose: str, value: str) -> str:
    if not value or len(value) > MAX_SECRET_INPUT_LENGTH:
        # Still perform a fixed digest before the caller returns a generic failure.
        value = "invalid-input"
    payload = purpose.encode("ascii") + b"\x00" + value.encode("utf-8", errors="replace")
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def credential_digest(key: bytes, access_code: str) -> str:
    return keyed_digest(key, "credential-v1", access_code)


def session_digest(key: bytes, token: str) -> str:
    return keyed_digest(key, "session-v1", token)


def csrf_token(key: bytes, session_token: str) -> str:
    digest = hmac.new(
        key,
        b"csrf-v1\x00" + session_token.encode("utf-8", errors="replace"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))

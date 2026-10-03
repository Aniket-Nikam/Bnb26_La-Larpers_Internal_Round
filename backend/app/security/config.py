from __future__ import annotations

import os
import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlsplit


INSECURE_MARKERS = ("change_me", "changeme", "default", "insecure", "example")


@dataclass(frozen=True, slots=True)
class SecurityConfig:
    app_profile: str
    public_origin: str
    session_digest_key: bytes
    credential_digest_key: bytes
    cookie_secure: bool
    cookie_name: str = "fairdrop_session"
    session_lifetime_seconds: int = 86_400
    trusted_proxy_cidrs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.app_profile not in {"normal", "demo", "test"}:
            raise ValueError("APP_PROFILE must be normal, demo, or test")
        origin = _validate_origin(self.public_origin)
        if origin != self.public_origin.rstrip("/"):
            raise ValueError("PUBLIC_ORIGIN must be canonical")
        _validate_secret_bytes(self.session_digest_key, "SESSION_DIGEST_KEY", self.app_profile)
        _validate_secret_bytes(
            self.credential_digest_key, "CREDENTIAL_DIGEST_KEY", self.app_profile
        )
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", self.cookie_name):
            raise ValueError("cookie_name contains unsupported characters")
        for value in self.trusted_proxy_cidrs:
            ipaddress.ip_network(value, strict=False)
        if self.app_profile == "normal":
            if not self.cookie_secure:
                raise ValueError("normal profile requires COOKIE_SECURE=true")
            if urlsplit(origin).scheme != "https":
                raise ValueError("normal profile requires an HTTPS PUBLIC_ORIGIN")

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> SecurityConfig:
        values = os.environ if env is None else env
        profile = values.get("APP_PROFILE", "").strip().lower()
        if profile not in {"normal", "demo", "test"}:
            raise ValueError("APP_PROFILE must be normal, demo, or test")
        origin = _validate_origin(values.get("PUBLIC_ORIGIN", ""))
        cookie_secure = _strict_bool(values.get("COOKIE_SECURE", ""), "COOKIE_SECURE")
        session_key = _secret(values.get("SESSION_DIGEST_KEY", ""), "SESSION_DIGEST_KEY", profile)
        credential_key = _secret(
            values.get("CREDENTIAL_DIGEST_KEY", ""), "CREDENTIAL_DIGEST_KEY", profile
        )
        proxies = tuple(
            item.strip()
            for item in values.get("TRUSTED_PROXY_CIDRS", "").split(",")
            if item.strip()
        )
        return cls(profile, origin, session_key, credential_key, cookie_secure, trusted_proxy_cidrs=proxies)


def _validate_origin(value: str) -> str:
    value = value.strip().rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("PUBLIC_ORIGIN must be an absolute HTTP(S) origin")
    if parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise ValueError("PUBLIC_ORIGIN must not contain credentials, path, query, or fragment")
    return value


def _strict_bool(value: str, name: str) -> bool:
    normalized = value.strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError(f"{name} must be true or false")
    return normalized == "true"


def _secret(value: str, name: str, profile: str) -> bytes:
    raw = value.encode("utf-8")
    _validate_secret_bytes(raw, name, profile)
    return raw


def _validate_secret_bytes(raw: bytes, name: str, profile: str) -> None:
    if len(raw) < 32:
        raise ValueError(f"{name} must contain at least 32 bytes")
    lowered = raw.decode("utf-8", errors="ignore").lower()
    if profile == "normal" and any(marker in lowered for marker in INSECURE_MARKERS):
        raise ValueError(f"{name} contains an insecure placeholder")

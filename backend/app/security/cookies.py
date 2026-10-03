from __future__ import annotations

from dataclasses import dataclass

from .config import SecurityConfig


@dataclass(frozen=True, slots=True)
class SessionCookiePolicy:
    key: str
    httponly: bool
    secure: bool
    samesite: str
    path: str
    max_age: int

    @classmethod
    def from_config(cls, config: SecurityConfig) -> SessionCookiePolicy:
        return cls(
            key=config.cookie_name,
            httponly=True,
            secure=config.cookie_secure,
            samesite="lax",
            path="/",
            max_age=config.session_lifetime_seconds,
        )

    def set_kwargs(self) -> dict[str, object]:
        return {
            "key": self.key,
            "httponly": self.httponly,
            "secure": self.secure,
            "samesite": self.samesite,
            "path": self.path,
            "max_age": self.max_age,
        }

    def delete_kwargs(self) -> dict[str, object]:
        return {"key": self.key, "path": self.path, "secure": self.secure, "samesite": self.samesite}

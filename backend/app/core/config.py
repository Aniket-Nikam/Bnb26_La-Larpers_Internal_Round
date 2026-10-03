"""
Shared application configuration — P1 area.
P2 reads SESSION_DIGEST_KEY, CREDENTIAL_DIGEST_KEY, COOKIE_SECURE, PUBLIC_ORIGIN.
"""
from __future__ import annotations

import secrets
from enum import Enum
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppProfile(str, Enum):
    normal = "normal"
    demo = "demo"
    test = "test"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_PROFILE: AppProfile = AppProfile.normal

    DATABASE_URL: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"

    # Origins that may issue browser write requests.
    # PUBLIC_ORIGIN is the canonical same-origin, e.g. https://fairdrop.example
    PUBLIC_ORIGIN: str = "http://localhost:5173"

    # 32-byte hex keys (64 hex chars) — must not be default in normal profile
    SESSION_DIGEST_KEY: str = "CHANGE_ME_SESSION_DIGEST_KEY_000000000000000000000000000000"
    CREDENTIAL_DIGEST_KEY: str = "CHANGE_ME_CREDENTIAL_DIGEST_KEY_00000000000000000000000000000"
    SEED_ENCRYPTION_KEY: str = "CHANGE_ME_SEED_ENCRYPTION_KEY_000000000000000000000000000000"

    COOKIE_SECURE: bool = True  # False only in local HTTP demo

    # Lab / demo settings (ignored in normal profile)
    LAB_TARGET_ORIGIN: str = ""
    LAB_MAX_RPS: int = 100
    LAB_MAX_IDENTITIES: int = 50_000

    # Session lifetime
    SESSION_LIFETIME_SECONDS: int = 86_400  # 24 hours

    @field_validator("APP_PROFILE", mode="before")
    @classmethod
    def _validate_profile(cls, v: str) -> str:
        v = v.lower()
        if v not in {p.value for p in AppProfile}:
            raise ValueError(f"APP_PROFILE must be one of {[p.value for p in AppProfile]}")
        return v

    @model_validator(mode="after")
    def _reject_defaults_in_normal(self) -> "Settings":
        if self.APP_PROFILE == AppProfile.normal:
            defaults = {
                "CHANGE_ME_SESSION_DIGEST_KEY_000000000000000000000000000000",
                "CHANGE_ME_CREDENTIAL_DIGEST_KEY_00000000000000000000000000000",
                "CHANGE_ME_SEED_ENCRYPTION_KEY_000000000000000000000000000000",
            }
            for key in (
                self.SESSION_DIGEST_KEY,
                self.CREDENTIAL_DIGEST_KEY,
                self.SEED_ENCRYPTION_KEY,
            ):
                if key in defaults:
                    raise ValueError(
                        "Normal profile requires non-default secret keys. "
                        "Set SESSION_DIGEST_KEY, CREDENTIAL_DIGEST_KEY, SEED_ENCRYPTION_KEY."
                    )
        return self

    @property
    def is_demo(self) -> bool:
        return self.APP_PROFILE in (AppProfile.demo, AppProfile.test)

    @property
    def is_test(self) -> bool:
        return self.APP_PROFILE == AppProfile.test

    @property
    def cookie_samesite(self) -> str:
        return "lax"  # Lax is appropriate for same-origin; Strict blocks cross-site GETs

    @property
    def allowed_origins(self) -> set[str]:
        """Exact origins allowed to issue authenticated browser writes."""
        origins = {self.PUBLIC_ORIGIN.rstrip("/")}
        if self.LAB_TARGET_ORIGIN:
            origins.add(self.LAB_TARGET_ORIGIN.rstrip("/"))
        return origins


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

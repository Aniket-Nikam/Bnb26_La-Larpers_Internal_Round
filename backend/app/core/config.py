import base64
from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")
    app_profile: Literal["normal", "demo", "test"] = "normal"
    database_url: str = "postgresql+psycopg://localhost/fairdrop"
    redis_url: str = "redis://localhost:6379/0"
    public_origin: str = "https://fairdrop.example.invalid"
    session_digest_key: SecretStr = SecretStr("")
    credential_digest_key: SecretStr = SecretStr("")
    seed_encryption_key: SecretStr = SecretStr("")
    cookie_secure: bool = True
    db_pool_size: int = 8
    db_max_overflow: int = 2
    worker_tick_seconds: float = 1
    worker_batch: int = 100

    @model_validator(mode="after")
    def validate_profile(self):
        origin = urlparse(self.public_origin)
        if (
            origin.scheme not in {"http", "https"}
            or not origin.netloc
            or origin.username
            or origin.password
            or origin.path
            or origin.query
            or origin.fragment
        ):
            raise ValueError("PUBLIC_ORIGIN must be a canonical HTTP(S) origin")
        if not 1 <= self.db_pool_size <= 100 or not 0 <= self.db_max_overflow <= 100:
            raise ValueError("Database pools must be positive and bounded")
        if not 0.1 <= self.worker_tick_seconds <= 60:
            raise ValueError("Worker tick must be 0.1..60 seconds")
        if not 1 <= self.worker_batch <= 100:
            raise ValueError("worker_batch must be 1..100")
        if self.app_profile == "normal":
            if not self.cookie_secure or urlparse(self.public_origin).scheme != "https":
                raise ValueError("normal profile requires HTTPS and Secure cookies")
            for secret in (self.session_digest_key, self.credential_digest_key):
                value = secret.get_secret_value()
                if len(value) < 32 or any(
                    marker in value.lower()
                    for marker in ("change_me", "changeme", "default", "insecure", "example")
                ):
                    raise ValueError("normal profile requires configured stable digest keys")
            self.seed_key()
        return self

    def seed_key(self) -> bytes:
        try:
            key = base64.b64decode(self.seed_encryption_key.get_secret_value(), validate=True)
        except ValueError:
            raise ValueError("SEED_ENCRYPTION_KEY must be base64 of 32 random bytes") from None
        if len(key) != 32 or (self.app_profile == "normal" and len(set(key)) == 1):
            raise ValueError("SEED_ENCRYPTION_KEY must be base64 of 32 random bytes")
        return key


@lru_cache
def get_settings() -> Settings:
    return Settings()

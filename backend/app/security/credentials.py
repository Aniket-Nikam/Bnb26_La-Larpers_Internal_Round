from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from .config import SecurityConfig
from .crypto import credential_digest, generate_access_code
from .errors import invalid_credentials
from .protocols import CredentialRecord, CredentialRepository


@dataclass(frozen=True, slots=True)
class ProvisionedCredential:
    record: CredentialRecord
    access_code: str


class CredentialService:
    def __init__(self, repository: CredentialRepository, config: SecurityConfig):
        self.repository = repository
        self.config = config

    def provision(
        self,
        *,
        user_id: str,
        expires_at: datetime | None = None,
        demo_fixture: bool = False,
        now: datetime | None = None,
    ) -> ProvisionedCredential:
        timestamp = _utc(now)
        if demo_fixture and self.config.app_profile == "normal":
            raise ValueError("demo fixture credentials are disabled in normal profile")
        if not self.repository.user_exists(user_id):
            raise ValueError("credentials can only be provisioned for an existing user")
        if expires_at is not None and _utc(expires_at) <= timestamp:
            raise ValueError("credential expiry must be in the future")
        access_code = generate_access_code()
        digest = credential_digest(self.config.credential_digest_key, access_code)
        record = self.repository.insert_credential(
            user_id=user_id,
            digest=digest,
            issued_at=timestamp,
            expires_at=_utc(expires_at) if expires_at else None,
        )
        return ProvisionedCredential(record, access_code)

    def verify(self, access_code: str, *, now: datetime | None = None) -> CredentialRecord:
        timestamp = _utc(now)
        digest = credential_digest(self.config.credential_digest_key, access_code)
        record = self.repository.get_credential_by_digest(digest)
        if (
            record is None
            or record.revoked_at is not None
            or (record.expires_at is not None and _utc(record.expires_at) <= timestamp)
        ):
            raise invalid_credentials()
        return record

    @staticmethod
    def new_record_id() -> str:
        return str(uuid.uuid4())


def _utc(value: datetime | None) -> datetime:
    value = value or datetime.now(UTC)
    if value.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC)

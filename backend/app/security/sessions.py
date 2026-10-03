from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from .config import SecurityConfig
from .credentials import CredentialService
from .crypto import csrf_token, generate_session_token, keyed_digest, session_digest
from .errors import session_required, validation_error
from .protocols import Principal, SessionRecord, SessionRepository
from .profile import validate_profile_patch


@dataclass(frozen=True, slots=True)
class IssuedSession:
    token: str
    csrf_token: str
    record: SessionRecord
    principal: Principal


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    token: str
    csrf_token: str
    record: SessionRecord
    principal: Principal


class SessionService:
    def __init__(
        self,
        repository: SessionRepository,
        credentials: CredentialService,
        config: SecurityConfig,
    ):
        self.repository = repository
        self.credentials = credentials
        self.config = config

    def create(self, access_code: str, *, now: datetime | None = None) -> IssuedSession:
        timestamp = _utc(now)
        credential = self.credentials.verify(access_code, now=timestamp)
        principal = self.repository.get_principal(credential.user_id)
        if principal is None:
            # Credential/user referential integrity should make this unreachable.
            raise session_required()
        token = generate_session_token()
        csrf = csrf_token(self.config.session_digest_key, token)
        record = self.repository.insert_session(
            user_id=principal.id,
            token_digest=session_digest(self.config.session_digest_key, token),
            csrf_digest=keyed_digest(self.config.session_digest_key, "csrf-record-v1", csrf),
            created_at=timestamp,
            expires_at=timestamp + timedelta(seconds=self.config.session_lifetime_seconds),
        )
        return IssuedSession(token, csrf, record, principal)

    def authenticate(self, token: str | None, *, now: datetime | None = None) -> AuthenticatedSession:
        timestamp = _utc(now)
        candidate = token or ""
        digest = session_digest(self.config.session_digest_key, candidate)
        record = self.repository.get_session_by_digest(digest)
        if (
            not candidate
            or record is None
            or record.revoked_at is not None
            or _utc(record.expires_at) <= timestamp
        ):
            raise session_required()
        principal = self.repository.get_principal(record.user_id)
        if principal is None:
            raise session_required()
        csrf = csrf_token(self.config.session_digest_key, candidate)
        return AuthenticatedSession(candidate, csrf, record, principal)

    def revoke(self, token: str | None, *, now: datetime | None = None) -> bool:
        candidate = token or ""
        record = self.repository.get_session_by_digest(
            session_digest(self.config.session_digest_key, candidate)
        )
        if record is None or record.revoked_at is not None:
            return False
        self.repository.revoke_session(record.id, _utc(now))
        return True

    def update_profile(
        self,
        authenticated: AuthenticatedSession,
        patch: dict[str, object],
    ) -> Principal:
        try:
            display_name, timezone = validate_profile_patch(patch)
        except ValueError as exc:
            raise validation_error({"profile": [str(exc)]}) from exc
        return self.repository.update_profile(
            authenticated.principal.id,
            display_name=display_name,
            timezone=timezone,
        )


def _utc(value: datetime | None) -> datetime:
    value = value or datetime.now(UTC)
    if value.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC)

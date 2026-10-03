from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Principal:
    id: str
    public_id: str
    role: str
    display_name: str
    timezone: str


@dataclass(frozen=True, slots=True)
class CredentialRecord:
    id: str
    user_id: str
    digest: str
    issued_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None


@dataclass(frozen=True, slots=True)
class SessionRecord:
    id: str
    user_id: str
    token_digest: str
    csrf_digest: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None


class CredentialRepository(Protocol):
    def user_exists(self, user_id: str) -> bool: ...

    def get_credential_by_digest(self, digest: str) -> CredentialRecord | None: ...

    def insert_credential(
        self,
        *,
        user_id: str,
        digest: str,
        issued_at: datetime,
        expires_at: datetime | None,
    ) -> CredentialRecord: ...


class SessionRepository(Protocol):
    def get_principal(self, user_id: str) -> Principal | None: ...

    def insert_session(
        self,
        *,
        user_id: str,
        token_digest: str,
        csrf_digest: str,
        created_at: datetime,
        expires_at: datetime,
    ) -> SessionRecord: ...

    def get_session_by_digest(self, token_digest: str) -> SessionRecord | None: ...

    def revoke_session(self, session_id: str, revoked_at: datetime) -> None: ...

    def update_profile(self, user_id: str, *, display_name: str | None, timezone: str | None) -> Principal: ...


class DropAccessRepository(Protocol):
    def organizer_owns_drop(self, user_id: str, drop_id: str) -> bool: ...

    def participant_has_drop_access(self, user_id: str, drop_id: str) -> bool: ...


class RedisScriptBackend(Protocol):
    def eval(self, script: str, numkeys: int, *keys_and_args: object) -> list[int]: ...

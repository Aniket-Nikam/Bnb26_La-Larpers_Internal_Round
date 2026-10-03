from __future__ import annotations

import threading
import uuid
from dataclasses import replace
from datetime import datetime

from backend.app.security.protocols import CredentialRecord, Principal, SessionRecord


class FakeRepository:
    def __init__(self) -> None:
        self.users: dict[str, Principal] = {}
        self.credentials: dict[str, CredentialRecord] = {}
        self.sessions: dict[str, SessionRecord] = {}
        self.owned_drops: set[tuple[str, str]] = set()
        self.participant_drops: set[tuple[str, str]] = set()

    def user_exists(self, user_id: str) -> bool:
        return user_id in self.users

    def get_credential_by_digest(self, digest: str) -> CredentialRecord | None:
        return self.credentials.get(digest)

    def insert_credential(self, *, user_id, digest, issued_at, expires_at):
        record = CredentialRecord(str(uuid.uuid4()), user_id, digest, issued_at, expires_at, None)
        self.credentials[digest] = record
        return record

    def get_principal(self, user_id: str) -> Principal | None:
        return self.users.get(user_id)

    def insert_session(self, *, user_id, token_digest, csrf_digest, created_at, expires_at):
        record = SessionRecord(
            str(uuid.uuid4()), user_id, token_digest, csrf_digest, created_at, expires_at, None
        )
        self.sessions[token_digest] = record
        return record

    def get_session_by_digest(self, token_digest: str) -> SessionRecord | None:
        return self.sessions.get(token_digest)

    def revoke_session(self, session_id: str, revoked_at: datetime) -> None:
        for digest, record in self.sessions.items():
            if record.id == session_id:
                self.sessions[digest] = replace(record, revoked_at=revoked_at)
                return
        raise KeyError(session_id)

    def update_profile(self, user_id: str, *, display_name, timezone):
        current = self.users[user_id]
        updated = replace(
            current,
            display_name=current.display_name if display_name is None else display_name,
            timezone=current.timezone if timezone is None else timezone,
        )
        self.users[user_id] = updated
        return updated

    def organizer_owns_drop(self, user_id: str, drop_id: str) -> bool:
        return (user_id, drop_id) in self.owned_drops

    def participant_has_drop_access(self, user_id: str, drop_id: str) -> bool:
        return (user_id, drop_id) in self.participant_drops


class RecordingRedis:
    def __init__(self, result=None, error: Exception | None = None):
        self.result = [1, 0] if result is None else result
        self.error = error
        self.calls: list[tuple] = []

    def eval(self, script, numkeys, *keys_and_args):
        self.calls.append((script, numkeys, keys_and_args))
        if self.error:
            raise self.error
        return self.result


class AtomicFakeRedis:
    """Thread-safe behavioral stand-in; it does not prove Redis integration."""

    def __init__(self):
        self._lock = threading.Lock()
        self.counts: dict[str, int] = {}

    def eval(self, _script, numkeys, *keys_and_args):
        keys = [str(value) for value in keys_and_args[:numkeys]]
        arguments = [int(value) for value in keys_and_args[numkeys:]]
        limits = [arguments[index * 2] for index in range(numkeys)]
        with self._lock:
            if any(self.counts.get(key, 0) >= limit for key, limit in zip(keys, limits, strict=True)):
                return [0, 10_000]
            for key in keys:
                self.counts[key] = self.counts.get(key, 0) + 1
            return [1, 0]

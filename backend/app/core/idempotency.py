"""Durable claims in the same transaction as the domain write; no secret responses."""

import hashlib
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.errors import DomainError
from app.persistence.models import IdempotencyOperation


def claim(db, user_id, method: str, path: str, key: UUID, payload: dict):
    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    # ON CONFLICT waits for concurrent uncommitted claims. Statement snapshots at
    # READ COMMITTED then see the completed operation. A rollback frees the claim.
    db.execute(
        insert(IdempotencyOperation)
        .values(
            user_id=user_id,
            method=method,
            path=path,
            key=key,
            fingerprint=fingerprint,
            status="CLAIMED",
        )
        .on_conflict_do_nothing(index_elements=["user_id", "method", "path", "key"])
    )
    op = db.scalar(
        select(IdempotencyOperation)
        .where(
            IdempotencyOperation.user_id == user_id,
            IdempotencyOperation.method == method,
            IdempotencyOperation.path == path,
            IdempotencyOperation.key == key,
        )
        .with_for_update()
    )
    if op.fingerprint != fingerprint:
        raise DomainError("IDEMPOTENCY_CONFLICT", "This key was used with a different payload.")
    return op


def complete(op, kind: str, object_id=None, data=None):
    op.status, op.result_kind, op.result_id, op.result_data = "COMPLETED", kind, object_id, data

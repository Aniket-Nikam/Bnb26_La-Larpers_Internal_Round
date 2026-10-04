"""Short durable domain transactions; callers commit BEFORE returning success."""

import secrets
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.allocation.crypto import protect_seed, seed_commitment
from app.audit.service import record
from app.core.clock import db_now
from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.schemas import DraftInput
from app.persistence import models as m


def not_found():
    raise DomainError("NOT_FOUND", "Resource not found.", 404)


def lock_drop(db, drop_id, shared=False):
    drop = db.scalar(select(m.Drop).where(m.Drop.id == drop_id).with_for_update(read=shared))
    if drop is None:
        not_found()
    ensure_mode(drop)
    return drop


def ensure_mode(drop):
    if drop.mode == "FCFS_DEMO" and get_settings().app_profile != "demo":
        raise DomainError("FORBIDDEN", "FCFS comparison requires the isolated demo profile.", 403)


def owned(drop, principal):
    if principal.role not in {"organizer", "admin"}:
        raise DomainError("FORBIDDEN", "Organizer access required.", 403)
    if principal.role != "admin" and drop.owner_id != principal.id:
        not_found()


def draft_only(drop):
    if drop.phase != "DRAFT":
        raise DomainError("INVALID_STATE", "Rule fields are locked at publication.")


def create(db, principal, payload):
    if payload.mode == "FCFS_DEMO" and get_settings().app_profile != "demo":
        raise DomainError("FORBIDDEN", "FCFS comparison requires the isolated demo profile.", 403)
    drop = m.Drop(id=uuid4(), owner_id=principal.id, **payload.model_dump())
    db.add(drop)
    db.flush()
    record(db, drop.id, "DRAFT_CREATED", "drop", drop.id, principal)
    return drop


def edit(db, drop, principal, payload):
    values = payload.model_dump(exclude_unset=True)
    if drop.phase != "DRAFT" and set(values) - {"title", "description", "location_label"}:
        raise DomainError("INVALID_STATE", "Published drops allow descriptive edits only.")
    if values.get("mode") == "FCFS_DEMO" and get_settings().app_profile != "demo":
        raise DomainError("FORBIDDEN", "FCFS comparison requires the isolated demo profile.", 403)
    proposed = {name: values.get(name, getattr(drop, name)) for name in DraftInput.model_fields}
    try:
        DraftInput.model_validate(proposed)
    except ValueError:
        raise DomainError("VALIDATION_ERROR", "Check draft deadlines and settings.", 422) from None
    for name, value in values.items():
        setattr(drop, name, value)
    record(db, drop.id, "CONTENT_UPDATED", "drop", drop.id, principal)
    return drop


def grant(db, drop, principal, payload):
    draft_only(drop)
    ids = set(payload.user_public_ids)
    users = list(db.scalars(select(m.User).where(m.User.public_id.in_(ids))))
    if len(users) != len(ids):
        raise DomainError("VALIDATION_ERROR", "All grants must name pre-existing accounts.", 422)
    existing = {
        g.user_id: g
        for g in db.scalars(select(m.EligibilityGrant).where(m.EligibilityGrant.drop_id == drop.id))
    }
    active_count = sum(g.revoked_at is None for g in existing.values())
    added = sum(u.id not in existing or existing[u.id].revoked_at is not None for u in users)
    if active_count + added > 50000:
        raise DomainError(
            "POPULATION_LIMIT", "This drop permits at most 50000 eligible identities."
        )
    for user in users:
        if user.id in existing:
            existing[user.id].revoked_at = None
        else:
            db.add(m.EligibilityGrant(drop_id=drop.id, user_id=user.id, granted_by=principal.id))
    record(db, drop.id, "ELIGIBILITY_GRANTED", "drop", drop.id, principal)
    return {"drop_id": str(drop.id), "granted_count": added, "existing_count": len(users) - added}


def revoke(db, drop, principal, user_public_id):
    draft_only(drop)
    grant = db.scalar(
        select(m.EligibilityGrant)
        .join(m.User, m.User.id == m.EligibilityGrant.user_id)
        .where(m.EligibilityGrant.drop_id == drop.id, m.User.public_id == user_public_id)
    )
    if grant and grant.revoked_at is None:
        grant.revoked_at = db_now(db)
        record(db, drop.id, "ELIGIBILITY_REMOVED", "drop", drop.id, principal)


def publish(db, drop, principal=None):
    if drop.phase != "DRAFT":
        return drop  # replay publication always resolves the original drop
    now = db_now(db)
    if drop.starts_at <= now:
        raise DomainError("INVALID_STATE", "Publication requires a future entry start.")
    active = db.scalar(
        select(func.count())
        .select_from(m.EligibilityGrant)
        .where(m.EligibilityGrant.drop_id == drop.id, m.EligibilityGrant.revoked_at.is_(None))
    )
    if active > 50000:
        raise DomainError("POPULATION_LIMIT", "This drop exceeds the supported population.")
    if drop.mode == "LOTTERY":
        seed = secrets.token_bytes(32)
        drop.encrypted_seed = protect_seed(drop.id, seed)
        drop.seed_commitment = seed_commitment(seed)
    elif get_settings().app_profile != "demo":
        raise DomainError("FORBIDDEN", "FCFS comparison requires the isolated demo profile.", 403)
    db.add_all(m.SeatSlot(drop_id=drop.id, slot_number=n) for n in range(1, drop.capacity + 1))
    drop.phase = "SCHEDULED"
    record(db, drop.id, "PUBLISHED", "drop", drop.id, principal)
    return drop


def open_drop(db, drop, principal=None):
    if drop.phase not in {"SCHEDULED", "DRAFT"}:
        return drop
    if drop.phase != "SCHEDULED" or db_now(db) < drop.starts_at:
        raise DomainError("INVALID_STATE", "Drop is not scheduled to open yet.")
    drop.phase = "OPEN"
    record(db, drop.id, "OPENED", "drop", drop.id, principal)
    return drop


def enter(db, drop_id, principal):
    # FCFS uses exclusive lock for atomic admission sequence; LOTTERY holds FOR SHARE.
    mode = db.scalar(select(m.Drop.mode).where(m.Drop.id == drop_id))
    drop = lock_drop(db, drop_id, shared=mode != "FCFS_DEMO")
    if mode != drop.mode:
        raise DomainError(
            "TEMPORARILY_UNAVAILABLE", "Drop publication changed; retry this operation.", 503, True
        )
    now = db_now(db)
    existing = db.scalar(
        select(m.Entry).where(m.Entry.drop_id == drop_id, m.Entry.user_id == principal.id)
    )
    if existing:
        return existing, False
    if (
        drop.phase in {"CLOSED", "DRAWING", "OFFERING", "COMPLETED", "CANCELLED"}
        or now >= drop.ends_at
    ):
        raise DomainError("ENTRY_CLOSED", "The entry window has closed.")
    if drop.phase != "OPEN" or now < drop.starts_at:
        raise DomainError("ENTRY_NOT_OPEN", "The entry window has not opened.")
    # Published drops are open to every authenticated participant. Keep a
    # qualifying grant as internal provenance so the existing immutable entry
    # foreign key remains valid, but create it automatically on first entry.
    grant_id = db.scalar(
        insert(m.EligibilityGrant)
        .values(drop_id=drop.id, user_id=principal.id, granted_by=drop.owner_id)
        .on_conflict_do_update(
            index_elements=["drop_id", "user_id"],
            set_={"revoked_at": None, "granted_by": drop.owner_id},
        )
        .returning(m.EligibilityGrant.id)
    )
    sequence = None
    if drop.mode == "FCFS_DEMO":
        if get_settings().app_profile != "demo":
            raise DomainError(
                "FORBIDDEN", "FCFS comparison requires the isolated demo profile.", 403
            )
        drop.admission_sequence += 1
        sequence = drop.admission_sequence
    entry_id = db.scalar(
        insert(m.Entry)
        .values(
            drop_id=drop.id,
            user_id=principal.id,
            qualifying_grant_id=grant_id,
            joined_at=now,
            admission_sequence=sequence,
        )
        .on_conflict_do_nothing(index_elements=["drop_id", "user_id"])
        .returning(m.Entry.id)
    )
    entry = db.scalar(
        select(m.Entry).where(m.Entry.drop_id == drop.id, m.Entry.user_id == principal.id)
    )
    if entry_id:
        record(db, drop.id, "ENTRY_ACCEPTED", "entry", entry.id, principal)
    if entry_id and drop.mode == "FCFS_DEMO":
        from app.allocation.fcfs import reconcile_locked

        reconcile_locked(db, drop)
    # No counter write/lock upgrade in lottery path. Grant ceiling bounds entries.
    return entry, entry_id is not None


def cancel(db, drop, principal, reason):
    if drop.phase == "CANCELLED":
        return drop
    if drop.phase not in {"DRAFT", "SCHEDULED", "OPEN"}:
        raise DomainError("INVALID_STATE", "Cancellation is allowed only before allocation starts.")
    if db.scalar(select(m.DrawRun.id).where(m.DrawRun.drop_id == drop.id)) or db.scalar(
        select(m.Reservation.id).where(m.Reservation.drop_id == drop.id).limit(1)
    ):
        raise DomainError("INVALID_STATE", "Allocation has already started.")
    drop.phase, drop.cancellation_reason = "CANCELLED", reason
    record(db, drop.id, "CANCELLED", "drop", drop.id, principal, reason)
    return drop

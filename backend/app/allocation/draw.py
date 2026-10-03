"""Freeze atomically; compute unlocked; publish the COMPLETE persisted ranking atomically."""

from uuid import uuid4

from sqlalchemy import insert, select

from app.allocation.crypto import (
    ALGORITHM,
    manifest_commitment,
    reveal_seed,
    score,
    seed_commitment,
)
from app.audit.service import record
from app.core.clock import db_now
from app.core.errors import DomainError
from app.drops.service import lock_drop, open_drop
from app.persistence import models as m


def close_drop(db, drop, principal=None):
    existing = db.scalar(select(m.DrawRun).where(m.DrawRun.drop_id == drop.id))
    if existing:
        return drop
    if drop.phase == "SCHEDULED" and db_now(db) >= drop.ends_at:
        open_drop(db, drop, principal)
    if drop.phase != "OPEN" or db_now(db) < drop.ends_at:
        raise DomainError("INVALID_STATE", "Drop cannot close before its deadline.")
    # Caller already holds the exclusive Drop lock, conflicting with admissions.
    # This NEW statement snapshot includes every admission committed while waiting.
    entries = list(
        db.execute(select(m.Entry.id, m.Entry.public_entry_id).where(m.Entry.drop_id == drop.id))
    )
    run = m.DrawRun(
        id=uuid4(),
        drop_id=drop.id,
        status="FROZEN",
        snapshot_sealed=False,
        algorithm_version=ALGORITHM if drop.mode == "LOTTERY" else "fcfs-admission-v1",
        manifest_commitment=manifest_commitment([e.public_entry_id for e in entries]),
        total_entries=len(entries),
        processed_entries=0,
        next_rank=1,
    )
    drop.phase = "CLOSED"
    db.add(run)
    db.flush()
    if entries:
        db.execute(
            insert(m.FrozenEntry),
            [
                {"draw_id": run.id, "entry_id": e.id, "public_entry_id": e.public_entry_id}
                for e in entries
            ],
        )
    run.snapshot_sealed = True
    record(db, drop.id, "MANIFEST_FROZEN", "draw", run.id, principal)
    return drop


def trigger_draw(db, drop, principal=None):
    run = db.scalar(select(m.DrawRun).where(m.DrawRun.drop_id == drop.id).with_for_update())
    if run is None or drop.phase not in {"CLOSED", "DRAWING", "OFFERING", "COMPLETED"}:
        raise DomainError("INVALID_STATE", "Close and freeze this drop before drawing.")
    if run.status == "FROZEN":
        run.status, drop.phase = "COMPUTING", "DRAWING"
        record(db, drop.id, "DRAW_STARTED", "draw", run.id, principal)
    return run


def calculate_ranking(mode, seed, drop_id, entries):
    if mode != "LOTTERY":
        raise DomainError("NOT_IMPLEMENTED", "FCFS ranking is not yet implemented.", 501)
    return sorted(
        [(e.entry_id, e.public_entry_id, score(seed, drop_id, e.public_entry_id)) for e in entries],
        key=lambda row: (row[2], row[1]),
    )


def publish_ranking(db, drop, run, ranking):
    if len(ranking) != run.total_entries or len({r[0] for r in ranking}) != run.total_entries:
        raise DomainError("INTERNAL_ERROR", "Incomplete ranking cannot be published.", 500)
    if ranking:
        db.execute(
            insert(m.DrawRank),
            [
                {"draw_id": run.id, "entry_id": row[0], "rank": n, "score_bytes": row[2]}
                for n, row in enumerate(ranking, 1)
            ],
        )
    # DB constraints validate membership, unique entries and rank positions.
    run.processed_entries = run.total_entries
    run.status, run.recoverable_error, drop.phase = "PUBLISHED", None, "OFFERING"
    record(db, drop.id, "RANKING_PUBLISHED", "draw", run.id)


def compute_draw(drop_id, factory):
    with factory.begin() as db:
        drop = lock_drop(db, drop_id)
        run = trigger_draw(db, drop)
        if run.status == "PUBLISHED":
            return run.id
        draw_id = run.id
    # No row locks or ownership transaction while calculating HMAC/sorting.
    with factory() as db:
        drop = db.get(m.Drop, drop_id)
        run = db.get(m.DrawRun, draw_id)
        entries = list(db.scalars(select(m.FrozenEntry).where(m.FrozenEntry.draw_id == draw_id)))
        if (
            not run.snapshot_sealed
            or manifest_commitment([e.public_entry_id for e in entries]) != run.manifest_commitment
        ):
            raise DomainError("INTERNAL_ERROR", "Frozen manifest validation failed.", 500)
        seed = reveal_seed(drop.id, drop.encrypted_seed) if drop.mode == "LOTTERY" else None
        if seed is not None and seed_commitment(seed) != drop.seed_commitment:
            raise DomainError("INTERNAL_ERROR", "Seed commitment validation failed.", 500)
        mode = drop.mode
    ranking = calculate_ranking(mode, seed, drop_id, entries)
    with factory.begin() as db:
        drop = lock_drop(db, drop_id)
        run = db.scalar(select(m.DrawRun).where(m.DrawRun.id == draw_id).with_for_update())
        if run.status == "PUBLISHED":
            return run.id
        if run.total_entries != len(entries) or not run.snapshot_sealed:
            raise DomainError("INTERNAL_ERROR", "Snapshot changed during computation.", 500)
        publish_ranking(db, drop, run, ranking)
    return draw_id


def record_recoverable_error(drop_id, factory):
    """Safe checkpoint only; no raw exceptions/SQL/seed in recoverable error fields."""
    with factory.begin() as db:
        lock_drop(db, drop_id)
        run = db.scalar(select(m.DrawRun).where(m.DrawRun.drop_id == drop_id).with_for_update())
        if run and run.status != "PUBLISHED":
            run.recoverable_error = "Draw interrupted; retrying the original frozen snapshot."

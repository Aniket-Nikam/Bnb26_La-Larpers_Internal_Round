from sqlalchemy import select

from app.core import schemas as s
from app.core.clock import db_now
from app.persistence import models as m


def summary(db, drop):
    owner = db.get(m.User, drop.owner_id)
    return s.DropSummary(
        id=drop.id,
        title=drop.title,
        category=drop.category,
        organizer=s.PublicOrganizer(public_id=owner.public_id, display_name=owner.display_name),
        location_type=drop.location_type,
        location_label=drop.location_label,
        starts_at=drop.starts_at,
        ends_at=drop.ends_at,
        capacity=drop.capacity,
        phase=drop.phase,
        mode=drop.mode,
    )


def detail(db, drop):
    return s.DropDetail(
        **summary(db, drop).model_dump(),
        description=drop.description,
        confirmation_seconds=drop.confirmation_seconds,
        rules_version=drop.rules_version,
        seed_commitment=drop.seed_commitment,
        server_time=db_now(db),
        cancellation_reason=drop.cancellation_reason,
    )


def entry_state(db, entry):
    drop = db.get(m.Drop, entry.drop_id)
    run = db.scalar(select(m.DrawRun).where(m.DrawRun.drop_id == drop.id))
    rank = None
    if run and run.status == "PUBLISHED":
        rank = db.get(m.DrawRank, (run.id, entry.id))
    reservation = db.scalar(select(m.Reservation).where(m.Reservation.entry_id == entry.id))
    status = "ENTERED"
    if drop.phase == "CANCELLED":
        status = "CANCELLED"
    elif reservation:
        status = reservation.status
    elif rank or (drop.mode == "FCFS_DEMO" and drop.phase == "OPEN"):
        status = "WAITLISTED"
    return s.EntryState(
        entry_id=entry.id,
        public_entry_id=entry.public_entry_id,
        drop_id=entry.drop_id,
        status=status,
        joined_at=entry.joined_at,
        receipt_id=entry.receipt_id,
        draw_id=run.id if run else None,
        rank=rank.rank if rank else None,
        reservation=s.Reservation.model_validate(reservation) if reservation else None,
        server_time=db_now(db),
    )


def receipt(db, entry):
    drop = db.get(m.Drop, entry.drop_id)
    return s.Receipt(
        entry=entry_state(db, entry),
        drop=summary(db, drop),
        rules_version=drop.rules_version,
        proof_url=f"/api/v1/drops/{drop.id}/proof",
    )


def draw_status(db, run):
    return s.DrawStatus(
        draw_id=run.id,
        drop_id=run.drop_id,
        status=run.status,
        processed_entries=run.processed_entries,
        total_entries=run.total_entries,
        recoverable_error=run.recoverable_error,
        server_time=db_now(db),
    )

"""Reservation is the only seat owner. Every mutation locks Drop -> Slot -> Reservation."""

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import func, select

from app.audit.service import record
from app.core.clock import db_now
from app.core.config import get_settings
from app.core.errors import DomainError
from app.drops.service import lock_drop, not_found
from app.persistence import models as m

ACTIVE = ("OFFERED", "CONFIRMED")


def confirm(db, reservation_id, principal):
    # Resolve immutable lock identities without taking conflicting locks.
    reference = db.execute(
        select(m.Reservation.drop_id, m.Reservation.seat_slot_id, m.Reservation.user_id).where(
            m.Reservation.id == reservation_id
        )
    ).first()
    if reference is None or reference.user_id != principal.id:
        not_found()
    lock_drop(db, reference.drop_id)
    db.scalar(select(m.SeatSlot).where(m.SeatSlot.id == reference.seat_slot_id).with_for_update())
    reservation = db.scalar(
        select(m.Reservation)
        .where(m.Reservation.id == reservation_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    now = db_now(db)
    if reservation.user_id != principal.id:
        not_found()
    if reservation.status == "CONFIRMED":
        return db.get(m.Entry, reservation.entry_id)
    if reservation.status == "EXPIRED" or now >= reservation.expires_at:
        raise DomainError("OFFER_EXPIRED", "This offer's confirmation window has ended.")
    if reservation.status != "OFFERED":
        raise DomainError("INVALID_STATE", "This reservation cannot be confirmed.")
    reservation.status, reservation.confirmed_at = "CONFIRMED", now
    record(
        db, reservation.drop_id, "RESERVATION_CONFIRMED", "reservation", reservation.id, principal
    )
    return db.get(m.Entry, reservation.entry_id)


def offer(db, drop, slot, entry):
    now = db_now(db)
    reservation = m.Reservation(
        id=uuid4(),
        drop_id=drop.id,
        user_id=entry.user_id,
        entry_id=entry.id,
        seat_slot_id=slot.id,
        status="OFFERED",
        offered_at=now,
        expires_at=now + timedelta(seconds=drop.confirmation_seconds),
    )
    db.add(reservation)
    db.flush()
    record(db, drop.id, "RESERVATION_OFFERED", "reservation", reservation.id)
    return reservation


def reconcile_offers(drop_id, factory, batch=None):
    budget = min(batch or get_settings().worker_batch, 100)
    with factory.begin() as db:
        drop = lock_drop(db, drop_id)
        if drop.phase != "OFFERING":
            return 0
        slots = list(
            db.scalars(
                select(m.SeatSlot)
                .where(m.SeatSlot.drop_id == drop_id)
                .order_by(m.SeatSlot.slot_number)
                .with_for_update()
            )
        )
        reservations = list(
            db.scalars(
                select(m.Reservation)
                .where(m.Reservation.drop_id == drop_id, m.Reservation.status.in_(ACTIVE))
                .order_by(m.Reservation.id)
                .with_for_update()
            )
        )
        now = db_now(db)
        changes = 0
        for reservation in reservations:
            if changes >= budget:
                break
            if reservation.status == "OFFERED" and now >= reservation.expires_at:
                reservation.status, reservation.expired_at = "EXPIRED", now
                record(db, drop_id, "RESERVATION_EXPIRED", "reservation", reservation.id)
                changes += 1
        # Release partial-index ownership BEFORE inserting replacement offers.
        db.flush()
        run = db.scalar(select(m.DrawRun).where(m.DrawRun.drop_id == drop_id).with_for_update())
        if run is None or run.status != "PUBLISHED":
            raise DomainError("INVALID_STATE", "Complete ranking required before lottery offers.")
        occupied = {r.seat_slot_id for r in reservations if r.status in ACTIVE}
        for slot in slots:
            if slot.id in occupied or changes >= budget or run.next_rank > run.total_entries:
                continue
            rank = db.scalar(
                select(m.DrawRank).where(
                    m.DrawRank.draw_id == run.id, m.DrawRank.rank == run.next_rank
                )
            )
            if rank is None:
                raise DomainError("INTERNAL_ERROR", "Published ranking is incomplete.", 500)
            entry = db.get(m.Entry, rank.entry_id)
            if db.scalar(select(m.Reservation.id).where(m.Reservation.entry_id == entry.id)):
                raise DomainError(
                    "INTERNAL_ERROR", "Promotion cursor points to an already offered entry.", 500
                )
            offer(db, drop, slot, entry)
            run.next_rank += 1
            changes += 1
        db.flush()
        if changes < budget:
            confirmed = db.scalar(
                select(func.count())
                .select_from(m.Reservation)
                .where(m.Reservation.drop_id == drop_id, m.Reservation.status == "CONFIRMED")
            )
            offered = db.scalar(
                select(func.count())
                .select_from(m.Reservation)
                .where(m.Reservation.drop_id == drop_id, m.Reservation.status == "OFFERED")
            )
            if confirmed == drop.capacity or (run.next_rank > run.total_entries and offered == 0):
                drop.phase = "COMPLETED"
                record(db, drop_id, "COMPLETED", "drop", drop_id)
                changes += 1
        return changes

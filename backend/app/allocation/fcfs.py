"""Isolated comparator: admission order, same inventory/identity/deadline defenses."""

from sqlalchemy import select

from app.allocation.reservations import ACTIVE, offer
from app.audit.service import record
from app.core.clock import db_now
from app.core.config import get_settings
from app.core.errors import DomainError
from app.drops.service import lock_drop
from app.persistence import models as m


def reconcile_locked(db, drop, batch=None):
    if get_settings().app_profile != "demo":
        raise DomainError("FORBIDDEN", "FCFS comparison requires the isolated demo profile.", 403)
    if drop.phase != "OPEN" or drop.mode != "FCFS_DEMO":
        return 0
    budget = min(batch or get_settings().worker_batch, 100)
    slots = list(
        db.scalars(
            select(m.SeatSlot)
            .where(m.SeatSlot.drop_id == drop.id)
            .order_by(m.SeatSlot.slot_number)
            .with_for_update()
        )
    )
    active = list(
        db.scalars(
            select(m.Reservation)
            .where(m.Reservation.drop_id == drop.id, m.Reservation.status.in_(ACTIVE))
            .order_by(m.Reservation.id)
            .with_for_update()
        )
    )
    now = db_now(db)
    changes = 0
    for reservation in active:
        if changes >= budget:
            break
        if reservation.status == "OFFERED" and now >= reservation.expires_at:
            reservation.status, reservation.expired_at = "EXPIRED", now
            record(db, drop.id, "RESERVATION_EXPIRED", "reservation", reservation.id)
            changes += 1
    db.flush()
    occupied = {r.seat_slot_id for r in active if r.status in ACTIVE}
    for slot in slots:
        if (
            slot.id in occupied
            or changes >= budget
            or drop.admission_cursor > drop.admission_sequence
        ):
            continue
        entry = db.scalar(
            select(m.Entry).where(
                m.Entry.drop_id == drop.id, m.Entry.admission_sequence == drop.admission_cursor
            )
        )
        if entry is None or db.scalar(
            select(m.Reservation.id).where(m.Reservation.entry_id == entry.id)
        ):
            raise DomainError("INTERNAL_ERROR", "Invalid durable admission cursor.", 500)
        offer(db, drop, slot, entry)
        drop.admission_cursor += 1
        changes += 1
    return changes


def reconcile(drop_id, factory):
    with factory.begin() as db:
        drop = lock_drop(db, drop_id)
        return reconcile_locked(db, drop)

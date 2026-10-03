from sqlalchemy import select

from app.allocation.draw import close_drop, compute_draw, record_recoverable_error
from app.allocation.reservations import reconcile_offers
from app.core.clock import db_now
from app.drops.service import lock_drop, open_drop
from app.persistence import models as m


def advance_lifecycle(drop_id, factory):
    with factory.begin() as db:
        drop = lock_drop(db, drop_id)
        now = db_now(db)
        if drop.phase == "SCHEDULED" and now >= drop.starts_at:
            open_drop(db, drop)
        if drop.phase == "OPEN" and now >= drop.ends_at:
            close_drop(db, drop)
        return drop.phase


def tick(factory):
    """All work is discoverable from durable PostgreSQL facts, never Redis timers."""
    with factory() as db:
        now = db_now(db)
        candidates = list(
            db.scalars(
                select(m.Drop.id)
                .where(
                    ((m.Drop.phase == "SCHEDULED") & (m.Drop.starts_at <= now))
                    | ((m.Drop.phase == "OPEN") & (m.Drop.ends_at <= now))
                    | m.Drop.phase.in_(["CLOSED", "DRAWING", "OFFERING"])
                )
                .order_by(m.Drop.id)
            )
        )
    failures = []
    for drop_id in candidates:
        try:
            phase = advance_lifecycle(drop_id, factory)
            if phase in {"CLOSED", "DRAWING"}:
                compute_draw(drop_id, factory)
            reconcile_offers(drop_id, factory)
        except Exception:
            failures.append(drop_id)
            try:
                record_recoverable_error(drop_id, factory)
            except Exception:
                pass  # DB may be unavailable; next tick discovers the same durable work.
    return failures

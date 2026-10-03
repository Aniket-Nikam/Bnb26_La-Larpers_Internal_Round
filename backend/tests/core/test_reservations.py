import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from conftest import headers, prepare_open
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from test_draw import close_due

from app.allocation import lifecycle, reservations
from app.core.clock import db_now
from app.drops import service
from app.persistence import models as m


def allocate(api, actors, payload, factory, count=2):
    drop_id = prepare_open(api, actors, payload, factory)
    entries = []
    for actor in actors[1 : 1 + count]:
        result = api.post(f"/api/v1/drops/{drop_id}/entries", json={}, headers=headers(actor))
        assert result.status_code == 201, result.text
        entries.append(result.json())
    close_due(api, actors, factory, drop_id)
    assert lifecycle.tick(factory) == []
    return drop_id, entries


def offered(factory):
    with factory() as db:
        return db.scalar(select(m.Reservation).where(m.Reservation.status == "OFFERED"))


def actor_for(actors, user_id):
    return next(a for a in actors if a.id == user_id)


def test_offer_confirm_refresh_idempotency_and_constraints(api, actors, draft_payload, factory):
    drop_id, entries = allocate(api, actors, draft_payload, factory)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(lambda _: reservations.reconcile_offers(UUID(drop_id), factory), range(8))
        )
    assert sum(results) == 0  # Initial offers were already reconciled once.
    with factory() as db:
        active = list(db.scalars(select(m.Reservation)))
        assert len(active) == draft_payload["capacity"]
        assert len({r.seat_slot_id for r in active}) == len({r.user_id for r in active}) == 2
    for reservation in active:
        actor = actor_for(actors, reservation.user_id)
        path = f"/api/v1/reservations/{reservation.id}/confirm"
        key = uuid4()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(
                pool.map(
                    lambda k: api.post(path, json={}, headers=headers(actor, k)),
                    [key] * 4 + [uuid4() for _ in range(4)],
                )
            )
        assert all(r.status_code == 200 and r.json()["status"] == "CONFIRMED" for r in results)
        other = actor_for(actors, next(a.id for a in actors[1:3] if a.id != actor.id))
        assert api.post(path, json={}, headers=headers(other)).status_code == 404
        refreshed = api.get(
            f"/api/v1/entries/{reservation.entry_id}", headers=headers(actor)
        ).json()
        assert refreshed["entry"]["status"] == "CONFIRMED"
    assert lifecycle.tick(factory) == []
    with factory() as db:
        assert db.get(m.Drop, UUID(drop_id)).phase == "COMPLETED"
        assert (
            db.scalar(
                select(func.count())
                .select_from(m.AuditEvent)
                .where(m.AuditEvent.event_type == "RESERVATION_CONFIRMED")
            )
            == 2
        )
    metrics = api.get(f"/api/v1/admin/drops/{drop_id}/metrics", headers=headers(actors[0])).json()
    assert (
        metrics["integrity_ok"] and metrics["confirmed_seats"] == 2 and metrics["free_seats"] == 0
    )
    # Attempt cross-drop and wrong-user ownership, independently of application guards.
    second_drop = prepare_open(api, actors, draft_payload, factory)
    with factory() as db:
        foreign_slot = db.scalar(
            select(m.SeatSlot.id).where(m.SeatSlot.drop_id == UUID(second_drop))
        )
        source = active[0]
    with pytest.raises(IntegrityError):
        with factory.begin() as db:
            db.add(
                m.Reservation(
                    drop_id=source.drop_id,
                    user_id=actors[3].id,
                    entry_id=source.entry_id,
                    seat_slot_id=foreign_slot,
                    status="OFFERED",
                    offered_at=db_now(db),
                    expires_at=db_now(db) + timedelta(minutes=1),
                )
            )
            db.flush()


def test_expiry_promotes_exact_next_rank_and_never_reoffers(api, actors, draft_payload, factory):
    payload = {**draft_payload, "capacity": 1}
    drop_id, _ = allocate(api, actors, payload, factory)
    first = offered(factory)
    with factory.begin() as db:
        rank2 = db.scalar(select(m.DrawRank).where(m.DrawRank.rank == 2))
        db.get(m.Reservation, first.id).expires_at = db_now(db)
    assert lifecycle.tick(factory) == []
    second = offered(factory)
    assert second.entry_id == rank2.entry_id and second.seat_slot_id == first.seat_slot_id
    actor = actor_for(actors, first.user_id)
    late = api.post(f"/api/v1/reservations/{first.id}/confirm", json={}, headers=headers(actor))
    assert late.status_code == 409 and late.json()["error"]["code"] == "OFFER_EXPIRED"
    with factory.begin() as db:
        db.get(m.Reservation, second.id).expires_at = db_now(db)
    assert lifecycle.tick(factory) == []
    assert lifecycle.tick(factory) == []
    with factory() as db:
        assert db.get(m.Drop, UUID(drop_id)).phase == "COMPLETED"
        assert db.scalar(select(func.count()).select_from(m.Reservation)) == 2
        assert (
            db.scalar(
                select(func.count())
                .select_from(m.Reservation)
                .where(m.Reservation.status == "OFFERED")
            )
            == 0
        )
        run = db.scalar(select(m.DrawRun))
        assert run.next_rank == 3
    metrics = api.get(f"/api/v1/admin/drops/{drop_id}/metrics", headers=headers(actors[0])).json()
    assert (
        metrics["free_seats"] == 1
        and metrics["expired_reservations"] == 2
        and metrics["integrity_ok"]
    )


def test_confirm_waiting_past_deadline_loses_to_expiry(api, actors, draft_payload, factory):
    drop_id, _ = allocate(api, actors, {**draft_payload, "capacity": 1}, factory)
    first = offered(factory)
    with factory.begin() as db:
        db.get(m.Reservation, first.id).expires_at = db_now(db) + timedelta(milliseconds=200)
    blocker = factory()
    service.lock_drop(blocker, UUID(drop_id))
    actor = actor_for(actors, first.user_id)
    with ThreadPoolExecutor(max_workers=2) as pool:
        confirm = pool.submit(
            lambda: api.post(
                f"/api/v1/reservations/{first.id}/confirm", json={}, headers=headers(actor)
            )
        )
        expire = pool.submit(reservations.reconcile_offers, UUID(drop_id), factory)
        with factory() as db:
            deadline = db.get(m.Reservation, first.id).expires_at
            while db_now(db) < deadline:
                time.sleep(0.01)
        blocker.commit()
        response = confirm.result(timeout=5)
        expire.result(timeout=5)
    blocker.close()
    assert response.status_code == 409, response.text
    with factory() as db:
        assert db.get(m.Reservation, first.id).status == "EXPIRED"
        assert (
            db.scalar(
                select(func.count())
                .select_from(m.Reservation)
                .where(m.Reservation.status.in_(reservations.ACTIVE))
            )
            == 1
        )


def test_timely_confirmation_survives_worker_wait_past_expiry(api, actors, draft_payload, factory):
    drop_id, _ = allocate(api, actors, {**draft_payload, "capacity": 1}, factory)
    first = offered(factory)
    with factory.begin() as db:
        db.get(m.Reservation, first.id).expires_at = db_now(db) + timedelta(milliseconds=200)
    confirming = factory()
    reservations.confirm(confirming, first.id, actor_for(actors, first.user_id))
    with ThreadPoolExecutor(max_workers=1) as pool:
        expire = pool.submit(reservations.reconcile_offers, UUID(drop_id), factory)
        with factory() as db:
            deadline = db.get(m.Reservation, first.id).expires_at
            while db_now(db) < deadline:
                time.sleep(0.01)
        confirming.commit()
        expire.result(timeout=5)
    confirming.close()
    with factory() as db:
        assert db.get(m.Reservation, first.id).status == "CONFIRMED"
        assert db.get(m.Drop, UUID(drop_id)).phase == "COMPLETED"
        assert db.scalar(select(func.count()).select_from(m.Reservation)) == 1


def test_empty_undersubscribed_and_bounded_offer_recovery(api, actors, draft_payload, factory):
    drop_id = prepare_open(api, actors, draft_payload, factory)
    close_due(api, actors, factory, drop_id)
    assert lifecycle.tick(factory) == []
    with factory() as db:
        assert db.get(m.Drop, UUID(drop_id)).phase == "COMPLETED"
    under, _ = allocate(api, actors, {**draft_payload, "capacity": 5}, factory, count=1)
    reservation = offered(factory)
    actor = actor_for(actors, reservation.user_id)
    api.post(f"/api/v1/reservations/{reservation.id}/confirm", json={}, headers=headers(actor))
    lifecycle.tick(factory)
    with factory() as db:
        assert db.get(m.Drop, UUID(under)).phase == "COMPLETED"
        assert (
            db.scalar(
                select(func.count())
                .select_from(m.Reservation)
                .where(m.Reservation.drop_id == UUID(under))
            )
            == 1
        )
    metrics = api.get(f"/api/v1/admin/drops/{under}/metrics", headers=headers(actors[0])).json()
    assert metrics["confirmed_seats"] == 1 and metrics["free_seats"] == 4


def kill_during_event(module, event, operation):
    code = f"""import os, signal
from app.allocation import {module} as target
from app.persistence.database import session_factory
from uuid import UUID
original = target.record
def crash(*args, **kwargs):
    if args[2] == {event!r}: os.kill(os.getpid(), signal.SIGKILL)
    return original(*args, **kwargs)
target.record = crash
{operation}
"""
    result = subprocess.run([".venv/bin/python", "-c", code], env=os.environ.copy(), timeout=10)
    assert result.returncode == -9


def test_real_process_crashes_during_draw_offer_and_promotion(api, actors, draft_payload, factory):
    drop_id = prepare_open(api, actors, {**draft_payload, "capacity": 1}, factory)
    for actor in actors[1:3]:
        api.post(f"/api/v1/drops/{drop_id}/entries", json={}, headers=headers(actor))
    close_due(api, actors, factory, drop_id)
    with factory() as db:
        original_run = db.scalar(select(m.DrawRun.id))
        original_seed = db.get(m.Drop, UUID(drop_id)).encrypted_seed
    kill_during_event(
        "draw", "RANKING_PUBLISHED", f"target.compute_draw(UUID({drop_id!r}), session_factory())"
    )
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(m.DrawRank)) == 0
        assert db.get(m.DrawRun, original_run).status == "COMPUTING"
    from app.allocation.draw import compute_draw

    compute_draw(UUID(drop_id), factory)
    kill_during_event(
        "reservations",
        "RESERVATION_OFFERED",
        f"target.reconcile_offers(UUID({drop_id!r}), session_factory())",
    )
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(m.Reservation)) == 0
        assert db.get(m.DrawRun, original_run).next_rank == 1
    assert lifecycle.tick(factory) == []
    first = offered(factory)
    with factory.begin() as db:
        db.get(m.Reservation, first.id).expires_at = db_now(db)
    kill_during_event(
        "reservations",
        "RESERVATION_OFFERED",
        f"target.reconcile_offers(UUID({drop_id!r}), session_factory())",
    )
    with factory() as db:
        assert db.get(m.Reservation, first.id).status == "OFFERED"
        assert db.get(m.DrawRun, original_run).next_rank == 2
    # Actual worker entrypoint resumes the same ranking, slot and cursor after SIGKILL.
    result = subprocess.run(
        [".venv/bin/python", "-m", "app.allocation.worker", "--once"],
        env=os.environ.copy(),
        timeout=10,
    )
    assert result.returncode == 0
    with factory() as db:
        assert db.get(m.Reservation, first.id).status == "EXPIRED"
        assert db.get(m.DrawRun, original_run).next_rank == 3
        assert db.get(m.Drop, UUID(drop_id)).encrypted_seed == original_seed
        assert db.scalar(select(func.count()).select_from(m.Reservation)) == 2
        assert (
            db.scalar(
                select(func.count())
                .select_from(m.Reservation)
                .where(m.Reservation.status == "OFFERED")
            )
            == 1
        )


def test_missing_offers_resume_in_bounded_transactions(api, actors, draft_payload, factory):
    from app.allocation.draw import compute_draw

    drop_id = prepare_open(api, actors, draft_payload, factory)
    for actor in actors[1:3]:
        api.post(f"/api/v1/drops/{drop_id}/entries", json={}, headers=headers(actor))
    close_due(api, actors, factory, drop_id)
    compute_draw(UUID(drop_id), factory)
    assert reservations.reconcile_offers(UUID(drop_id), factory, batch=1) == 1
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(m.Reservation)) == 1
        assert db.scalar(select(m.DrawRun.next_rank)) == 2
    assert reservations.reconcile_offers(UUID(drop_id), factory, batch=1) == 1
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(m.Reservation)) == 2
        assert db.scalar(select(m.DrawRun.next_rank)) == 3
    assert reservations.reconcile_offers(UUID(drop_id), factory, batch=1) == 0

from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from conftest import headers, prepare_open
from sqlalchemy import func, select
from test_draw import close_due
from test_reservations import actor_for, offered

from app.allocation import lifecycle
from app.audit.verifier import verify
from app.core.clock import db_now
from app.core.config import Settings, get_settings
from app.persistence import models as m


def test_fcfs_rejected_outside_demo_and_normal_config_validation(
    api, actors, draft_payload, monkeypatch
):
    response = api.post(
        "/api/v1/admin/drops",
        json={**draft_payload, "mode": "FCFS_DEMO"},
        headers=headers(actors[0]),
    )
    assert response.status_code == 403
    monkeypatch.setattr(get_settings(), "app_profile", "normal")
    monkeypatch.setenv("FCFS_DEMO_ENABLED", "true")
    response = api.post(
        "/api/v1/admin/drops",
        json={**draft_payload, "mode": "FCFS_DEMO"},
        headers=headers(actors[0]),
    )
    assert response.status_code == 403
    import pytest

    with pytest.raises(ValueError):
        Settings(app_profile="normal", cookie_secure=False)
    with pytest.raises(ValueError):
        Settings(app_profile="unknown")


def test_demo_fcfs_immediate_order_expiry_and_nonlottery_proof(
    api, actors, draft_payload, factory, monkeypatch
):
    monkeypatch.setattr(get_settings(), "app_profile", "demo")
    drop_id = prepare_open(
        api, actors, {**draft_payload, "capacity": 1, "mode": "FCFS_DEMO"}, factory
    )
    path = f"/api/v1/drops/{drop_id}/entries"
    first = api.post(path, json={}, headers=headers(actors[2]))
    second = api.post(path, json={}, headers=headers(actors[1]))
    assert first.status_code == second.status_code == 201
    assert first.json()["status"] == "OFFERED" and first.json()["rank"] is None
    assert second.json()["status"] == "WAITLISTED" and second.json()["rank"] is None
    exported = api.get(f"/api/v1/admin/drops/{drop_id}/entries/export", headers=headers(actors[0]))
    assert f"{second.json()['public_entry_id']},WAITLISTED," in exported.text
    with ThreadPoolExecutor(max_workers=4) as pool:
        repeats = list(
            pool.map(lambda _: api.post(path, json={}, headers=headers(actors[2])), range(8))
        )
    assert all(
        r.status_code == 200 and r.json()["entry_id"] == first.json()["entry_id"] for r in repeats
    )
    with factory() as db:
        drop = db.get(m.Drop, UUID(drop_id))
        assert drop.admission_sequence == 2 and drop.admission_cursor == 2
        assert drop.encrypted_seed is None and drop.seed_commitment is None
    cancelled = api.post(
        f"/api/v1/admin/drops/{drop_id}/cancel",
        json={"reason": "Too late"},
        headers=headers(actors[0]),
    )
    assert cancelled.status_code == 409
    reservation = offered(factory)
    with factory.begin() as db:
        db.get(m.Reservation, reservation.id).expires_at = db_now(db)
    assert lifecycle.tick(factory) == []
    promoted = offered(factory)
    assert promoted.entry_id == UUID(second.json()["entry_id"])
    pending = api.get(f"/api/v1/drops/{drop_id}/proof").json()
    assert pending["status"] == "pending" and pending["seed_commitment"] is None
    close_due(api, actors, factory, drop_id)
    assert lifecycle.tick(factory) == []
    proof = api.get(f"/api/v1/drops/{drop_id}/proof").json()
    assert proof["seed"] is None and proof["seed_commitment"] is None
    assert all(e["score_hex"] is None for e in proof["entries"])
    assert [e["public_entry_id"] for e in proof["entries"]] == [
        first.json()["public_entry_id"],
        second.json()["public_entry_id"],
    ]
    assert verify(proof)["ranking_reproduced"] is False
    actor = actor_for(actors, promoted.user_id)
    confirm = api.post(
        f"/api/v1/reservations/{promoted.id}/confirm", json={}, headers=headers(actor)
    )
    assert confirm.status_code == 200 and confirm.json()["status"] == "CONFIRMED"
    assert lifecycle.tick(factory) == []
    with factory() as db:
        assert db.get(m.Drop, UUID(drop_id)).phase == "COMPLETED"
        assert db.scalar(select(m.DrawRun.next_rank)) == 3
        assert db.scalar(select(func.count()).select_from(m.Reservation)) == 2


def test_fcfs_exhausted_slot_waits_for_new_admission(
    api, actors, draft_payload, factory, monkeypatch
):
    monkeypatch.setattr(get_settings(), "app_profile", "demo")
    drop_id = prepare_open(
        api, actors, {**draft_payload, "capacity": 1, "mode": "FCFS_DEMO"}, factory
    )
    path = f"/api/v1/drops/{drop_id}/entries"
    first = api.post(path, json={}, headers=headers(actors[1]))
    assert first.json()["status"] == "OFFERED"
    reservation = offered(factory)
    with factory.begin() as db:
        db.get(m.Reservation, reservation.id).expires_at = db_now(db)
    assert lifecycle.tick(factory) == []
    assert offered(factory) is None
    with factory() as db:
        assert db.get(m.Drop, UUID(drop_id)).phase == "OPEN"
    second = api.post(path, json={}, headers=headers(actors[2]))
    assert second.json()["status"] == "OFFERED"
    assert offered(factory).entry_id == UUID(second.json()["entry_id"])


def test_existing_demo_drop_cannot_allocate_in_normal_profile(
    api, actors, draft_payload, factory, monkeypatch
):
    monkeypatch.setattr(get_settings(), "app_profile", "demo")
    drop_id = prepare_open(
        api, actors, {**draft_payload, "capacity": 1, "mode": "FCFS_DEMO"}, factory
    )
    api.post(f"/api/v1/drops/{drop_id}/entries", json={}, headers=headers(actors[1]))
    close_due(api, actors, factory, drop_id)
    monkeypatch.setattr(get_settings(), "app_profile", "normal")
    assert api.get(f"/api/v1/drops/{drop_id}/proof").status_code == 404
    assert api.get(f"/api/v1/drops/{drop_id}").status_code == 404
    assert api.get("/api/v1/drops").json()["items"] == []
    assert lifecycle.tick(factory) == [UUID(drop_id)]
    with factory() as db:
        assert db.get(m.Drop, UUID(drop_id)).phase == "CLOSED"
        assert db.scalar(select(m.DrawRun.status)) == "FROZEN"

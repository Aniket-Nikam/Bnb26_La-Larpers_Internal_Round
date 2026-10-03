"""Real auth-to-allocation integration, without the core test security adapter."""

import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.allocation.lifecycle import tick
from app.audit.verifier import verify
from app.core.clock import db_now
from app.core.config import get_settings
from app.main import app
from app.persistence.database import session_factory
from app.persistence.models import Entry, LabRun, Session
from app.security.provisioning import provision_user_with_credential, revoke_credential


def login(client, code):
    response = client.post(
        "/api/v1/auth/session", json={"access_code": code}, headers={"Origin": "http://testclient"}
    )
    assert response.status_code == 200, response.text
    return response.json()


def write(client, path, csrf, body=None, key=None, method="POST"):
    return client.request(
        method,
        "/api/v1" + path,
        json=body or {},
        headers={
            "Origin": "http://testclient",
            "X-CSRF-Token": csrf,
            "Idempotency-Key": str(key or uuid4()),
        },
    )


def test_authenticated_entry_receipt_offer_confirmation_and_public_verifier(
    client, db, test_user, test_organizer
):
    org = login(client, test_organizer["raw_code"])
    now = db_now(db)
    payload = {
        "title": "Integrated draw",
        "description": "",
        "category": "test",
        "location_type": "venue",
        "location_label": "Hall",
        "capacity": 1,
        "starts_at": (now + timedelta(seconds=1)).isoformat(),
        "ends_at": (now + timedelta(seconds=3)).isoformat(),
        "confirmation_seconds": 30,
    }
    created = write(client, "/admin/drops", org["csrf_token"], payload)
    assert created.status_code == 201, created.text
    drop_id = created.json()["id"]
    assert (
        write(
            client,
            f"/admin/drops/{drop_id}/eligibility",
            org["csrf_token"],
            {"user_public_ids": [test_user["user"].public_id]},
        ).status_code
        == 200
    )
    assert write(client, f"/admin/drops/{drop_id}/publish", org["csrf_token"]).status_code == 200
    deadline = time.monotonic() + 5
    while client.get(f"/api/v1/drops/{drop_id}").json()["phase"] != "OPEN":
        assert time.monotonic() < deadline
        tick(session_factory())
        time.sleep(0.1)
    with (
        TestClient(app, base_url="http://testclient") as person,
        TestClient(app, base_url="http://testclient") as second_device,
    ):
        p1 = login(person, test_user["raw_code"])
        p2 = login(second_device, test_user["raw_code"])
        key = uuid4()
        response = write(person, f"/drops/{drop_id}/entries", p1["csrf_token"], key=key)
        assert response.status_code == 201, response.text
        entry_id = response.json()["entry_id"]
        assert (
            write(person, f"/drops/{drop_id}/entries", p1["csrf_token"], key=key).json()["entry_id"]
            == entry_id
        )
        assert (
            write(second_device, f"/drops/{drop_id}/entries", p2["csrf_token"]).json()["entry_id"]
            == entry_id
        )
        assert person.get(f"/api/v1/entries/{entry_id}").status_code == 200
        assert person.get("/api/v1/admin/drops").status_code == 403
        assert (
            person.post(
                f"/api/v1/drops/{drop_id}/entries",
                json={},
                headers={"Idempotency-Key": str(uuid4()), "Origin": "http://testclient"},
            ).status_code
            == 403
        )
        deadline = time.monotonic() + 6
        while True:
            tick(session_factory())
            state = person.get(f"/api/v1/drops/{drop_id}/me").json()["entry"]
            if state["reservation"]:
                break
            assert time.monotonic() < deadline
            time.sleep(0.1)
        reservation_id = state["reservation"]["id"]
        confirmed = write(person, f"/reservations/{reservation_id}/confirm", p1["csrf_token"])
        assert confirmed.status_code == 200, confirmed.text
        assert confirmed.json()["status"] == "CONFIRMED"
        public_proof = person.get(f"/api/v1/drops/{drop_id}/proof").json()
        assert verify(public_proof)["valid"]
        assert "user_id" not in str(public_proof) and "access_code" not in str(public_proof)
        assert (
            second_device.get(f"/api/v1/drops/{drop_id}/me").json()["entry"]["status"]
            == "CONFIRMED"
        )
        outsider_code = secrets.token_urlsafe(32)
        provision_user_with_credential(db, "Outsider", "participant", outsider_code)
        db.commit()
        with TestClient(app, base_url="http://testclient") as outsider:
            login(outsider, outsider_code)
            assert outsider.get(f"/api/v1/entries/{entry_id}").status_code == 404
            assert (
                write(
                    outsider, f"/reservations/{reservation_id}/confirm", p1["csrf_token"]
                ).status_code
                == 403
            )
            other = outsider.get("/api/v1/auth/me").json()
            assert (
                write(
                    outsider, f"/reservations/{reservation_id}/confirm", other["csrf_token"]
                ).status_code
                == 404
            )
        assert len(list(db.scalars(select(Entry).where(Entry.drop_id == UUID(drop_id))))) == 1
        assert (
            len(list(db.scalars(select(Session).where(Session.user_id == test_user["user"].id))))
            == 2
        )
        revoke_credential(db, test_user["credential"].id)
        db.commit()
        assert person.get("/api/v1/auth/me").status_code == 401
        assert second_device.get("/api/v1/auth/me").status_code == 401


def test_real_account_budget_survives_multiple_device_sessions(client, test_user):
    login(client, test_user["raw_code"])
    # Consume exactly the shared account quota across two session tokens.
    second = TestClient(app, base_url="http://testclient")
    login(second, test_user["raw_code"])
    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(
            pool.map(
                lambda i: (client if i % 2 else second).get("/api/v1/auth/me").status_code,
                range(40),
            )
        )
    assert statuses.count(200) == 30
    assert statuses.count(429) == 10


def test_profile_idempotency_is_durable_and_conflicts(client, test_user):
    session = login(client, test_user["raw_code"])
    key = uuid4()
    path = "/profile"
    response = write(
        client, path, session["csrf_token"], {"display_name": "Saved name"}, key, "PATCH"
    )
    assert response.status_code == 200
    assert (
        write(
            client, path, session["csrf_token"], {"display_name": "Saved name"}, key, "PATCH"
        ).status_code
        == 200
    )
    assert (
        write(
            client, path, session["csrf_token"], {"display_name": "Other name"}, key, "PATCH"
        ).status_code
        == 409
    )
    assert client.get("/api/v1/auth/me").json()["principal"]["display_name"] == "Saved name"


def test_lab_is_profile_gated_owner_scoped_and_idempotent(client, db, test_organizer, monkeypatch):
    org = login(client, test_organizer["raw_code"])
    cfg = get_settings()
    payload = {
        "scenario": "normal",
        "human_actors": 2,
        "bot_actors": 2,
        "duration_seconds": 1,
        "target_rps": 1,
        "retries_per_actor": 0,
        "trials": 1,
        "drop_capacity": 1,
    }
    assert write(client, "/admin/lab/runs", org["csrf_token"], payload).status_code == 404
    monkeypatch.setattr(cfg, "app_profile", "demo")
    monkeypatch.setattr(cfg, "lab_enabled", True)
    key = uuid4()
    started = write(client, "/admin/lab/runs", org["csrf_token"], payload, key)
    assert started.status_code == 202, started.text
    run_id = started.json()["run_id"]
    assert (
        write(client, "/admin/lab/runs", org["csrf_token"], payload, key).json()["run_id"] == run_id
    )
    assert write(client, "/admin/lab/runs", org["csrf_token"], payload).status_code == 409
    assert client.get(f"/api/v1/admin/lab/runs/{run_id}/report").json()["status"] == "pending"
    assert client.get(f"/api/v1/admin/lab/runs/{run_id}/export").status_code == 409
    code = secrets.token_urlsafe(32)
    provision_user_with_credential(db, "Other organizer", "organizer", code)
    db.commit()
    with TestClient(app, base_url="http://testclient") as other:
        principal = login(other, code)
        assert other.get(f"/api/v1/admin/lab/runs/{run_id}").status_code == 404
        assert (
            write(other, f"/admin/lab/runs/{run_id}/stop", principal["csrf_token"]).status_code
            == 404
        )
    assert (
        write(client, f"/admin/lab/runs/{run_id}/stop", org["csrf_token"]).json()["status"]
        == "STOPPED"
    )
    db.expire_all()
    assert db.get(LabRun, UUID(run_id)).status == "STOPPED"

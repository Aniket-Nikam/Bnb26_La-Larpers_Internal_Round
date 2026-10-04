from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.core.clock import db_now
from app.persistence import models as m

from .conftest import headers, prepare_open


def test_publication_locks_rules_and_exact_capacity(api, actors, draft_payload, factory):
    key = uuid4()
    path = "/api/v1/admin/drops"
    # Inputs may carry an offset, but every response must be canonical UTC with Z.
    for field in ("starts_at", "ends_at"):
        draft_payload[field] = (
            datetime.fromisoformat(draft_payload[field])
            .astimezone(timezone(timedelta(hours=5, minutes=30)))
            .isoformat()
        )
    created = api.post(path, json=draft_payload, headers=headers(actors[0], key))
    assert created.status_code == 201, created.text
    drop_id = created.json()["id"]
    assert created.json()["starts_at"].endswith("Z")
    assert created.json()["server_time"].endswith("Z")
    repeat = api.post(path, json=draft_payload, headers=headers(actors[0], key))
    assert repeat.json()["id"] == drop_id
    conflict = api.post(
        path, json={**draft_payload, "title": "different"}, headers=headers(actors[0], key)
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert api.get(f"/api/v1/drops/{drop_id}").status_code == 404
    assert api.get("/api/v1/drops").json()["items"] == []
    published = api.post(
        f"/api/v1/admin/drops/{drop_id}/publish", json={}, headers=headers(actors[0])
    )
    assert published.status_code == 200
    assert len(published.json()["seed_commitment"]) == 64
    with factory() as db:
        slots = db.scalar(
            select(func.count()).select_from(m.SeatSlot).where(m.SeatSlot.drop_id == UUID(drop_id))
        )
        assert slots == draft_payload["capacity"]
    for edit in ({"capacity": 3}, {"mode": "FCFS_DEMO"}, {"category": "other"}):
        response = api.patch(
            f"/api/v1/admin/drops/{drop_id}", json=edit, headers=headers(actors[0])
        )
        assert response.status_code == 409
    edit = api.patch(
        f"/api/v1/admin/drops/{drop_id}", json={"title": "Updated"}, headers=headers(actors[0])
    )
    assert edit.json()["title"] == "Updated"
    removed_grant_route = api.post(
        f"/api/v1/admin/drops/{drop_id}/eligibility",
        json={"user_public_ids": [actors[1].public_id]},
        headers=headers(actors[0]),
    )
    assert removed_grant_route.status_code == 404
    forbidden = api.post(
        f"/api/v1/admin/drops/{drop_id}/publish", json={}, headers=headers(actors[1])
    )
    assert forbidden.status_code == 403
    other = api.patch(
        f"/api/v1/admin/drops/{drop_id}", json={"title": "Stolen"}, headers=headers(actors[3])
    )
    assert other.status_code == 404


def test_concurrent_same_account_same_and_different_keys(api, actors, draft_payload, factory):
    drop_id = prepare_open(api, actors, draft_payload, factory)
    path = f"/api/v1/drops/{drop_id}/entries"
    key = uuid4()
    keys = [key] * 8 + [uuid4() for _ in range(8)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(
            pool.map(lambda k: api.post(path, json={}, headers=headers(actors[1], k)), keys)
        )
    assert all(r.status_code in (200, 201) for r in results), [
        (r.status_code, r.text) for r in results
    ]
    assert sum(r.status_code == 201 for r in results) == 1
    assert len({r.json()["entry_id"] for r in results}) == 1
    entry_id = results[0].json()["entry_id"]
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(m.Entry)) == 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(m.AuditEvent)
                .where(m.AuditEvent.event_type == "ENTRY_ACCEPTED")
            )
            == 1
        )
    # Simulated devices are distinct HTTP requests using one principal; P2 tests real sessions.
    assert (
        api.get(f"/api/v1/drops/{drop_id}/me", headers=headers(actors[1])).json()["entry"][
            "entry_id"
        ]
        == entry_id
    )
    assert api.get(f"/api/v1/entries/{entry_id}", headers=headers(actors[2])).status_code == 404
    assert api.get("/api/v1/entries", headers=headers(actors[2])).json()["items"] == []
    assert api.get("/api/v1/entries").status_code == 401
    with factory.begin() as db:
        drop = db.get(m.Drop, UUID(drop_id))
        drop.ends_at = db_now(db) - timedelta(seconds=1)
    assert api.post(path, json={}, headers=headers(actors[1], key)).status_code == 200
    late = api.post(path, json={}, headers=headers(actors[2]))
    assert late.status_code == 409 and late.json()["error"]["code"] == "ENTRY_CLOSED"
    assert (
        api.get(f"/api/v1/entries/{entry_id}", headers=headers(actors[1])).json()["entry"][
            "entry_id"
        ]
        == entry_id
    )


def test_cancel_pagination_and_draft_validation(api, actors, draft_payload, factory):
    created = api.post("/api/v1/admin/drops", json=draft_payload, headers=headers(actors[0]))
    drop_id = created.json()["id"]
    bad = api.patch(
        f"/api/v1/admin/drops/{drop_id}",
        json={"starts_at": draft_payload["ends_at"]},
        headers=headers(actors[0]),
    )
    assert bad.status_code == 422
    bad = api.patch(
        f"/api/v1/admin/drops/{drop_id}", json={"title": None}, headers=headers(actors[0])
    )
    assert bad.status_code == 422
    # Cancel an actual accepted entry; no deletion of receipt.
    opened = prepare_open(api, actors, draft_payload, factory)
    accepted = api.post(
        f"/api/v1/drops/{opened}/entries", json={}, headers=headers(actors[1])
    ).json()
    response = api.post(
        f"/api/v1/admin/drops/{opened}/cancel",
        json={"reason": "Event cancelled"},
        headers=headers(actors[0]),
    )
    assert response.status_code == 200, response.text
    assert (
        api.get(f"/api/v1/entries/{accepted['entry_id']}", headers=headers(actors[1])).json()[
            "entry"
        ]["status"]
        == "CANCELLED"
    )
    assert api.get("/api/v1/drops?cursor=invalid").status_code == 422
    assert api.get("/api/v1/drops?limit=101").status_code == 422
    metrics = api.get(f"/api/v1/admin/drops/{opened}/metrics", headers=headers(actors[0])).json()
    assert metrics["integrity_ok"] and metrics["entered_count"] == 1

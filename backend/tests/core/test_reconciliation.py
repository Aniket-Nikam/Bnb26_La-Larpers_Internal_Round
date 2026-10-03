from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.allocation.lifecycle import tick
from app.core.clock import db_now
from app.core.config import Settings
from app.persistence import models as m

from .conftest import headers


def test_worker_opens_closes_and_completes_missed_schedule(api, actors, draft_payload, factory):
    created = api.post("/api/v1/admin/drops", json=draft_payload, headers=headers(actors[0]))
    drop_id = created.json()["id"]
    publish = api.post(
        f"/api/v1/admin/drops/{drop_id}/publish", json={}, headers=headers(actors[0])
    )
    assert publish.status_code == 200
    assert (
        api.post(
            f"/api/v1/admin/drops/{drop_id}/open", json={}, headers=headers(actors[0])
        ).status_code
        == 409
    )
    assert (
        api.post(
            f"/api/v1/admin/drops/{drop_id}/close", json={}, headers=headers(actors[0])
        ).status_code
        == 409
    )
    with factory.begin() as db:
        drop = db.get(m.Drop, UUID(drop_id))
        now = db_now(db)
        drop.starts_at, drop.ends_at = now - timedelta(minutes=2), now - timedelta(minutes=1)
    assert tick(factory) == []
    with factory() as db:
        drop = db.get(m.Drop, UUID(drop_id))
        assert drop.phase == "COMPLETED"
        events = set(db.scalars(select(m.AuditEvent.event_type)))
        assert events >= {
            "PUBLISHED",
            "OPENED",
            "MANIFEST_FROZEN",
            "DRAW_STARTED",
            "RANKING_PUBLISHED",
            "COMPLETED",
        }


def test_database_outage_is_explicit_safe_and_correlated(api, monkeypatch):
    from app import main
    from app.persistence import database

    def unavailable():
        raise OperationalError(
            "private SQL text", {}, RuntimeError("private infrastructure detail")
        )

    request_id = str(uuid4())
    monkeypatch.setattr(main, "get_engine", unavailable)
    ready = api.get("/api/health/ready")
    assert ready.status_code == 503 and ready.json()["status"] == "unavailable"
    assert not ready.json()["capabilities"]["safe_reads"]
    monkeypatch.setattr(database, "get_engine", unavailable)
    response = api.get("/api/v1/drops", headers={"X-Request-ID": request_id})
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "TEMPORARILY_UNAVAILABLE" and error["retryable"]
    assert error["request_id"] == response.headers["X-Request-ID"] == request_id
    assert "private" not in response.text
    assert api.get("/api/health/live").status_code == 200


def test_invalid_pool_origin_and_placeholder_keys_fail_closed():
    for values in (
        {"public_origin": "https://fairdrop.test/path"},
        {"db_pool_size": 0},
        {"db_max_overflow": -1},
        {"worker_tick_seconds": 0},
        {"worker_batch": 101},
    ):
        with pytest.raises(ValueError):
            Settings(app_profile="test", **values)
    with pytest.raises(ValueError):
        Settings(
            app_profile="normal",
            session_digest_key="insecure" * 8,
            credential_digest_key="insecure" * 8,
        )

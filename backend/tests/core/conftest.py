import os

os.environ.setdefault("APP_PROFILE", "test")
# Tests require a caller-provided, migrated disposable PostgreSQL database.
if "DATABASE_URL" not in os.environ:
    raise RuntimeError("Set DATABASE_URL to a migrated disposable PostgreSQL test database.")

import base64
import secrets
from datetime import timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

os.environ.setdefault("SEED_ENCRYPTION_KEY", base64.b64encode(secrets.token_bytes(32)).decode())


@pytest.fixture
def factory():
    from app.core.config import get_settings
    from app.persistence.database import session_factory

    cfg = get_settings()
    if cfg.app_profile != "test" or not cfg.database_url.split("?")[0].endswith("_test"):
        raise RuntimeError("Core fixtures may reset ONLY a test-profile database ending _test")
    maker = session_factory()
    with maker.begin() as db:
        db.execute(
            text(
                "TRUNCATE users, access_credentials, sessions, drops, eligibility_grants, entries, "
                "seat_slots, reservations, draw_runs, frozen_entries, draw_ranks, audit_events, "
                "idempotency_operations, lab_runs CASCADE"
            )
        )
    return maker


@pytest.fixture
def actors(factory):
    from app.core.schemas import Principal
    from app.persistence.models import User

    with factory.begin() as db:
        users = [
            User(display_name="Organizer", role="organizer"),
            User(display_name="Participant"),
            User(display_name="Other"),
            User(display_name="Other organizer", role="organizer"),
        ]
        db.add_all(users)
        db.flush()
        return [Principal.model_validate(u) for u in users]


@pytest.fixture
def api(actors, monkeypatch):
    """Test-only security adapter. Does not claim P2 auth/session/CSRF/limiter evidence."""
    from app.core.errors import DomainError
    from app.drops import router as routes
    from app.main import app
    from app.security.authorization import get_principal, require_organizer

    def principal(request):
        actor_id = request.headers.get("X-Test-Principal")
        actor = next((a for a in actors if str(a.id) == actor_id), None)
        if actor is None:
            raise DomainError("SESSION_REQUIRED", "Session required.", 401)
        return actor

    from fastapi import Request

    # FastAPI dependency annotations must be concrete after nested function creation.
    principal.__annotations__["request"] = Request

    def organizer(request):
        actor = principal(request)
        if actor.role not in {"organizer", "admin"}:
            raise DomainError("FORBIDDEN", "Organizer required.", 403)
        return actor

    organizer.__annotations__["request"] = Request
    app.dependency_overrides[get_principal] = principal
    app.dependency_overrides[require_organizer] = organizer
    monkeypatch.setattr(routes, "get_principal", principal)
    monkeypatch.setattr(routes, "require_drop_access", lambda p, d: None)
    monkeypatch.setattr(routes, "enforce_limit", lambda request, p, action: None)
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def draft_payload(factory):
    from app.core.clock import db_now

    with factory() as db:
        now = db_now(db)
    return dict(
        title="Fair workshop",
        description="One saved entry.",
        category="workshop",
        location_type="venue",
        location_label="Hall",
        capacity=2,
        starts_at=(now + timedelta(minutes=5)).isoformat(),
        ends_at=(now + timedelta(minutes=10)).isoformat(),
        confirmation_seconds=60,
        mode="LOTTERY",
    )


def headers(actor, key=None):
    from uuid import uuid4

    return {"X-Test-Principal": str(actor.id), "Idempotency-Key": str(key or uuid4())}


def prepare_open(api, actors, payload, factory):
    """Time travel fixture only; production clocks/deadlines are never user mutable."""
    from app.core.clock import db_now
    from app.persistence.models import Drop

    created = api.post("/api/v1/admin/drops", json=payload, headers=headers(actors[0]))
    assert created.status_code == 201, created.text
    drop_id = created.json()["id"]
    grant = api.post(
        f"/api/v1/admin/drops/{drop_id}/eligibility",
        json={"user_public_ids": [a.public_id for a in actors[1:3]]},
        headers=headers(actors[0]),
    )
    assert grant.status_code == 200, grant.text
    published = api.post(
        f"/api/v1/admin/drops/{drop_id}/publish", json={}, headers=headers(actors[0])
    )
    assert published.status_code == 200, published.text
    with factory.begin() as db:
        drop = db.get(Drop, UUID(drop_id))
        drop.starts_at = db_now(db) - timedelta(minutes=1)
    opened = api.post(f"/api/v1/admin/drops/{drop_id}/open", json={}, headers=headers(actors[0]))
    assert opened.status_code == 200, opened.text
    return drop_id

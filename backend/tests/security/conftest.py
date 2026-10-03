"""Real migrated PostgreSQL/Redis tests. Never create/drop schema or bypass auth."""

import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.main import app
from app.persistence.database import session_factory
from app.security.limits import get_redis
from app.security.provisioning import provision_user_with_credential


@pytest.fixture
def db():
    cfg = get_settings()
    if cfg.app_profile != "test" or not cfg.database_url.split("?")[0].endswith("_test"):
        raise RuntimeError("Security fixtures require a disposable migrated _test database")
    if cfg.redis_url.rsplit("/", 1)[-1] not in {"1", "15"}:
        raise RuntimeError("Security fixtures require disposable Redis database 1 or 15")
    get_redis().flushdb()
    maker = session_factory()
    with maker.begin() as session:
        session.execute(text("TRUNCATE users CASCADE"))
    with maker() as session:
        yield session


@pytest.fixture
def client(db):
    with TestClient(app, base_url="http://testclient") as client:
        yield client


def provision(db, name, role):
    raw = secrets.token_urlsafe(32)
    user, credential = provision_user_with_credential(db, name, role, raw)
    db.commit()
    return {"user": user, "credential": credential, "raw_code": raw}


@pytest.fixture
def test_user(db):
    return provision(db, "Participant", "participant")


@pytest.fixture
def test_organizer(db):
    return provision(db, "Organizer", "organizer")


@pytest.fixture
def authenticated_client(client, test_user):
    response = client.post(
        "/api/v1/auth/session",
        json={"access_code": test_user["raw_code"]},
        headers={"Origin": "http://testclient"},
    )
    assert response.status_code == 200, response.text
    return {
        "client": client,
        "csrf_token": response.json()["csrf_token"],
        "principal": response.json()["principal"],
        "session": response.json(),
    }

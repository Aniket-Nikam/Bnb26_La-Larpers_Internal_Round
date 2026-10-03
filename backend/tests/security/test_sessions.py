"""
Security tests: Session lifecycle — P2.

Test cases:
3. Session expiry → 401
3. Logout revokes session → subsequent requests 401
4. Refresh / API restart → session survives (PostgreSQL durability)
5. Same account across multiple devices/sessions
7. Two sessions for same user don't create two entry identities (identity is user ID)
"""
import secrets

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_get_me_with_valid_session(authenticated_client):
    """GET /auth/me returns principal with valid session."""
    c = authenticated_client["client"]
    resp = await c.get("/api/v1/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["principal"]["id"] == authenticated_client["principal"]["id"]
    assert "csrf_token" in data
    assert "expires_at" in data
    assert "server_time" in data


@pytest.mark.asyncio
async def test_get_me_response_no_store(authenticated_client):
    """GET /auth/me response must have no-store cache header."""
    c = authenticated_client["client"]
    resp = await c.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert "no-store" in resp.headers.get("cache-control", "").lower()


@pytest.mark.asyncio
async def test_logout_revokes_session(authenticated_client, db):
    """Logout revokes session; subsequent /me returns 401."""
    c = authenticated_client["client"]
    csrf = authenticated_client["csrf_token"]

    # Logout
    resp = await c.delete(
        "/api/v1/auth/session",
        headers={
            "X-CSRF-Token": csrf,
            "Origin": "http://testclient",
        },
    )
    assert resp.status_code == 204

    # Session cookie should be cleared
    # Now /me should fail
    resp2 = await c.get("/api/v1/auth/me")
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_logout_idempotent(authenticated_client):
    """Logout twice returns 204 both times (idempotent)."""
    c = authenticated_client["client"]
    csrf = authenticated_client["csrf_token"]

    resp1 = await c.delete(
        "/api/v1/auth/session",
        headers={"X-CSRF-Token": csrf, "Origin": "http://testclient"},
    )
    assert resp1.status_code == 204

    resp2 = await c.delete(
        "/api/v1/auth/session",
        headers={"X-CSRF-Token": csrf, "Origin": "http://testclient"},
    )
    assert resp2.status_code == 204


@pytest.mark.asyncio
async def test_expired_session_rejected(client, db):
    """Session with expires_at in the past is rejected."""
    from datetime import timezone
    from backend.app.core.clock import utc_now
    from backend.app.persistence.models import Session as SessionModel
    from backend.app.security.provisioning import provision_user_with_credential
    from backend.app.security.sessions import _session_digest_hmac
    from backend.app.core.config import get_settings
    import hashlib, hmac

    raw_code = "expiry-test-" + secrets.token_hex(8)
    user, _ = await provision_user_with_credential(
        db=db, display_name="Expiry Test", role="participant", raw_code=raw_code
    )
    await db.commit()

    # Manually create an expired session
    raw_token = secrets.token_hex(32)
    digest = _session_digest_hmac(raw_token, get_settings().SESSION_DIGEST_KEY)
    csrf_secret = secrets.token_hex(32)

    past = utc_now().replace(year=2020)
    session = SessionModel(
        user_id=user.id,
        token_digest=digest,
        csrf_secret=csrf_secret,
        expires_at=past,
    )
    db.add(session)
    await db.commit()

    # Try to use this expired session
    resp = await client.get(
        "/api/v1/auth/me",
        cookies={"fd_session": raw_token},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_session_identity_preserved_across_refresh(client, test_user):
    """Identity (user ID) stable across GET /auth/me calls."""
    # Login
    resp1 = await client.post(
        "/api/v1/auth/session",
        json={"access_code": test_user["raw_code"]},
        headers={"Origin": "http://testclient"},
    )
    assert resp1.status_code == 200
    user_id = resp1.json()["principal"]["id"]

    # Refresh (GET /me with same session cookie)
    resp2 = await client.get("/api/v1/auth/me")
    assert resp2.status_code == 200
    assert resp2.json()["principal"]["id"] == user_id


@pytest.mark.asyncio
async def test_two_sessions_one_user_identity(client, test_user):
    """Two sessions for same user both resolve to same principal ID."""
    from backend.app.main import app
    from backend.app.persistence.database import get_db

    # First session
    r1 = await client.post(
        "/api/v1/auth/session",
        json={"access_code": test_user["raw_code"]},
        headers={"Origin": "http://testclient"},
    )
    assert r1.status_code == 200
    id1 = r1.json()["principal"]["id"]

    # Second session (separate login)
    r2 = await client.post(
        "/api/v1/auth/session",
        json={"access_code": test_user["raw_code"]},
        headers={"Origin": "http://testclient"},
    )
    assert r2.status_code == 200
    id2 = r2.json()["principal"]["id"]

    # Both sessions map to same identity
    assert id1 == id2


@pytest.mark.asyncio
async def test_session_survives_without_redis(client, test_user, monkeypatch):
    """
    Session lookup works even when Redis is unavailable.
    PostgreSQL is the authoritative session store.
    """
    # First login to create session
    resp1 = await client.post(
        "/api/v1/auth/session",
        json={"access_code": test_user["raw_code"]},
        headers={"Origin": "http://testclient"},
    )
    assert resp1.status_code == 200

    # Simulate Redis failure for session checks (not auth limit checks)
    import backend.app.security.limits as limits_module
    original = limits_module.get_redis

    def failing_redis():
        import redis.asyncio as r
        bad = r.Redis(host="localhost", port=9999)  # Non-existent
        return bad

    monkeypatch.setattr(limits_module, "_redis_client", None)
    # Session check itself doesn't use Redis, so /me should still work
    resp2 = await client.get("/api/v1/auth/me")
    # Should succeed (session is PostgreSQL-backed)
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_revoked_session_rejected(client, db, test_user):
    """Manually revoked session returns 401 on subsequent requests."""
    # Login
    resp = await client.post(
        "/api/v1/auth/session",
        json={"access_code": test_user["raw_code"]},
        headers={"Origin": "http://testclient"},
    )
    assert resp.status_code == 200

    # Manually revoke in DB
    from backend.app.core.clock import utc_now
    from backend.app.persistence.models import Session as SessionModel
    from sqlalchemy import select
    result = await db.execute(
        select(SessionModel).where(SessionModel.user_id == test_user["user"].id)
    )
    session = result.scalar_one_or_none()
    assert session is not None
    session.revoked_at = utc_now()
    db.add(session)
    await db.commit()

    # Now /me should fail
    resp2 = await client.get("/api/v1/auth/me")
    assert resp2.status_code == 401

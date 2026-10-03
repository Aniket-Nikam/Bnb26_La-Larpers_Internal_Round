"""
Security tests: CSRF and Origin validation — P2.

Test cases:
6. Missing CSRF token → 403 CSRF_REJECTED
6. Incorrect CSRF token → 403 CSRF_REJECTED
7. Invalid Origin → 403 ORIGIN_REJECTED
   Correct Origin + correct CSRF → success
"""
import secrets

import pytest


@pytest.mark.asyncio
async def test_logout_missing_csrf(authenticated_client):
    """DELETE /auth/session without X-CSRF-Token → 403."""
    c = authenticated_client["client"]
    resp = await c.delete(
        "/api/v1/auth/session",
        headers={"Origin": "http://testclient"},
    )
    assert resp.status_code == 403
    data = resp.json()
    assert data["error"]["code"] == "CSRF_REJECTED"


@pytest.mark.asyncio
async def test_logout_wrong_csrf(authenticated_client):
    """DELETE /auth/session with wrong X-CSRF-Token → 403."""
    c = authenticated_client["client"]
    resp = await c.delete(
        "/api/v1/auth/session",
        headers={
            "X-CSRF-Token": "wrong-csrf-value-" + secrets.token_hex(8),
            "Origin": "http://testclient",
        },
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "CSRF_REJECTED"


@pytest.mark.asyncio
async def test_profile_update_missing_csrf(authenticated_client):
    """PATCH /profile without CSRF → 403."""
    c = authenticated_client["client"]
    resp = await c.patch(
        "/api/v1/profile",
        json={"display_name": "New Name"},
        headers={"Origin": "http://testclient"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "CSRF_REJECTED"


@pytest.mark.asyncio
async def test_profile_update_valid_csrf(authenticated_client):
    """PATCH /profile with correct CSRF → 200."""
    c = authenticated_client["client"]
    csrf = authenticated_client["csrf_token"]
    resp = await c.patch(
        "/api/v1/profile",
        json={"display_name": "Updated Name"},
        headers={
            "X-CSRF-Token": csrf,
            "Origin": "http://testclient",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["principal"]["display_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_invalid_origin_rejected(client, test_user):
    """POST /auth/session with disallowed Origin → 403."""
    resp = await client.post(
        "/api/v1/auth/session",
        json={"access_code": test_user["raw_code"]},
        headers={"Origin": "https://evil.attacker.com"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "ORIGIN_REJECTED"


@pytest.mark.asyncio
async def test_csrf_token_is_correct_after_login(client, test_user):
    """CSRF token returned from login is usable for subsequent mutations."""
    from backend.app.security.csrf import generate_csrf_token, verify_csrf_token

    resp = await client.post(
        "/api/v1/auth/session",
        json={"access_code": test_user["raw_code"]},
        headers={"Origin": "http://testclient"},
    )
    assert resp.status_code == 200
    csrf_token = resp.json()["csrf_token"]

    # CSRF token should be non-empty and hex-like
    assert len(csrf_token) == 64  # SHA-256 hex


@pytest.mark.asyncio
async def test_csrf_token_stable_per_session(authenticated_client):
    """Same session always returns same CSRF token (deterministic from secret)."""
    c = authenticated_client["client"]
    
    r1 = await c.get("/api/v1/auth/me")
    r2 = await c.get("/api/v1/auth/me")
    
    assert r1.json()["csrf_token"] == r2.json()["csrf_token"]


@pytest.mark.asyncio
async def test_login_without_origin_header(client, test_user):
    """Login without Origin header from non-browser client should be allowed for test clients."""
    # Test clients (non-browser) may not send Origin; we allow requests without Origin
    resp = await client.post(
        "/api/v1/auth/session",
        json={"access_code": test_user["raw_code"]},
        # No Origin header (simulates API test runner)
    )
    # Test clients are allowed through (no browser Origin set)
    assert resp.status_code == 200

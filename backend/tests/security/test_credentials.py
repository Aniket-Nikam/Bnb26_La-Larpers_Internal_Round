"""
Security tests: Credential authentication — P2.

Test cases:
1. Correct credential → 200 + session cookie
2. Incorrect credential → 401
3. Expired credential → 401
4. Revoked credential → 401
5. Credential guessing rate limiting
6. Raw credential never in response body
7. Login does not create new user
8. Multiple logins same credential → same user identity
"""

import secrets


def test_login_correct_credential(client, test_user):
    """Correct credential returns 200 with session cookie and no raw token."""
    resp = client.post(
        "/api/v1/auth/session",
        json={"access_code": test_user["raw_code"]},
        headers={"Origin": "http://testclient"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # SessionResponse structure
    assert "principal" in data
    assert "csrf_token" in data
    assert "expires_at" in data
    assert "server_time" in data

    # No raw credential in response
    assert test_user["raw_code"] not in resp.text

    # Session cookie set
    assert "fd_session" in resp.cookies

    # Principal identity
    assert data["principal"]["id"] == str(test_user["user"].id)
    assert data["principal"]["role"] == "participant"


def test_login_incorrect_credential(client):
    """Wrong credential returns 401 without revealing reason."""
    resp = client.post(
        "/api/v1/auth/session",
        json={"access_code": "totally-wrong-code-" + secrets.token_hex(8)},
        headers={"Origin": "http://testclient"},
    )
    assert resp.status_code == 401
    data = resp.json()
    assert data["error"]["code"] == "SESSION_REQUIRED"
    # No credential enumeration info
    assert "account" not in data["error"]["message"].lower()
    assert "exists" not in data["error"]["message"].lower()


def test_login_expired_credential(client, db):
    """Expired credential returns 401."""
    from app.core.clock import utc_now
    from app.security.provisioning import provision_user_with_credential

    past = utc_now().replace(year=2020)  # Already expired
    raw_code = "expired-code-" + secrets.token_hex(8)
    user, credential = provision_user_with_credential(
        db=db,
        display_name="Expired User",
        role="participant",
        raw_code=raw_code,
        expires_at=past,
    )
    db.commit()

    resp = client.post(
        "/api/v1/auth/session",
        json={"access_code": raw_code},
        headers={"Origin": "http://testclient"},
    )
    assert resp.status_code == 401


def test_login_revoked_credential(client, db):
    """Revoked credential returns 401."""
    from app.security.provisioning import provision_user_with_credential, revoke_credential

    raw_code = "revoked-code-" + secrets.token_hex(8)
    user, credential = provision_user_with_credential(
        db=db,
        display_name="Revoked User",
        role="participant",
        raw_code=raw_code,
    )
    revoke_credential(db, credential.id)
    db.commit()

    resp = client.post(
        "/api/v1/auth/session",
        json={"access_code": raw_code},
        headers={"Origin": "http://testclient"},
    )
    assert resp.status_code == 401


def test_login_no_raw_credential_in_error(client):
    """Ensure raw credential never appears in error responses."""
    secret_code = "my-secret-code-" + secrets.token_hex(16)
    resp = client.post(
        "/api/v1/auth/session",
        json={"access_code": secret_code},
        headers={"Origin": "http://testclient"},
    )
    assert resp.status_code in (401, 429, 503)
    assert secret_code not in resp.text


def test_login_multiple_sessions_same_user(client, test_user):
    """Same credential used multiple times → same user identity."""
    ids = set()
    for _ in range(3):
        resp = client.post(
            "/api/v1/auth/session",
            json={"access_code": test_user["raw_code"]},
            headers={"Origin": "http://testclient"},
        )
        assert resp.status_code == 200
        ids.add(resp.json()["principal"]["id"])

    # All sessions map to the same user
    assert len(ids) == 1


def test_login_no_cookie_no_session(client):
    """GET /auth/me without cookie returns 401."""
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "SESSION_REQUIRED"


def test_login_does_not_create_new_user(client, db, test_user):
    """Login with same credential always returns same user, never creates another."""
    from sqlalchemy import func, select

    from app.persistence.models import User

    # Count users before
    before = db.execute(select(func.count(User.id)))
    count_before = before.scalar()

    # Login twice
    for _ in range(2):
        resp = client.post(
            "/api/v1/auth/session",
            json={"access_code": test_user["raw_code"]},
            headers={"Origin": "http://testclient"},
        )
        assert resp.status_code == 200

    after = db.execute(select(func.count(User.id)))
    count_after = after.scalar()

    # No new users created
    assert count_before == count_after

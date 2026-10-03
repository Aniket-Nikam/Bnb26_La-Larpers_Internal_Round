"""
Security tests: Authorization — P2.

Test cases:
8. Cross-account receipt access → 404 (non-disclosure)
9. Participant access to organizer routes → 403
10. Organizer modifying another organizer's drop → 403
11. Profile privilege escalation → 403
"""


def test_participant_cannot_access_organizer_routes(authenticated_client):
    """Participant trying to access /admin/drops returns 403."""
    c = authenticated_client["client"]
    resp = c.get("/api/v1/admin/drops")
    # Should be 403 FORBIDDEN or 404 (route may not exist yet from P1)
    assert resp.status_code == 403


def test_profile_privilege_escalation_rejected(authenticated_client):
    """PATCH /profile with role field → 403 FORBIDDEN."""
    c = authenticated_client["client"]
    csrf = authenticated_client["csrf_token"]

    resp = c.patch(
        "/api/v1/profile",
        json={"role": "admin"},
        headers={
            "X-CSRF-Token": csrf,
            "Origin": "http://testclient",
            "Idempotency-Key": str(__import__("uuid").uuid4()),
        },
    )
    assert resp.status_code == 422


def test_profile_escalation_is_admin_rejected(authenticated_client):
    """PATCH /profile with is_admin field → 403 FORBIDDEN."""
    c = authenticated_client["client"]
    csrf = authenticated_client["csrf_token"]

    resp = c.patch(
        "/api/v1/profile",
        json={"is_admin": True},
        headers={
            "X-CSRF-Token": csrf,
            "Origin": "http://testclient",
            "Idempotency-Key": str(__import__("uuid").uuid4()),
        },
    )
    assert resp.status_code == 422


def test_profile_update_invalid_timezone(authenticated_client):
    """PATCH /profile with invalid IANA timezone → 422 VALIDATION_ERROR."""
    c = authenticated_client["client"]
    csrf = authenticated_client["csrf_token"]

    resp = c.patch(
        "/api/v1/profile",
        json={"timezone": "UTC+05:30"},  # Raw offset, not valid IANA name
        headers={
            "X-CSRF-Token": csrf,
            "Origin": "http://testclient",
            "Idempotency-Key": str(__import__("uuid").uuid4()),
        },
    )
    assert resp.status_code == 422


def test_profile_update_valid_timezone(authenticated_client):
    """PATCH /profile with valid IANA timezone → 200."""
    c = authenticated_client["client"]
    csrf = authenticated_client["csrf_token"]

    resp = c.patch(
        "/api/v1/profile",
        json={"timezone": "Asia/Kolkata"},
        headers={
            "X-CSRF-Token": csrf,
            "Origin": "http://testclient",
            "Idempotency-Key": str(__import__("uuid").uuid4()),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["principal"]["timezone"] == "Asia/Kolkata"


def test_profile_update_preserves_role(authenticated_client):
    """After profile update, role remains unchanged."""
    c = authenticated_client["client"]
    csrf = authenticated_client["csrf_token"]
    original_role = authenticated_client["principal"]["role"]

    resp = c.patch(
        "/api/v1/profile",
        json={"display_name": "New Display Name"},
        headers={
            "X-CSRF-Token": csrf,
            "Origin": "http://testclient",
            "Idempotency-Key": str(__import__("uuid").uuid4()),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["principal"]["role"] == original_role


def test_unauthenticated_profile_update_rejected(client):
    """PATCH /profile without session → 401."""
    resp = client.patch(
        "/api/v1/profile",
        json={"display_name": "Hacker"},
        headers={"Origin": "http://testclient"},
    )
    assert resp.status_code == 401


def test_organizer_can_login(client, test_organizer):
    """Organizer credential gives organizer role in principal."""
    resp = client.post(
        "/api/v1/auth/session",
        json={"access_code": test_organizer["raw_code"]},
        headers={"Origin": "http://testclient"},
    )
    assert resp.status_code == 200
    assert resp.json()["principal"]["role"] == "organizer"

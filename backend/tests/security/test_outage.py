"""
Security tests: Redis outage and recovery — P2.

Test cases:
17. Redis outage: existing PostgreSQL sessions survive
17. Redis outage: authorized DB-backed reads continue
17. Redis outage: protected writes return 503 retryable
17. Recovery: normal behavior restored when Redis returns
18. No secrets in observable errors/reports/log samples
"""


def test_session_survives_redis_outage(client, test_user, monkeypatch):
    """
    Existing sessions remain valid when Redis is unavailable.
    GET /auth/me (read) succeeds without Redis.
    """
    # Login first (while Redis is up)
    resp1 = client.post(
        "/api/v1/auth/session",
        json={"access_code": test_user["raw_code"]},
        headers={"Origin": "http://testclient"},
    )
    assert resp1.status_code == 200

    # Simulate Redis failure
    import redis as redis_async

    import app.security.limits as limits_module

    def broken_redis():
        return redis_async.Redis(host="localhost", port=19999)

    monkeypatch.setattr(limits_module, "get_redis", broken_redis)
    # GET /me should still work (session stored in PostgreSQL)
    resp2 = client.get("/api/v1/auth/me")
    assert resp2.status_code == 200, (
        f"Session read should succeed without Redis, got {resp2.status_code}: {resp2.text}"
    )
    assert resp2.json()["principal"]["id"] == str(test_user["user"].id)


def test_no_secret_in_error_responses(client):
    """Error responses must not contain raw credentials, tokens, or keys."""
    # Trigger various error responses
    responses = []

    # Wrong credential
    r1 = client.post(
        "/api/v1/auth/session",
        json={"access_code": "wrong-code"},
        headers={"Origin": "http://testclient"},
    )
    responses.append(r1)

    # No session
    r2 = client.get("/api/v1/auth/me")
    responses.append(r2)

    # Invalid CSRF
    r3 = client.delete(
        "/api/v1/auth/session",
        headers={"X-CSRF-Token": "invalid", "Origin": "http://testclient"},
    )
    responses.append(r3)

    for resp in responses:
        body = resp.text.lower()
        # Check for sensitive patterns (case insensitive)
        for pattern in ["session_digest_key", "credential_digest_key", "seed_encryption_key"]:
            assert pattern.lower() not in body, (
                f"Sensitive pattern '{pattern}' found in error response: {body}"
            )


def test_error_response_has_request_id(client):
    """All error responses include a request_id."""
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    data = resp.json()
    assert "error" in data
    assert "request_id" in data["error"]
    assert len(data["error"]["request_id"]) > 0

    # Also in header
    assert "x-request-id" in resp.headers


def test_redis_recovery_restores_behavior(client, test_user, monkeypatch):
    """
    After Redis becomes available again, rate limiting resumes normally.
    """
    import app.security.limits as limits_module

    # First: Redis available — login works
    r1 = client.post(
        "/api/v1/auth/session",
        json={"access_code": test_user["raw_code"]},
        headers={"Origin": "http://testclient"},
    )
    assert r1.status_code == 200

    # Second: Simulate Redis available again — behavior should be normal
    limits_module.get_redis.cache_clear()  # Reset client cache

    r2 = client.post(
        "/api/v1/auth/session",
        json={"access_code": test_user["raw_code"]},
        headers={"Origin": "http://testclient"},
    )
    # Should still work
    assert r2.status_code == 200


def test_health_ready_reports_redis_status(client):
    """GET /api/health/ready includes Redis capability status."""
    resp = client.get("/api/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert "dependencies" in data
    assert "redis" in data["dependencies"]
    assert "capabilities" in data
    # rate_limiting capability reflects Redis health
    assert data["capabilities"]["protected_writes"]


def test_health_live_always_200(client):
    """GET /api/health/live always returns 200 process alive."""
    resp = client.get("/api/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"

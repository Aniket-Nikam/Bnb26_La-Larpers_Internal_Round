import base64
import hashlib
import json
import time

import pytest

from app.core.errors import DomainError
from app.security.altcha import create_altcha_challenge, verify_altcha_payload


def test_altcha_challenge_generation():
    challenge = create_altcha_challenge(max_number=1000, expires_in_seconds=120)
    assert challenge["algorithm"] == "SHA-256"
    assert len(challenge["challenge"]) == 64
    assert len(challenge["signature"]) == 64
    assert challenge["maxnumber"] == 1000
    assert "?expires=" in challenge["salt"]


def test_altcha_solve_and_verify():
    challenge_data = create_altcha_challenge(max_number=5000, expires_in_seconds=300)
    salt = challenge_data["salt"]
    target = challenge_data["challenge"]

    # Solve PoW
    solution = None
    for i in range(5001):
        if hashlib.sha256(f"{salt}{i}".encode("utf-8")).hexdigest() == target:
            solution = i
            break

    assert solution is not None

    payload = {
        "algorithm": "SHA-256",
        "challenge": target,
        "number": solution,
        "salt": salt,
        "signature": challenge_data["signature"],
    }
    payload_b64 = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")

    # Should verify successfully
    assert verify_altcha_payload(payload_b64) is True


def test_altcha_tampered_solution_rejected():
    challenge_data = create_altcha_challenge(max_number=1000, expires_in_seconds=300)
    payload = {
        "algorithm": "SHA-256",
        "challenge": challenge_data["challenge"],
        "number": 999999,  # Incorrect number
        "salt": challenge_data["salt"],
        "signature": challenge_data["signature"],
    }
    with pytest.raises(DomainError) as exc_info:
        verify_altcha_payload(payload)
    assert exc_info.value.code == "ALTCHA_INVALID"


def test_altcha_tampered_signature_rejected():
    challenge_data = create_altcha_challenge(max_number=1000, expires_in_seconds=300)
    payload = {
        "algorithm": "SHA-256",
        "challenge": challenge_data["challenge"],
        "number": 0,
        "salt": challenge_data["salt"],
        "signature": "0000000000000000000000000000000000000000000000000000000000000000",
    }
    with pytest.raises(DomainError) as exc_info:
        verify_altcha_payload(payload)
    assert exc_info.value.code == "ALTCHA_INVALID"


def test_altcha_expired_challenge_rejected():
    # Expired 10 seconds ago
    challenge_data = create_altcha_challenge(max_number=100, expires_in_seconds=-10)
    salt = challenge_data["salt"]
    target = challenge_data["challenge"]

    solution = None
    for i in range(101):
        if hashlib.sha256(f"{salt}{i}".encode("utf-8")).hexdigest() == target:
            solution = i
            break

    payload = {
        "algorithm": "SHA-256",
        "challenge": target,
        "number": solution,
        "salt": salt,
        "signature": challenge_data["signature"],
    }
    with pytest.raises(DomainError) as exc_info:
        verify_altcha_payload(payload)
    assert exc_info.value.code == "ALTCHA_EXPIRED"


def test_altcha_api_endpoint_and_register(client):
    res = client.get("/api/v1/security/altcha/challenge")
    assert res.status_code == 200
    data = res.json()
    assert data["algorithm"] == "SHA-256"
    assert "salt" in data
    assert "challenge" in data
    assert "signature" in data

    # Solve challenge returned by API
    salt = data["salt"]
    target = data["challenge"]
    max_num = data["maxnumber"]
    sol = None
    for i in range(max_num + 1):
        if hashlib.sha256(f"{salt}{i}".encode("utf-8")).hexdigest() == target:
            sol = i
            break
    assert sol is not None

    payload = {
        "algorithm": "SHA-256",
        "challenge": target,
        "number": sol,
        "salt": salt,
        "signature": data["signature"],
    }
    payload_b64 = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")

    # Register with solved ALTCHA payload
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Altcha User",
            "email": "altcha_user@example.com",
            "phone_number": "+14155559999",
            "password": "strong password 123",
            "altcha_payload": payload_b64,
        },
        headers={"Origin": "http://testclient"},
    )
    assert reg.status_code == 201

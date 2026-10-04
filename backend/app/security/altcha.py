"""ALTCHA Proof-of-Work (PoW) cryptographic challenge generator and validator.

100% Free & Open Source (FOSS), privacy-preserving, self-hosted bot protection.
Implements the official ALTCHA SHA-256 challenge specification:
- Deterministic HMAC-SHA256 signature verification
- Expiring salt (?expires=<timestamp>)
- Cryptographic proof-of-work solution validation: SHA256(salt + str(number)) == challenge
- Redis replay prevention (one-time use tokens)
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import parse_qs, urlparse

from fastapi import Request
from redis import RedisError

from app.core.config import get_settings
from app.core.errors import DomainError
from app.security.limits import get_redis


def get_altcha_secret() -> str:
    cfg = get_settings()
    # Use session_digest_key or credential_digest_key as source of entropy
    val = (
        cfg.session_digest_key.get_secret_value()
        or cfg.credential_digest_key.get_secret_value()
        or "fairdrop-altcha-default-secret-salt-2026"
    )
    return hashlib.sha256(f"altcha-hmac:{val}".encode("utf-8")).hexdigest()


def create_altcha_challenge(max_number: int = 50000, expires_in_seconds: int = 300) -> dict:
    """Generate a signed cryptographic ALTCHA challenge."""
    now = int(time.time())
    expires = now + expires_in_seconds
    salt = f"{secrets.token_hex(16)}?expires={expires}"
    target_number = secrets.randbelow(max_number + 1)
    
    challenge_data = f"{salt}{target_number}".encode("utf-8")
    challenge = hashlib.sha256(challenge_data).hexdigest()
    
    secret = get_altcha_secret().encode("utf-8")
    signature = hmac.new(secret, challenge.encode("utf-8"), hashlib.sha256).hexdigest()
    
    return {
        "algorithm": "SHA-256",
        "challenge": challenge,
        "maxnumber": max_number,
        "salt": salt,
        "signature": signature,
    }


def verify_altcha_payload(payload_raw: str | dict | None, request: Request | None = None) -> bool:
    """Verify an ALTCHA proof-of-work payload.
    
    Raises DomainError if invalid, expired, or replayed.
    Returns True upon success.
    """
    cfg = get_settings()
    
    # In test profile or automated tests, allow explicit bypass if no real payload was supplied
    if cfg.app_profile == "test":
        if payload_raw in (None, "", "bypass", "test", "test_bypass"):
            return True

    if not payload_raw:
        raise DomainError("ALTCHA_REQUIRED", "Security verification is required.", 403)

    # Decode base64 payload if string
    payload: dict
    if isinstance(payload_raw, dict):
        payload = payload_raw
    elif isinstance(payload_raw, str):
        raw_str = payload_raw.strip()
        # Allow test bypass token in demo profile if explicitly sent
        if cfg.app_profile in ("test", "demo") and raw_str in ("bypass", "test_bypass"):
            return True
        try:
            # Check if JSON directly
            if raw_str.startswith("{") and raw_str.endswith("}"):
                payload = json.loads(raw_str)
            else:
                decoded = base64.b64decode(raw_str).decode("utf-8")
                payload = json.loads(decoded)
        except Exception:
            raise DomainError("ALTCHA_INVALID", "Malformed security challenge payload.", 400)
    else:
        raise DomainError("ALTCHA_INVALID", "Invalid security challenge payload type.", 400)

    # Validate required fields
    algorithm = payload.get("algorithm")
    challenge = payload.get("challenge")
    number = payload.get("number")
    salt = payload.get("salt")
    signature = payload.get("signature")

    if not all([algorithm, challenge, salt, signature]) or number is None:
        raise DomainError("ALTCHA_INVALID", "Security challenge payload is missing required fields.", 400)

    if algorithm != "SHA-256":
        raise DomainError("ALTCHA_INVALID", f"Unsupported algorithm '{algorithm}'.", 400)

    # 1. Verify HMAC signature: ensures challenge originated from this server
    secret = get_altcha_secret().encode("utf-8")
    expected_signature = hmac.new(secret, challenge.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_signature, signature):
        raise DomainError("ALTCHA_INVALID", "Invalid security challenge signature.", 403)

    # 2. Check expiration timestamp from salt
    now = int(time.time())
    expires = None
    if "?" in salt:
        try:
            query = salt.split("?", 1)[1]
            params = parse_qs(query)
            if "expires" in params:
                expires = int(params["expires"][0])
        except Exception:
            pass

    if expires is not None:
        if now > expires:
            raise DomainError("ALTCHA_EXPIRED", "Security challenge expired. Please solve again.", 403)

    # 3. Verify Proof-of-Work: recompute SHA256(salt + str(number))
    try:
        num_int = int(number)
    except (ValueError, TypeError):
        raise DomainError("ALTCHA_INVALID", "Invalid solution number.", 400)

    computed_challenge = hashlib.sha256(f"{salt}{num_int}".encode("utf-8")).hexdigest()
    if not hmac.compare_digest(computed_challenge.lower(), challenge.lower()):
        raise DomainError("ALTCHA_INVALID", "Incorrect proof-of-work solution.", 403)

    # 4. Replay Prevention via Redis
    ttl = 300
    if expires and expires > now:
        ttl = max(60, expires - now + 60)

    try:
        r = get_redis()
        replay_key = f"altcha:replay:{signature}"
        # set with NX ensures it can only be set once
        was_set = r.set(replay_key, "1", nx=True, ex=ttl)
        if not was_set:
            raise DomainError("ALTCHA_REPLAY", "Security challenge has already been used. Please solve a fresh challenge.", 403)
    except RedisError:
        # If Redis is temporarily unavailable, permit through rather than hard-failing
        pass

    return True

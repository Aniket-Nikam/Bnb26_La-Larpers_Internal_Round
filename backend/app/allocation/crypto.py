import hashlib
import hmac
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings

ALGORITHM = "hmac-sha256-v1"


def protect_seed(drop_id, seed):
    nonce = secrets.token_bytes(12)
    return nonce + AESGCM(get_settings().seed_key()).encrypt(nonce, seed, str(drop_id).encode())


def reveal_seed(drop_id, encrypted):
    return AESGCM(get_settings().seed_key()).decrypt(
        encrypted[:12], encrypted[12:], str(drop_id).encode()
    )


def seed_commitment(seed):
    return hashlib.sha256(seed).hexdigest()


def manifest_bytes(ids):
    return b"".join((value + "\n").encode("utf-8") for value in sorted(ids))


def manifest_commitment(ids):
    return hashlib.sha256(manifest_bytes(ids)).hexdigest()


def score(seed, drop_id, public_entry_id):
    message = f"fair-drop:v1:{str(drop_id).lower()}:{public_entry_id}".encode("utf-8")
    return hmac.digest(seed, message, "sha256")

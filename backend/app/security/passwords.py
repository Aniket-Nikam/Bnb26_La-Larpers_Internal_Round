"""Password account authentication using salted, memory-hard scrypt hashes."""

import base64
import hashlib
import hmac
import secrets

from sqlalchemy import func, select

from app.persistence.models import AccessCredential, User

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
_DUMMY_HASH = (
    "scrypt$16384$8$1$AAAAAAAAAAAAAAAAAAAAAA==$"
    + base64.b64encode(
        hashlib.scrypt(b"invalid-password", salt=b"\0" * 16, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)
    ).decode()
)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)
    return "$".join(
        (
            "scrypt",
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            base64.b64encode(salt).decode(),
            base64.b64encode(digest).decode(),
        )
    )


def verify_password(password: str, encoded: str | None) -> bool:
    encoded = encoded or _DUMMY_HASH
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(
            password.encode(),
            salt=base64.b64decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
        )
        return hmac.compare_digest(actual, base64.b64decode(expected))
    except (ValueError, TypeError):
        return False


def verify_account(db, email: str, password: str):
    user = db.scalar(select(User).where(func.lower(User.email) == email.lower()))
    valid = verify_password(password, user.password_hash if user else None)
    if not user or not valid or not user.is_active:
        return None
    credential = db.scalar(
        select(AccessCredential).where(
            AccessCredential.user_id == user.id,
            AccessCredential.label == "account-password",
            AccessCredential.revoked_at.is_(None),
        )
    )
    return (user, credential) if credential else None

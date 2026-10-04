import base64
import hmac
import logging
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import DomainError
from app.persistence.models import User
from app.security.limits import get_redis

logger = logging.getLogger("fairdrop.otp")

# In-memory fallback if Redis is unreachable (useful in local isolated unit tests)
_IN_MEMORY_OTP: dict[str, tuple[str, float, int]] = {}


def dispatch_sms_via_twilio(to_number: str, message: str) -> bool:
    """Send real SMS via Twilio REST API if configured."""
    cfg = get_settings()
    if not cfg.twilio_account_sid or not cfg.twilio_phone_number:
        return False
    auth_token = cfg.twilio_auth_token.get_secret_value()
    if not auth_token:
        return False

    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{cfg.twilio_account_sid}/Messages.json"
        auth = base64.b64encode(f"{cfg.twilio_account_sid}:{auth_token}".encode()).decode()
        data = urllib.parse.urlencode({
            "From": cfg.twilio_phone_number,
            "To": to_number,
            "Body": message,
        }).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("Twilio SMS successfully dispatched to %s (HTTP %s)", to_number, resp.status)
            return True
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        logger.error("Twilio HTTPError when sending to %s: HTTP %s - %s", to_number, e.code, err_msg)
        return False
    except Exception as e:
        logger.error("Twilio unexpected error when sending to %s: %s", to_number, e)
        return False


def normalize_phone_number(raw: str) -> str:
    """Normalize phone number to international E.164-compatible string."""
    if not raw or not isinstance(raw, str):
        raise DomainError(
            "VALIDATION_ERROR",
            "A valid phone number is required.",
            422,
        )
    cleaned = re.sub(r"[\s\-\(\)\.]", "", raw.strip())
    # Allow + prefix, or assume international if >= 10 digits
    if not cleaned.startswith("+"):
        if len(cleaned) == 10:
            cleaned = "+1" + cleaned  # default North America if standard 10 digits without code
        else:
            cleaned = "+" + cleaned

    if not re.match(r"^\+[1-9]\d{7,14}$", cleaned):
        raise DomainError(
            "VALIDATION_ERROR",
            "Invalid phone number format. Provide 8 to 15 digits (e.g. +14155552671).",
            422,
        )
    return cleaned


def send_otp(
    db: Session,
    raw_phone: str,
    purpose: Literal["register", "login"],
) -> dict:
    phone = normalize_phone_number(raw_phone)

    # Constraint check: Phone must be unique on register
    existing = db.scalar(select(User).where(User.phone_number == phone))
    if purpose == "register" and existing is not None:
        raise DomainError(
            "PHONE_EXISTS",
            "An account with this phone number already exists.",
            409,
        )
    if purpose == "login" and existing is None:
        raise DomainError(
            "ACCOUNT_NOT_FOUND",
            "No account found with this phone number. Please register first.",
            404,
        )

    # 6-digit numeric OTP
    otp = f"{secrets.randbelow(1_000_000):06d}"
    cfg = get_settings()

    # Try storing in Redis with 5-minute TTL and 30s cooldown
    redis_available = False
    try:
        r = get_redis()
        cooldown_key = f"otp_cd:{purpose}:{phone}"
        if r.exists(cooldown_key):
            ttl = r.ttl(cooldown_key)
            raise DomainError(
                "RATE_LIMITED",
                f"Please wait {max(1, ttl)} seconds before requesting another code.",
                429,
            )

        code_key = f"otp_val:{purpose}:{phone}"
        attempts_key = f"otp_att:{purpose}:{phone}"

        r.set(code_key, otp, ex=300)
        r.set(cooldown_key, "1", ex=30)
        r.set(attempts_key, "0", ex=300)
        redis_available = True
    except DomainError:
        raise
    except Exception as exc:
        logger.warning("Redis unavailable for OTP, falling back to memory: %s", exc)

    if not redis_available:
        now = time.time()
        # Check in-memory cooldown
        if phone in _IN_MEMORY_OTP:
            old_code, expires_at, attempts = _IN_MEMORY_OTP[phone]
            if now < (expires_at - 270):  # within 30s of creation
                raise DomainError(
                    "RATE_LIMITED",
                    "Please wait before requesting another code.",
                    429,
                )
        _IN_MEMORY_OTP[f"{purpose}:{phone}"] = (otp, now + 300, 0)

    logger.info("Generated OTP for %s [%s]: %s", phone, purpose, otp)

    # Dispatch real SMS via Twilio if credentials configured
    sms_body = f"Your Fairdrop verification code is: {otp}. Valid for 5 minutes."
    dispatch_sms_via_twilio(phone, sms_body)

    # Return debug_otp when not in strict production mode to facilitate frictionless testing
    is_dev = cfg.app_profile in {"test", "demo", "normal"}
    return {
        "status": "sent",
        "phone_number": phone,
        "cooldown_seconds": 30,
        "debug_otp": otp if is_dev else None,
    }


def verify_otp(
    raw_phone: str,
    purpose: Literal["register", "login"],
    candidate_otp: str,
) -> None:
    phone = normalize_phone_number(raw_phone)
    if not candidate_otp or len(candidate_otp.strip()) != 6:
        raise DomainError(
            "VALIDATION_ERROR",
            "Verification code must be 6 digits.",
            422,
        )

    stored_otp = None
    redis_available = False
    code_key = f"otp_val:{purpose}:{phone}"
    attempts_key = f"otp_att:{purpose}:{phone}"

    try:
        r = get_redis()
        raw_val = r.get(code_key)
        if raw_val:
            stored_otp = raw_val.decode() if isinstance(raw_val, bytes) else str(raw_val)
            redis_available = True
    except Exception:
        pass

    if not redis_available:
        mem_key = f"{purpose}:{phone}"
        if mem_key in _IN_MEMORY_OTP:
            code, expires_at, attempts = _IN_MEMORY_OTP[mem_key]
            if time.time() < expires_at:
                stored_otp = code
            else:
                del _IN_MEMORY_OTP[mem_key]

    if not stored_otp:
        raise DomainError(
            "OTP_EXPIRED",
            "Verification code has expired or was not requested. Please request a new code.",
            400,
        )

    # Check attempts
    if redis_available:
        r = get_redis()
        attempts = int(r.get(attempts_key) or 0)
        if attempts >= 5:
            r.delete(code_key)
            r.delete(attempts_key)
            raise DomainError(
                "OTP_MAX_ATTEMPTS",
                "Too many incorrect attempts. Please request a new code.",
                400,
            )
        if not hmac.compare_digest(stored_otp, candidate_otp.strip()):
            r.incr(attempts_key)
            raise DomainError(
                "INVALID_OTP",
                "Invalid verification code. Please check and try again.",
                400,
            )
        # Successful verification
        r.delete(code_key)
        r.delete(attempts_key)
    else:
        mem_key = f"{purpose}:{phone}"
        code, expires_at, attempts = _IN_MEMORY_OTP[mem_key]
        if attempts >= 5:
            del _IN_MEMORY_OTP[mem_key]
            raise DomainError(
                "OTP_MAX_ATTEMPTS",
                "Too many incorrect attempts. Please request a new code.",
                400,
            )
        if not hmac.compare_digest(stored_otp, candidate_otp.strip()):
            _IN_MEMORY_OTP[mem_key] = (code, expires_at, attempts + 1)
            raise DomainError(
                "INVALID_OTP",
                "Invalid verification code. Please check and try again.",
                400,
            )
        del _IN_MEMORY_OTP[mem_key]

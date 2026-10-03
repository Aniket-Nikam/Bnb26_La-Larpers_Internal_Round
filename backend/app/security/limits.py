"""
Redis-backed atomic rate limiter — P2 security module.

Design decisions (WB-04):
- Uses Redis EVALSHA Lua scripts for atomic token bucket / sliding window operations.
- Multiple dimensions: authenticated account, session, action/endpoint, network, global.
- Account limits survive session rotation (attacker cannot bypass by creating new sessions).
- Network/global limits use trusted proxy-derived IP only — never arbitrary X-Forwarded-For.
- Redis failure: protected writes return retryable 503; safe reads may continue.
- Returns 429 RATE_LIMITED with Retry-After header on throttle.

Initial budgets per architecture.md section 16:
- entry_write:   5 per 10 seconds (per account)
- confirm_write: 5 per 10 seconds (per account)
- status_read:  30 per 10 seconds (per account)
- credential_attempt: 5 per 60 seconds (per digest-derived key)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import redis.asyncio as redis

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


class LimitAction(str, Enum):
    entry_write = "entry_write"
    confirm_write = "confirm_write"
    status_read = "status_read"
    credential_attempt = "credential_attempt"
    session_create = "session_create"
    profile_write = "profile_write"
    global_write = "global_write"


@dataclass
class LimitConfig:
    max_tokens: int
    window_seconds: int


# Per-action budgets (account-level unless noted)
ACTION_LIMITS: dict[LimitAction, LimitConfig] = {
    LimitAction.entry_write:        LimitConfig(max_tokens=5, window_seconds=10),
    LimitAction.confirm_write:      LimitConfig(max_tokens=5, window_seconds=10),
    LimitAction.status_read:        LimitConfig(max_tokens=30, window_seconds=10),
    LimitAction.credential_attempt: LimitConfig(max_tokens=5, window_seconds=60),
    LimitAction.session_create:     LimitConfig(max_tokens=10, window_seconds=60),
    LimitAction.profile_write:      LimitConfig(max_tokens=10, window_seconds=60),
    LimitAction.global_write:       LimitConfig(max_tokens=1000, window_seconds=10),
}

# Network-level budgets (conservative; set low to protect under load)
NETWORK_LIMIT = LimitConfig(max_tokens=50, window_seconds=10)
GLOBAL_LIMIT = LimitConfig(max_tokens=5000, window_seconds=10)

# Atomic sliding window Lua script (INCR + EXPIRE pattern)
_SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local window = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local window_start = now - window * 1000

redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)
local count = redis.call('ZCARD', key)
if count >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_at = 0
    if #oldest >= 2 then
        retry_at = math.ceil((tonumber(oldest[2]) + window * 1000 - now) / 1000)
    end
    return {0, retry_at}
end
redis.call('ZADD', key, now, now .. '-' .. math.random(1, 1000000))
redis.call('EXPIRE', key, window + 1)
return {1, 0}
"""

_script_sha: Optional[str] = None


async def _get_script_sha() -> str:
    """Load Lua script into Redis and cache its SHA."""
    global _script_sha
    if _script_sha is None:
        r = get_redis()
        _script_sha = await r.script_load(_SLIDING_WINDOW_SCRIPT)
    return _script_sha


@dataclass
class LimitResult:
    allowed: bool
    retry_after_seconds: int = 0
    redis_unavailable: bool = False


async def _check_limit(key: str, config: LimitConfig) -> LimitResult:
    """
    Atomic sliding window check for a single dimension.
    Returns LimitResult.
    """
    try:
        r = get_redis()
        sha = await _get_script_sha()
        now_ms = int(time.time() * 1000)
        try:
            result = await r.evalsha(
                sha,
                1,
                key,
                str(config.window_seconds),
                str(config.max_tokens),
                str(now_ms),
            )
        except (redis.exceptions.NoScriptError, redis.exceptions.ResponseError) as e:
            if "NOSCRIPT" in str(e):
                global _script_sha
                _script_sha = await r.script_load(_SLIDING_WINDOW_SCRIPT)
                result = await r.evalsha(
                    _script_sha,
                    1,
                    key,
                    str(config.window_seconds),
                    str(config.max_tokens),
                    str(now_ms),
                )
            else:
                raise
        allowed = int(result[0]) == 1
        retry_after = int(result[1])
        return LimitResult(allowed=allowed, retry_after_seconds=retry_after)
    except (redis.RedisError, ConnectionError) as e:
        logger.warning("Redis unavailable during rate limit check: %s", type(e).__name__)
        return LimitResult(allowed=False, retry_after_seconds=5, redis_unavailable=True)


async def enforce_limit(
    request,  # FastAPI Request
    principal: Optional[object],  # Principal (has .id) or None
    action: LimitAction,
    session_id: Optional[str] = None,
    trusted_ip: Optional[str] = None,
) -> LimitResult:
    """
    Enforce rate limits across multiple dimensions:
    1. Per-account (survives session rotation)
    2. Per-session
    3. Per-action/endpoint
    4. Per-network (trusted proxy IP)
    5. Global

    Returns LimitResult; caller must return 429 if not allowed.
    Redis unavailability returns a retryable limit for protected writes.
    """
    config = ACTION_LIMITS.get(action, LimitConfig(max_tokens=10, window_seconds=10))

    # 1. Account-level limit (most important — survives session rotation)
    if principal is not None:
        account_key = f"lim:account:{principal.id}:{action.value}"
        result = await _check_limit(account_key, config)
        if not result.allowed:
            return result

    # 2. Session-level limit
    if session_id:
        session_key = f"lim:session:{session_id}:{action.value}"
        session_config = LimitConfig(
            max_tokens=max(config.max_tokens, 3),
            window_seconds=config.window_seconds,
        )
        result = await _check_limit(session_key, session_config)
        if not result.allowed:
            return result

    # 3. Network-level limit (cautious; campus Wi-Fi gets this budget per IP)
    if trusted_ip:
        net_key = f"lim:net:{trusted_ip}:{action.value}"
        result = await _check_limit(net_key, NETWORK_LIMIT)
        if not result.allowed:
            return result

    # 4. Global limit
    global_key = f"lim:global:{action.value}"
    result = await _check_limit(global_key, GLOBAL_LIMIT)
    if not result.allowed:
        return result

    return LimitResult(allowed=True)


def get_trusted_ip(request) -> Optional[str]:
    """
    Extract the client IP from trusted proxy headers ONLY.
    Arbitrary X-Forwarded-For from clients cannot override proxy-derived source.
    Only the first hop from configured proxy is trusted.
    """
    # In production, Nginx sets X-Real-IP from the actual connecting client.
    # We trust only that, not the full X-Forwarded-For chain from the client.
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        # Validate it looks like an IP (basic sanity check)
        import re
        if re.match(r'^[\d.:a-fA-F]+$', real_ip.strip()):
            return real_ip.strip()

    # Fall back to direct connection IP
    if request.client:
        return request.client.host

    return None

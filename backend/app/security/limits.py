"""Shared P2 sliding windows; all dimensions debit atomically on Redis time."""

import hashlib
import hmac
import ipaddress
from functools import lru_cache
from uuid import uuid4

from redis import Redis, RedisError

from app.core.config import get_settings
from app.core.errors import DomainError

# Read every window before debiting any. Redis TIME avoids replica clock skew.
SCRIPT = """
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + tonumber(t[2]) / 1000
local retry = 0
for i,key in ipairs(KEYS) do
  local window = tonumber(ARGV[i*2-1])
  local limit = tonumber(ARGV[i*2])
  redis.call('ZREMRANGEBYSCORE', key, '-inf', now-window*1000)
  if redis.call('ZCARD', key) >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    retry = math.max(retry, math.ceil((tonumber(oldest[2])+window*1000-now)/1000))
  end
end
if retry > 0 then return retry end
for i,key in ipairs(KEYS) do
  redis.call('ZADD', key, now, ARGV[#KEYS*2+1])
  redis.call('EXPIRE', key, tonumber(ARGV[i*2-1])+1)
end
return 0
"""


@lru_cache
def get_redis():
    return Redis.from_url(get_settings().redis_url, socket_timeout=1, socket_connect_timeout=1)


def get_trusted_ip(request):
    peer = request.client.host if request.client else "unknown"
    # The gateway replaces X-Real-IP. Only an explicitly trusted peer may supply it.
    try:
        trusted = any(
            ipaddress.ip_address(peer) in ipaddress.ip_network(net.strip())
            for net in get_settings().trusted_proxy_cidrs.split(",")
            if net.strip()
        )
        value = request.headers.get("X-Real-IP") if trusted else peer
        return str(ipaddress.ip_address(value))
    except ValueError:
        return peer


def enforce_limit(request, principal, action, credential_digest=None):
    budgets = {
        "entry": (5, 10),
        "confirmation": (5, 10),
        "status": (30, 10),
        "credential_attempt": (5, 60),
        "profile": (10, 60),
        "organizer": (60, 10),
    }
    limit, window = budgets.get(action, (10, 60))
    cfg = get_settings()
    network = hmac.new(
        cfg.session_digest_key.get_secret_value().encode(),
        get_trusted_ip(request).encode(),
        hashlib.sha256,
    ).hexdigest()
    dimensions = [
        (f"fd:lim:network:{network}:{action}", 1000, 10),
        (f"fd:lim:global:{action}", 10000, 10),
    ]
    if principal:
        dimensions.append((f"fd:lim:account:{principal.id}:{action}", limit, window))
    if getattr(request.state, "session_id", None):
        dimensions.append((f"fd:lim:session:{request.state.session_id}:{action}", limit, window))
    if credential_digest:
        dimensions.append((f"fd:lim:credential:{credential_digest}", limit, window))
    # Login network budget remains generous for a campus NAT; credential budget is specific.
    args = [value for _, maximum, seconds in dimensions for value in (seconds, maximum)]
    try:
        retry = int(
            get_redis().eval(
                SCRIPT, len(dimensions), *[key for key, _, _ in dimensions], *args, str(uuid4())
            )
        )
    except RedisError:
        if request.method in {"GET", "HEAD"}:
            return
        raise DomainError(
            "TEMPORARILY_UNAVAILABLE",
            "Admission protection temporarily unavailable.",
            503,
            True,
            headers={"Retry-After": "5"},
        ) from None
    if retry:
        raise DomainError(
            "RATE_LIMITED",
            "Retry after the indicated delay.",
            429,
            True,
            headers={"Retry-After": str(max(1, retry))},
        )

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from .crypto import keyed_digest
from .errors import rate_limited, temporarily_unavailable
from .protocols import RedisScriptBackend


ATOMIC_FIXED_WINDOW_LUA = r"""
local dimensions = #KEYS
local retry_ms = 0
for index = 1, dimensions do
  local limit = tonumber(ARGV[(index - 1) * 2 + 1])
  local current = tonumber(redis.call('GET', KEYS[index]) or '0')
  if current >= limit then
    local ttl = redis.call('PTTL', KEYS[index])
    if ttl < 1 then ttl = tonumber(ARGV[(index - 1) * 2 + 2]) end
    if ttl > retry_ms then retry_ms = ttl end
  end
end
if retry_ms > 0 then return {0, retry_ms} end
for index = 1, dimensions do
  local window_ms = tonumber(ARGV[(index - 1) * 2 + 2])
  local count = redis.call('INCR', KEYS[index])
  if count == 1 then redis.call('PEXPIRE', KEYS[index], window_ms) end
end
return {1, 0}
""".strip()


class LimitAction(StrEnum):
    LOGIN = "login"
    ENTRY_WRITE = "entry_write"
    CONFIRM_WRITE = "confirm_write"
    STATUS_READ = "status_read"


@dataclass(frozen=True, slots=True)
class LimitRule:
    limit: int
    window_seconds: int


@dataclass(frozen=True, slots=True)
class LimitDecision:
    allowed: bool
    degraded: bool = False


DEFAULT_RULES: dict[LimitAction, dict[str, LimitRule]] = {
    LimitAction.LOGIN: {
        "credential": LimitRule(5, 60),
        "network": LimitRule(100, 60),
        "global": LimitRule(2_000, 60),
    },
    LimitAction.ENTRY_WRITE: {
        "account": LimitRule(5, 10),
        "session": LimitRule(5, 10),
        "network": LimitRule(200, 10),
        "global": LimitRule(2_000, 10),
    },
    LimitAction.CONFIRM_WRITE: {
        "account": LimitRule(5, 10),
        "session": LimitRule(5, 10),
        "network": LimitRule(200, 10),
        "global": LimitRule(2_000, 10),
    },
    LimitAction.STATUS_READ: {
        "account": LimitRule(30, 10),
        "session": LimitRule(30, 10),
        "network": LimitRule(1_000, 10),
        "global": LimitRule(5_000, 10),
    },
}


class RateLimiter:
    def __init__(
        self,
        backend: RedisScriptBackend,
        digest_key: bytes,
        rules: dict[LimitAction, dict[str, LimitRule]] | None = None,
    ):
        self.backend = backend
        self.digest_key = digest_key
        self.rules = rules or DEFAULT_RULES

    def enforce(
        self,
        *,
        action: LimitAction,
        account_id: str | None,
        session_digest_value: str | None,
        source_address: str,
        credential_value: str | None = None,
    ) -> LimitDecision:
        dimensions = self._dimensions(
            action=action,
            account_id=account_id,
            session_digest_value=session_digest_value,
            source_address=source_address,
            credential_value=credential_value,
        )
        keys = [f"{{fairdrop}}:limit:{action.value}:{name}:{value}" for name, value, _ in dimensions]
        arguments: list[int] = []
        for _, _, rule in dimensions:
            arguments.extend((rule.limit, rule.window_seconds * 1_000))
        try:
            result = self.backend.eval(ATOMIC_FIXED_WINDOW_LUA, len(keys), *keys, *arguments)
        except Exception as exc:
            if action == LimitAction.STATUS_READ:
                return LimitDecision(True, degraded=True)
            raise temporarily_unavailable() from exc
        if not result or int(result[0]) != 1:
            retry_ms = int(result[1]) if len(result) > 1 else 1_000
            raise rate_limited(math.ceil(max(1, retry_ms) / 1_000))
        return LimitDecision(True)

    def _dimensions(
        self,
        *,
        action: LimitAction,
        account_id: str | None,
        session_digest_value: str | None,
        source_address: str,
        credential_value: str | None,
    ) -> list[tuple[str, str, LimitRule]]:
        rules = self.rules[action]
        values: dict[str, str] = {
            "network": keyed_digest(self.digest_key, "network-limit-v1", source_address)[:32],
            "global": "all",
        }
        if account_id:
            values["account"] = keyed_digest(self.digest_key, "account-limit-v1", account_id)[:32]
        if session_digest_value:
            values["session"] = session_digest_value[:32]
        if credential_value:
            values["credential"] = keyed_digest(
                self.digest_key, "credential-attempt-limit-v1", credential_value
            )[:32]
        missing = set(rules) - set(values)
        if missing:
            raise ValueError(f"missing limiter dimensions: {', '.join(sorted(missing))}")
        return [(name, values[name], rule) for name, rule in rules.items()]

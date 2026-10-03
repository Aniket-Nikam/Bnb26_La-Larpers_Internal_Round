from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class Scenario(StrEnum):
    NORMAL = "normal"
    EARLY_BOT = "early_bot"
    RETRY_FLOOD = "retry_flood"
    CREDENTIAL_FARM = "credential_farm"
    SHARED_IP = "shared_ip"
    RECONNECT = "reconnect"
    WORKER_RESTART = "worker_restart"
    EXPIRY_RACE = "expiry_race"
    REDIS_FAILURE = "redis_failure"
    POLICY_COMPARE = "policy_compare"


class RunStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


TERMINAL_STATUSES = {RunStatus.STOPPED, RunStatus.COMPLETED, RunStatus.FAILED}


@dataclass(frozen=True, slots=True)
class LabLimits:
    max_identities: int = 50_000
    max_rps: float = 2_000.0
    max_duration_seconds: int = 300
    max_trials: int = 20
    max_retries_per_actor: int = 20
    max_drop_capacity: int = 500


@dataclass(frozen=True, slots=True)
class RunConfig:
    scenario: Scenario
    human_actors: int
    bot_actors: int
    duration_seconds: int
    target_rps: float
    retries_per_actor: int
    trials: int
    drop_capacity: int

    @property
    def identity_count(self) -> int:
        return self.human_actors + self.bot_actors

    @classmethod
    def from_dict(cls, value: dict[str, Any], limits: LabLimits) -> RunConfig:
        allowed = {
            "scenario",
            "human_actors",
            "bot_actors",
            "duration_seconds",
            "target_rps",
            "retries_per_actor",
            "trials",
            "drop_capacity",
        }
        unexpected = set(value) - allowed
        if unexpected:
            raise ValueError(f"unsupported run fields: {', '.join(sorted(unexpected))}")

        try:
            config = cls(
                scenario=Scenario(value["scenario"]),
                human_actors=_strict_int(value["human_actors"], "human_actors"),
                bot_actors=_strict_int(value["bot_actors"], "bot_actors"),
                duration_seconds=_strict_int(value["duration_seconds"], "duration_seconds"),
                target_rps=_strict_number(value["target_rps"], "target_rps"),
                retries_per_actor=_strict_int(value["retries_per_actor"], "retries_per_actor"),
                trials=_strict_int(value["trials"], "trials"),
                drop_capacity=_strict_int(value["drop_capacity"], "drop_capacity"),
            )
        except KeyError as exc:
            raise ValueError(f"missing run field: {exc.args[0]}") from exc
        config.validate(limits)
        return config

    def validate(self, limits: LabLimits) -> None:
        if self.human_actors < 0 or self.bot_actors < 0:
            raise ValueError("actor counts must be non-negative")
        if not 1 <= self.identity_count <= limits.max_identities:
            raise ValueError(f"total identities must be between 1 and {limits.max_identities}")
        if not 1 <= self.duration_seconds <= limits.max_duration_seconds:
            raise ValueError(
                f"duration_seconds must be between 1 and {limits.max_duration_seconds}"
            )
        if not 0 < self.target_rps <= limits.max_rps:
            raise ValueError(f"target_rps must be greater than 0 and at most {limits.max_rps:g}")
        if not 0 <= self.retries_per_actor <= limits.max_retries_per_actor:
            raise ValueError(
                f"retries_per_actor must be between 0 and {limits.max_retries_per_actor}"
            )
        if not 1 <= self.trials <= limits.max_trials:
            raise ValueError(f"trials must be between 1 and {limits.max_trials}")
        if not 1 <= self.drop_capacity <= limits.max_drop_capacity:
            raise ValueError(f"drop_capacity must be between 1 and {limits.max_drop_capacity}")
        if self.scenario in {Scenario.EARLY_BOT, Scenario.POLICY_COMPARE}:
            if self.human_actors == 0 or self.bot_actors == 0:
                raise ValueError(
                    f"{self.scenario.value} requires at least one human and one bot actor"
                )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["scenario"] = self.scenario.value
        return result


@dataclass(slots=True)
class RunProgress:
    completed_steps: int = 0
    total_steps: int = 1
    message: str = "Queued"


@dataclass(slots=True)
class RunRecord:
    run_id: str
    status: RunStatus
    scenario: Scenario
    config: dict[str, Any]
    progress: RunProgress = field(default_factory=RunProgress)
    created_at: str = field(default_factory=lambda: now_iso())
    started_at: str | None = None
    ended_at: str | None = None
    error: dict[str, Any] | None = None
    report_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        value["scenario"] = self.scenario.value
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> RunRecord:
        return cls(
            run_id=value["run_id"],
            status=RunStatus(value["status"]),
            scenario=Scenario(value["scenario"]),
            config=value["config"],
            progress=RunProgress(**value["progress"]),
            created_at=value["created_at"],
            started_at=value.get("started_at"),
            ended_at=value.get("ended_at"),
            error=value.get("error"),
            report_path=value.get("report_path"),
        )


def now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _strict_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _strict_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{name} must be finite")
    return number

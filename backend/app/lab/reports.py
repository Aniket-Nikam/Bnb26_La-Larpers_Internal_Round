from __future__ import annotations

import math
from collections import Counter
from datetime import UTC, datetime
from typing import Any, Iterable


def performance_from_k6_summary(summary: dict[str, Any], *, target_rps: float) -> dict[str, Any]:
    metrics = summary.get("metrics", {})
    latency = metrics.get("fairdrop_successful_request_latency", {}).get("values", {})
    iterations = _metric_value(metrics, "iterations", "count")
    dropped = _metric_value(metrics, "dropped_iterations", "count") or 0
    delivered = int(iterations) if iterations is not None else None
    scheduled = delivered + int(dropped) if delivered is not None else None
    return {
        "workload": {
            "request_rate_target": target_rps,
            "scheduled_iterations": scheduled,
            "delivered_iterations": delivered,
            "dropped_iterations": int(dropped),
            "achieved_rps": _metric_value(metrics, "http_reqs", "rate"),
            "peak_open_connections": None,
            "peak_inflight_requests": None,
            "generator_cpu_peak": None,
            "generator_memory_peak": None,
        },
        "performance": {
            "successful_request_latency_ms": {
                "p50": latency.get("med"),
                "p95": latency.get("p(95)"),
                "p99": latency.get("p(99)"),
            },
            "endpoint_status_breakdown": None,
            "endpoint_status_breakdown_unavailable_reason": "k6 summary export does not retain tagged submetric breakdown unless configured per endpoint/status",
            "expected_429": _metric_value(metrics, "fairdrop_expected_429", "count") or 0,
            "expected_403": _metric_value(metrics, "fairdrop_expected_403", "count") or 0,
            "expected_409": _metric_value(metrics, "fairdrop_expected_409", "count") or 0,
            "unexpected_5xx": _metric_value(metrics, "fairdrop_unexpected_5xx", "count") or 0,
            "network_errors": _metric_value(metrics, "fairdrop_network_errors", "count") or 0,
        },
    }


def build_run_report(
    *,
    config: dict[str, Any],
    identities: Iterable[dict[str, Any]],
    performance: dict[str, Any],
    integrity: dict[str, Any],
    provenance: dict[str, Any],
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    """Aggregate a report using identity outcomes, never request counts.

    Identity records are harness/DB reconciliation data. Expected keys are
    identity_id, actor_id, cohort (human|bot), attempted, accepted,
    initial_offer, promotions, confirmed, expired and entry_latency_ms.
    """

    rows = _deduplicate_identities(identities)
    cohorts = {name: [row for row in rows if row.get("cohort") == name] for name in ("human", "bot")}
    admission: dict[str, Any] = {}
    allocation_cohorts: dict[str, Any] = {}

    for name, cohort_rows in cohorts.items():
        attempted = sum(bool(row.get("attempted")) for row in cohort_rows)
        accepted = sum(bool(row.get("accepted")) for row in cohort_rows)
        initial_offers = sum(bool(row.get("initial_offer")) for row in cohort_rows)
        promotions = sum(int(row.get("promotions", 0)) for row in cohort_rows)
        confirmed = sum(bool(row.get("confirmed")) for row in cohort_rows)
        expired = sum(bool(row.get("expired")) for row in cohort_rows)
        admission[name] = {
            "attempted_unique_identities": attempted,
            "accepted_unique_identities": accepted,
            "admission_rate": _rate(attempted, accepted),
        }
        allocation_cohorts[name] = {
            "eligible_identities": accepted,
            "initial_offers": initial_offers,
            "promotions": promotions,
            "confirmed": confirmed,
            "expired": expired,
            "win_rate": _rate(accepted, initial_offers),
            "actor_count": len({row.get("actor_id") for row in cohort_rows if row.get("actor_id")}),
            "credential_count": len(cohort_rows),
        }

    human_rate = allocation_cohorts["human"]["win_rate"]
    bot_rate = allocation_cohorts["bot"]["win_rate"]
    advantage, advantage_reason = _bot_advantage(human_rate, bot_rate)
    latency_statistics = _latency_statistics(rows)

    actor_credentials: dict[str, int] = Counter(
        str(row["actor_id"]) for row in rows if row.get("actor_id") is not None
    )
    report = {
        "provenance": {
            "source": "measured",
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            **provenance,
        },
        "config": config,
        "workload": performance.get("workload", {}),
        "admission": admission,
        "allocation": {
            "cohorts": allocation_cohorts,
            "actor_credentials": actor_credentials,
            "bot_advantage": advantage,
            "bot_advantage_undefined_reason": advantage_reason,
            "bot_initial_offer_share": _rate(
                allocation_cohorts["human"]["initial_offers"]
                + allocation_cohorts["bot"]["initial_offers"],
                allocation_cohorts["bot"]["initial_offers"],
            ),
            "bot_identity_share": _rate(
                allocation_cohorts["human"]["eligible_identities"]
                + allocation_cohorts["bot"]["eligible_identities"],
                allocation_cohorts["bot"]["eligible_identities"],
            ),
        },
        "integrity": integrity,
        "performance": performance.get("performance", {}),
        "statistics": {
            "trials": config.get("trials"),
            "sample_sizes": {name: data["eligible_identities"] for name, data in allocation_cohorts.items()},
            "interval_method": "Wilson score, 95%" if rows else None,
            "intervals": {
                name: _wilson_interval(data["initial_offers"], data["eligible_identities"])
                for name, data in allocation_cohorts.items()
            },
            **latency_statistics,
        },
        "limitations": list(limitations or []),
    }
    _assert_no_secret_fields(report)
    _assert_finite_json(report)
    return report


def _deduplicate_identities(identities: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for row in identities:
        identity_id = str(row.get("identity_id", ""))
        if not identity_id:
            raise ValueError("identity outcome is missing identity_id")
        if identity_id in unique:
            raise ValueError(f"duplicate identity outcome: {identity_id}")
        cohort = row.get("cohort")
        if cohort not in {"human", "bot"}:
            raise ValueError(f"identity {identity_id} has invalid cohort")
        unique[identity_id] = dict(row)
    return list(unique.values())


def _rate(denominator: int, numerator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def _bot_advantage(human_rate: float | None, bot_rate: float | None) -> tuple[float | None, str | None]:
    if human_rate is None:
        return None, "no accepted human identities"
    if bot_rate is None:
        return None, "no accepted bot identities"
    if human_rate == 0:
        if bot_rate > 0:
            return None, "human initial-offer rate is zero while bot rate is positive"
        return None, "both cohort initial-offer rates are zero"
    return bot_rate / human_rate, None


def _latency_statistics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    accepted = [
        row
        for row in rows
        if row.get("accepted") and isinstance(row.get("entry_latency_ms"), (int, float))
    ]
    if len(accepted) < 4:
        return {
            "latency_quartile_rates": None,
            "latency_jain_index": None,
            "latency_correlation": None,
            "latency_undefined_reason": "fewer than four accepted identities have measured latency",
        }
    accepted.sort(key=lambda row: float(row["entry_latency_ms"]))
    quartiles: list[list[dict[str, Any]]] = [[], [], [], []]
    for index, row in enumerate(accepted):
        quartiles[min(3, index * 4 // len(accepted))].append(row)
    if any(not group for group in quartiles):
        return {
            "latency_quartile_rates": None,
            "latency_jain_index": None,
            "latency_correlation": None,
            "latency_undefined_reason": "one or more latency quartiles are empty",
        }
    rates = [sum(bool(row.get("initial_offer")) for row in group) / len(group) for group in quartiles]
    squares = sum(rate * rate for rate in rates)
    jain = None if squares == 0 else (sum(rates) ** 2) / (4 * squares)
    latencies = [float(row["entry_latency_ms"]) for row in accepted]
    outcomes = [1.0 if row.get("initial_offer") else 0.0 for row in accepted]
    correlation, correlation_reason = _pearson(latencies, outcomes)
    return {
        "latency_quartile_rates": rates,
        "latency_jain_index": jain,
        "latency_correlation": correlation,
        "latency_undefined_reason": correlation_reason,
    }


def _pearson(xs: list[float], ys: list[float]) -> tuple[float | None, str | None]:
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    dx = [value - mean_x for value in xs]
    dy = [value - mean_y for value in ys]
    denominator = math.sqrt(sum(value * value for value in dx) * sum(value * value for value in dy))
    if denominator == 0:
        return None, "latency or initial-offer input is constant"
    return sum(left * right for left, right in zip(dx, dy, strict=True)) / denominator, None


def _wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> dict[str, float] | None:
    if total == 0:
        return None
    rate = successes / total
    denominator = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((rate * (1 - rate) + z * z / (4 * total)) / total) / denominator
    return {"lower": max(0.0, center - margin), "upper": min(1.0, center + margin)}


def _assert_finite_json(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("report contains a non-finite number")
    if isinstance(value, dict):
        for nested in value.values():
            _assert_finite_json(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_finite_json(nested)


def _metric_value(metrics: dict[str, Any], metric_name: str, value_name: str) -> float | None:
    value = metrics.get(metric_name, {}).get("values", {}).get(value_name)
    return value if isinstance(value, (int, float)) and math.isfinite(value) else None


def _assert_no_secret_fields(value: Any, path: str = "report") -> None:
    forbidden = {
        "access_code",
        "access_credential",
        "authorization",
        "cookie",
        "csrf",
        "csrf_token",
        "credential_digest",
        "password",
        "session_token",
    }
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).lower()
            if normalized in forbidden:
                raise ValueError(f"report contains forbidden secret field at {path}.{key}")
            _assert_no_secret_fields(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _assert_no_secret_fields(nested, f"{path}[{index}]")

"""Report regression checks against observed HTTP measurements and trial outcomes."""

from app.core.schemas import RunReport
from app.lab.integration import measured_report
from app.lab.reports import performance_from_k6_summary


def test_legacy_k6_export_uses_measured_counts_and_latency():
    summary = {
        "metrics": {
            "iterations": {"count": 7},
            "dropped_iterations": {"count": 2},
            "http_reqs": {"rate": 12.5},
            "fairdrop_successful_request_latency": {"med": 10, "p(95)": 25, "p(99)": 30},
        }
    }
    measured = performance_from_k6_summary(summary, target_rps=15)
    assert measured["workload"]["scheduled_iterations"] == 9
    assert measured["workload"]["delivered_iterations"] == 7
    assert measured["workload"]["achieved_rps"] == 12.5
    assert measured["performance"]["successful_request_latency_ms"] == {
        "p50": 10,
        "p95": 25,
        "p99": 30,
    }


def test_comparison_keeps_policy_outcomes_separate_and_intervals_at_trial_level():
    config = {
        "scenario": "policy_compare",
        "human_actors": 1,
        "bot_actors": 1,
        "target_rps": 6,
        "duration_seconds": 1,
        "retries_per_actor": 0,
        "trials": 2,
        "drop_capacity": 1,
    }
    outcomes = []
    for trial in range(2):
        policies = {}
        for mode in ("LOTTERY", "FCFS_DEMO"):
            rows = []
            for cohort in ("human", "bot"):
                won = cohort == ("human" if mode == "LOTTERY" else "bot")
                rows.append(
                    {
                        "identity_id": f"{cohort}-{trial}",
                        "actor_id": cohort,
                        "cohort": cohort,
                        "attempted": True,
                        "accepted": True,
                        "initial_offer": won,
                        "confirmed": False,
                        "expired": False,
                    }
                )
            policies[mode] = {
                "identities": rows,
                "integrity": {
                    "capacity": 1,
                    "maximum_observed_owned_slots": 1,
                    "duplicate_active_owners": 0,
                    "oversell_count": 0,
                    "audit_pass": True,
                },
            }
        outcomes.append(
            {
                "policies": policies,
                "measurements": [
                    {
                        "endpoint": "entry",
                        "status": 201,
                        "latency_ms": 10 + trial,
                        "public_id": "x",
                        "drop_id": "d",
                    }
                ],
            }
        )
    summaries = [{"metrics": {"iterations": {"count": 2}, "http_reqs": {"rate": 6}}}] * 2
    report = RunReport.model_validate(measured_report(config, outcomes, summaries, "test-commit"))
    assert report.allocation.human.initial_offers == 2
    assert report.allocation.bot.initial_offers == 0
    assert report.policy_comparison["FCFS_DEMO"].allocation.bot.initial_offers == 2
    assert report.policy_comparison["FCFS_DEMO"].allocation.bot_advantage is None
    assert report.statistics.trials == 2
    assert report.statistics.intervals
    assert report.workload.provisioned_identity_count == 4
    assert report.performance.endpoint_status_breakdown[0].count == 2
    assert report.provenance.app_commit == "test-commit"

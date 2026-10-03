import json
import unittest

from backend.app.lab.reports import build_run_report, performance_from_k6_summary


class ReportTests(unittest.TestCase):
    def report(self, identities):
        return build_run_report(
            config={"trials": 1},
            identities=identities,
            performance={"workload": {}, "performance": {}},
            integrity={"capacity": 2, "audit_pass": True},
            provenance={"app_commit": "test"},
        )

    def test_bot_advantage_uses_accepted_identities_not_requests(self) -> None:
        rows = [
            {"identity_id": "h1", "actor_id": "h", "cohort": "human", "attempted": True, "accepted": True, "initial_offer": True, "entry_latency_ms": 10},
            {"identity_id": "h2", "actor_id": "h2", "cohort": "human", "attempted": True, "accepted": True, "initial_offer": False, "entry_latency_ms": 20},
            {"identity_id": "b1", "actor_id": "bot", "cohort": "bot", "attempted": True, "accepted": True, "initial_offer": True, "request_count": 1000, "entry_latency_ms": 30},
            {"identity_id": "b2", "actor_id": "bot", "cohort": "bot", "attempted": True, "accepted": True, "initial_offer": False, "request_count": 1, "entry_latency_ms": 40},
        ]
        report = self.report(rows)
        self.assertEqual(report["allocation"]["bot_advantage"], 1.0)
        self.assertEqual(report["allocation"]["cohorts"]["bot"]["actor_count"], 1)
        json.dumps(report, allow_nan=False)

    def test_undefined_ratio_is_null_with_reason(self) -> None:
        rows = [
            {"identity_id": "h1", "actor_id": "h", "cohort": "human", "attempted": True, "accepted": True, "initial_offer": False},
            {"identity_id": "b1", "actor_id": "b", "cohort": "bot", "attempted": True, "accepted": True, "initial_offer": True},
        ]
        allocation = self.report(rows)["allocation"]
        self.assertIsNone(allocation["bot_advantage"])
        self.assertIn("human initial-offer rate is zero", allocation["bot_advantage_undefined_reason"])

    def test_duplicate_identity_outcomes_are_rejected(self) -> None:
        row = {"identity_id": "same", "actor_id": "a", "cohort": "human"}
        with self.assertRaisesRegex(ValueError, "duplicate identity"):
            self.report([row, row])

    def test_k6_summary_keeps_iterations_distinct_from_requests(self) -> None:
        summary = {
            "metrics": {
                "iterations": {"values": {"count": 90}},
                "dropped_iterations": {"values": {"count": 10}},
                "http_reqs": {"values": {"count": 270, "rate": 135}},
                "fairdrop_successful_request_latency": {
                    "values": {"med": 12, "p(95)": 40, "p(99)": 70}
                },
            }
        }
        parsed = performance_from_k6_summary(summary, target_rps=50)
        self.assertEqual(parsed["workload"]["scheduled_iterations"], 100)
        self.assertEqual(parsed["workload"]["delivered_iterations"], 90)
        self.assertEqual(parsed["workload"]["achieved_rps"], 135)
        self.assertEqual(parsed["performance"]["successful_request_latency_ms"]["p95"], 40)

    def test_report_rejects_secret_shaped_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "forbidden secret field"):
            build_run_report(
                config={"trials": 1},
                identities=[],
                performance={"workload": {}, "performance": {}},
                integrity={},
                provenance={"access_code": "must-not-leak"},
            )


if __name__ == "__main__":
    unittest.main()

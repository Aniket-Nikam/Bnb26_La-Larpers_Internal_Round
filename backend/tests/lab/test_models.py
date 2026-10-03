import unittest

from backend.app.lab.models import LabLimits, RunConfig, Scenario


class RunConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.valid = {
            "scenario": "normal",
            "human_actors": 90,
            "bot_actors": 10,
            "duration_seconds": 30,
            "target_rps": 100,
            "retries_per_actor": 2,
            "trials": 3,
            "drop_capacity": 40,
        }

    def test_accepts_allowlisted_bounded_configuration(self) -> None:
        config = RunConfig.from_dict(self.valid, LabLimits())
        self.assertEqual(config.scenario, Scenario.NORMAL)
        self.assertEqual(config.identity_count, 100)

    def test_rejects_arbitrary_target_or_command_fields(self) -> None:
        for field in ("target_url", "command", "script", "seed"):
            with self.subTest(field=field):
                payload = {**self.valid, field: "attacker-controlled"}
                with self.assertRaisesRegex(ValueError, "unsupported run fields"):
                    RunConfig.from_dict(payload, LabLimits())

    def test_rejects_cap_overrides_and_boolean_numbers(self) -> None:
        with self.assertRaisesRegex(ValueError, "at most 2000"):
            RunConfig.from_dict({**self.valid, "target_rps": 2001}, LabLimits())
        with self.assertRaisesRegex(ValueError, "must be an integer"):
            RunConfig.from_dict({**self.valid, "human_actors": True}, LabLimits())

    def test_comparison_requires_both_cohorts(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires at least one human and one bot"):
            RunConfig.from_dict(
                {**self.valid, "scenario": "policy_compare", "bot_actors": 0}, LabLimits()
            )


if __name__ == "__main__":
    unittest.main()

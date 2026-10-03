import json
import shutil
import unittest
import uuid
from pathlib import Path

from app.lab.models import LabLimits, RunConfig
from app.lab.runner import LabRunner
from app.lab.store import AtomicRunStore


class RunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("backend/tests/lab/.tmp") / uuid.uuid4().hex
        self.root.mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_argv_uses_only_allowlisted_script_and_separate_arguments(self) -> None:
        scripts = self.root / "scripts"
        fixtures = self.root / "fixtures"
        scripts.mkdir()
        fixtures.mkdir()
        (scripts / "normal.js").write_text("export default function() {}\n", encoding="utf-8")
        credential_file = fixtures / "actors.json"
        credential_file.write_text(json.dumps({"drop_id": "x", "actors": []}), encoding="utf-8")
        runner = LabRunner(
            store=AtomicRunStore(self.root / "runs"),
            script_root=scripts,
            private_fixture_root=fixtures,
            target_origin="http://gateway:8080",
        )
        config = RunConfig.from_dict(
            {
                "scenario": "normal",
                "human_actors": 1,
                "bot_actors": 0,
                "duration_seconds": 1,
                "target_rps": 1,
                "retries_per_actor": 0,
                "trials": 1,
                "drop_capacity": 1,
            },
            LabLimits(),
        )
        argv = runner.build_argv(config, self.root / "summary file.json")
        self.assertEqual(argv[0:3], ["k6", "run", "--quiet"])
        self.assertEqual(argv[-1], str((scripts / "normal.js").resolve()))
        self.assertNotIn("shell", " ".join(argv).lower())

    def test_target_is_an_origin_not_an_arbitrary_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not contain a path"):
            LabRunner(
                store=AtomicRunStore(self.root / "runs"),
                script_root=self.root,
                private_fixture_root=self.root,
                target_origin="https://example.test/attacker/path",
            )


if __name__ == "__main__":
    unittest.main()

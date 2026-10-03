import shutil
import unittest
import uuid
from pathlib import Path

from backend.app.lab.models import RunRecord, RunStatus, Scenario
from backend.app.lab.store import AtomicRunStore


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path("backend/tests/lab/.tmp") / uuid.uuid4().hex
        self.directory.mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.directory, ignore_errors=True)

    def test_persists_and_lists_run_state(self) -> None:
        store = AtomicRunStore(self.directory)
        record = RunRecord("11111111-1111-4111-8111-111111111111", RunStatus.QUEUED, Scenario.NORMAL, {})
        store.create(record)
        record.status = RunStatus.RUNNING
        store.save(record)
        self.assertEqual(store.get(record.run_id).status, RunStatus.RUNNING)
        self.assertEqual(store.active().run_id, record.run_id)

    def test_rejects_path_traversal_run_id(self) -> None:
        store = AtomicRunStore(self.directory)
        with self.assertRaises(ValueError):
            store.get("../../escape")

    def test_active_claim_is_atomic_and_released_explicitly(self) -> None:
        store = AtomicRunStore(self.directory)
        first = "11111111-1111-4111-8111-111111111111"
        second = "22222222-2222-4222-8222-222222222222"
        store.reserve_active(first)
        record = RunRecord(first, RunStatus.QUEUED, Scenario.NORMAL, {})
        store.create(record)
        with self.assertRaisesRegex(RuntimeError, "already active"):
            store.reserve_active(second)
        record.status = RunStatus.COMPLETED
        store.save(record)
        store.release_active(first)
        store.reserve_active(second)
        store.release_active(second)


if __name__ == "__main__":
    unittest.main()

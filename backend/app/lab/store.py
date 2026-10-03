from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path

from .models import RunRecord, RunStatus, TERMINAL_STATUSES


class AtomicRunStore:
    """Small durable store used by the isolated runner.

    P1's shared LabRun row remains the API authority once it exists.  This store
    keeps subprocess state and partial artifacts crash-readable without creating
    a competing allocation or inventory authority.
    """

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def create(self, record: RunRecord) -> None:
        with self._lock:
            path = self._status_path(record.run_id)
            if path.exists():
                raise ValueError("run already exists")
            path.parent.mkdir(parents=True, exist_ok=False)
            self._write(path, record.to_dict())

    def save(self, record: RunRecord) -> None:
        with self._lock:
            path = self._status_path(record.run_id)
            if not path.parent.exists():
                raise KeyError(record.run_id)
            self._write(path, record.to_dict())

    def get(self, run_id: str) -> RunRecord:
        path = self._status_path(run_id)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise KeyError(run_id) from exc
        return RunRecord.from_dict(value)

    def list(self) -> list[RunRecord]:
        records = []
        for path in self.root.glob("*/status.json"):
            try:
                records.append(RunRecord.from_dict(json.loads(path.read_text(encoding="utf-8"))))
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                continue
        return sorted(records, key=lambda item: item.created_at, reverse=True)

    def active(self) -> RunRecord | None:
        marker = self.root / ".active-run"
        try:
            run_id = marker.read_text(encoding="ascii").strip()
            record = self.get(run_id)
            if record.status not in TERMINAL_STATUSES:
                return record
        except (OSError, KeyError, ValueError):
            pass
        return next((record for record in self.list() if record.status not in TERMINAL_STATUSES), None)

    def reserve_active(self, run_id: str) -> None:
        """Atomically claim the single runner slot across API processes."""
        self._status_path(run_id)  # validate without requiring the run to exist yet
        marker = self.root / ".active-run"
        while True:
            try:
                descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                active = self.active()
                if active is not None:
                    raise RuntimeError(f"lab run {active.run_id} is already active")
                try:
                    marker.unlink()
                except FileNotFoundError:
                    pass
                continue
            with os.fdopen(descriptor, "w", encoding="ascii") as handle:
                handle.write(run_id)
                handle.flush()
                os.fsync(handle.fileno())
            return

    def release_active(self, run_id: str) -> None:
        marker = self.root / ".active-run"
        try:
            if marker.read_text(encoding="ascii").strip() == run_id:
                marker.unlink()
        except FileNotFoundError:
            return

    def run_dir(self, run_id: str) -> Path:
        return self._status_path(run_id).parent

    def _status_path(self, run_id: str) -> Path:
        if not run_id or any(char not in "0123456789abcdef-" for char in run_id.lower()):
            raise ValueError("invalid run id")
        path = (self.root / run_id / "status.json").resolve()
        if self.root not in path.parents:
            raise ValueError("invalid run path")
        return path

    @staticmethod
    def _write(path: Path, value: dict) -> None:
        descriptor, temporary_name = tempfile.mkstemp(prefix=".status-", suffix=".json", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

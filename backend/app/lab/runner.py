from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

from .models import (
    TERMINAL_STATUSES,
    LabLimits,
    RunConfig,
    RunProgress,
    RunRecord,
    RunStatus,
    now_iso,
)
from .reports import performance_from_k6_summary
from .store import AtomicRunStore

SCRIPT_BY_SCENARIO = {
    "normal": "normal.js",
    "early_bot": "early_bot.js",
    "retry_flood": "retry_flood.js",
    "credential_farm": "credential_farm.js",
    "shared_ip": "shared_ip.js",
    "reconnect": "reconnect.js",
    "worker_restart": "worker_restart.js",
    "expiry_race": "expiry_race.js",
    "redis_failure": "redis_failure.js",
    "policy_compare": "policy_compare.js",
}


class LabRunner:
    def __init__(
        self,
        *,
        store: AtomicRunStore,
        script_root: Path,
        private_fixture_root: Path,
        target_origin: str,
        limits: LabLimits | None = None,
        k6_executable: str = "k6",
    ):
        parsed = urlparse(target_origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username
            or parsed.password
        ):
            raise ValueError("LAB_TARGET_ORIGIN must be a fixed HTTP(S) origin without credentials")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError("LAB_TARGET_ORIGIN must not contain a path, query or fragment")
        self.store = store
        self.script_root = script_root.resolve()
        self.private_fixture_root = private_fixture_root.resolve()
        self.target_origin = target_origin.rstrip("/")
        self.limits = limits or LabLimits()
        self.k6_executable = k6_executable
        self._lock = threading.RLock()
        self._processes: dict[str, subprocess.Popen[str]] = {}

    def submit(
        self, payload: dict, *, credential_fixture: Path, app_commit: str, run_id: str | None = None
    ) -> RunRecord:
        config = RunConfig.from_dict(payload, self.limits)
        fixture = self._validated_fixture(credential_fixture)
        with self._lock:
            run_id = run_id or str(uuid.uuid4())
            self.store.reserve_active(run_id)
            record = RunRecord(
                run_id=run_id,
                status=RunStatus.QUEUED,
                scenario=config.scenario,
                config=config.to_dict(),
                progress=RunProgress(total_steps=config.trials, message="Queued"),
            )
            try:
                self.store.create(record)
            except Exception:
                self.store.release_active(run_id)
                raise
            thread = threading.Thread(
                target=self._execute,
                args=(run_id, fixture, app_commit),
                name=f"fairdrop-lab-{run_id}",
                daemon=True,
            )
            thread.start()
            return record

    def stop(self, run_id: str) -> RunRecord:
        with self._lock:
            record = self.store.get(run_id)
            if record.status in TERMINAL_STATUSES:
                return record
            record.status = RunStatus.STOPPING
            record.progress.message = "Cancellation requested"
            self.store.save(record)
            process = self._processes.get(run_id)
            if process is not None and process.poll() is None:
                process.terminate()
            return record

    def build_argv(self, config: RunConfig, summary_path: Path) -> list[str]:
        script_name = SCRIPT_BY_SCENARIO[config.scenario.value]
        script_path = (self.script_root / script_name).resolve()
        if self.script_root not in script_path.parents or not script_path.is_file():
            raise FileNotFoundError(f"allowlisted scenario script is missing: {script_name}")
        return [
            self.k6_executable,
            "run",
            "--quiet",
            "--log-format",
            "raw",
            "--summary-export",
            str(summary_path),
            str(script_path),
        ]

    def _execute(self, run_id: str, fixture: Path, app_commit: str) -> None:
        record = self.store.get(run_id)
        config = RunConfig.from_dict(record.config, self.limits)
        run_dir = self.store.run_dir(run_id)
        env = self._subprocess_env(config, fixture, run_id)
        timeout_seconds = min(config.duration_seconds + 60, 360)
        try:
            record.status = RunStatus.RUNNING
            record.started_at = now_iso()
            record.progress.message = "Running measured HTTP workload"
            self.store.save(record)
            summary_paths: list[Path] = []
            for trial in range(1, config.trials + 1):
                record = self.store.get(run_id)
                if record.status == RunStatus.STOPPING:
                    break
                record.progress.message = (
                    f"Running measured HTTP workload trial {trial}/{config.trials}"
                )
                self.store.save(record)
                summary_path = run_dir / f"k6-summary-{trial}.json"
                stdout_path = run_dir / f"k6-output-{trial}.log"
                trial_fixture = self.prepare_trial(record, trial, fixture)
                trial_env = {
                    **env,
                    "LAB_TRIAL_INDEX": str(trial),
                    "LAB_CREDENTIALS_FILE": str(trial_fixture),
                }
                argv = self.build_argv(config, summary_path)
                with stdout_path.open("w", encoding="utf-8") as output:
                    process = subprocess.Popen(
                        [sys.executable, str(Path(__file__).with_name("process.py")), *argv],
                        cwd=self.script_root,
                        env=trial_env,
                        stdin=subprocess.DEVNULL,
                        stdout=output,
                        stderr=subprocess.STDOUT,
                        shell=False,
                        text=True,
                    )
                    with self._lock:
                        self._processes[run_id] = process
                    deadline = time.monotonic() + timeout_seconds
                    while process.poll() is None:
                        latest = self.store.get(run_id)
                        if latest.status == RunStatus.STOPPING:
                            process.terminate()
                            break
                        if time.monotonic() >= deadline:
                            process.terminate()
                            try:
                                process.wait(timeout=10)
                            except subprocess.TimeoutExpired:
                                process.kill()
                            raise TimeoutError("lab trial exceeded its configured execution limit")
                        time.sleep(0.2)
                    return_code = process.wait(timeout=10)
                if return_code != 0:
                    latest = self.store.get(run_id)
                    if latest.status == RunStatus.STOPPING:
                        break
                    raise RuntimeError(f"load generator exited with status {return_code}")
                self.complete_trial(record, trial, trial_fixture, stdout_path)
                summary_paths.append(summary_path)
                record = self.store.get(run_id)
                record.progress.completed_steps = trial
                self.store.save(record)

            record = self.store.get(run_id)
            if record.status == RunStatus.STOPPING:
                record.status = RunStatus.STOPPED
                record.progress.message = "Stopped; partial artifacts retained"
                if summary_paths:
                    record.report_path = self._write_partial_report(
                        run_dir, record, summary_paths, app_commit
                    ).name
            else:
                report_path = self._write_partial_report(run_dir, record, summary_paths, app_commit)
                record.status = RunStatus.COMPLETED
                record.progress.message = "HTTP workload completed"
                record.report_path = report_path.name
            record.ended_at = now_iso()
            self.store.save(record)
        except (
            Exception
        ) as exc:  # safe boundary; raw subprocess output stays in restricted artifacts
            record = self.store.get(run_id)
            record.status = (
                RunStatus.STOPPED if record.status == RunStatus.STOPPING else RunStatus.FAILED
            )
            record.ended_at = now_iso()
            record.progress.message = "Run failed; partial artifacts retained"
            record.error = {
                "code": "LAB_RUN_FAILED",
                "message": _safe_error(exc),
                "retryable": isinstance(exc, (TimeoutError, FileNotFoundError)),
            }
            if "summary_paths" in locals() and summary_paths:
                try:
                    record.report_path = self._write_partial_report(
                        run_dir, record, summary_paths, app_commit
                    ).name
                except Exception:
                    pass  # Raw trial artifacts remain available even if reconciliation failed.
            self.store.save(record)
        finally:
            with self._lock:
                self._processes.pop(run_id, None)
            self.store.release_active(run_id)

    def prepare_trial(self, record, trial, fixture):
        return fixture

    def complete_trial(self, record, trial, fixture, stdout_path):
        pass

    def _subprocess_env(self, config: RunConfig, fixture: Path, run_id: str) -> dict[str, str]:
        keep = {
            name: os.environ[name]
            for name in (
                "PATH",
                "SystemRoot",
                "SystemDrive",
                "WINDIR",
                "ProgramData",
                "LOCALAPPDATA",
                "APPDATA",
                "USERPROFILE",
                "TEMP",
                "TMP",
            )
            if name in os.environ
        }
        keep.update(
            {
                "LAB_TARGET_ORIGIN": self.target_origin,
                "LAB_CREDENTIALS_FILE": str(fixture),
                "LAB_RUN_ID": run_id,
                "LAB_SCENARIO": config.scenario.value,
                "LAB_HUMAN_ACTORS": str(config.human_actors),
                "LAB_BOT_ACTORS": str(config.bot_actors),
                "LAB_DURATION_SECONDS": str(config.duration_seconds),
                "LAB_TARGET_RPS": str(config.target_rps),
                "LAB_RETRIES_PER_ACTOR": str(config.retries_per_actor),
                "LAB_TRIALS": str(config.trials),
                "LAB_DROP_CAPACITY": str(config.drop_capacity),
            }
        )
        return keep

    def _validated_fixture(self, value: Path) -> Path:
        fixture = value.resolve()
        if self.private_fixture_root not in fixture.parents or not fixture.is_file():
            raise ValueError(
                "credential fixture must be an existing file under the private fixture root"
            )
        return fixture

    @staticmethod
    def _write_partial_report(
        run_dir: Path, record: RunRecord, summary_paths: list[Path], app_commit: str
    ) -> Path:
        summaries = [
            json.loads(path.read_text(encoding="utf-8")) for path in summary_paths if path.exists()
        ]
        per_trial = [
            performance_from_k6_summary(summary, target_rps=float(record.config["target_rps"]))
            for summary in summaries
        ]
        single = per_trial[0] if len(per_trial) == 1 else {"workload": {}, "performance": {}}
        limitations = [
            "Partial report: authoritative database reconciliation is unavailable until P1 supplies the shared model/query interface.",
            "No allocation, admission, or integrity conclusion is made from HTTP timing data alone.",
        ]
        if len(per_trial) > 1:
            limitations.append(
                "Trial percentiles are retained per trial; aggregate percentiles are null because percentile summaries cannot be merged without raw samples."
            )
        report = {
            "provenance": {
                "source": "measured",
                "timestamp": now_iso(),
                "app_commit": app_commit,
                "contract_version": None,
                "algorithm_version": None,
            },
            "config": record.config,
            "workload": single["workload"],
            "admission": None,
            "allocation": None,
            "integrity": None,
            "performance": single["performance"],
            "statistics": {
                "trials_requested": record.config["trials"],
                "trials_completed": len(summaries),
                "per_trial_http_measurements": per_trial,
                "sample_sizes": None,
                "interval_method": None,
                "intervals": None,
            },
            "limitations": limitations,
        }
        report_path = run_dir / "report.json"
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
        )
        return report_path


def _safe_error(exc: Exception) -> str:
    if isinstance(exc, FileNotFoundError):
        return "Required allowlisted load-generator executable or scenario file was not found."
    if isinstance(exc, TimeoutError):
        return "The run exceeded its configured time limit and was stopped."
    if isinstance(exc, RuntimeError) and "exited with status" in str(exc):
        return str(exc)
    return "The isolated lab runner failed. Inspect restricted runner artifacts using the run ID."

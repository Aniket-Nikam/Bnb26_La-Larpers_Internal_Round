"""Dedicated demo job worker: python -m app.lab.worker. Allocation has its own worker."""

import json
import logging
import signal
from datetime import datetime
from pathlib import Path
from threading import Event
from uuid import UUID, uuid4

from sqlalchemy import select, text

from app.core.clock import db_now
from app.core.config import get_settings
from app.core.schemas import RunReport
from app.lab.integration import IntegratedRunner, write_private
from app.lab.models import TERMINAL_STATUSES, RunStatus
from app.lab.router import limits
from app.lab.store import AtomicRunStore
from app.persistence.database import get_engine, session_factory
from app.persistence.models import LabRun

logger = logging.getLogger("fairdrop.lab.worker")


def sync_job(runner, run_id):
    maker = session_factory()
    with maker.begin() as db:
        job = db.get(LabRun, UUID(run_id), with_for_update=True)
        if job.status == "STOPPING":
            runner.stop(run_id)
        record = runner.store.get(run_id)
        # Never overwrite an API cancellation with a stale RUNNING projection.
        job.status = record.status.value
        job.progress = {
            "completed_steps": record.progress.completed_steps,
            "total_steps": record.progress.total_steps,
            "message": record.progress.message,
        }
        job.started_at = datetime.fromisoformat(record.started_at) if record.started_at else None
        job.ended_at = datetime.fromisoformat(record.ended_at) if record.ended_at else None
        if record.error:
            job.error = {**record.error, "request_id": str(uuid4()), "fields": None}
        if record.report_path:
            path = runner.store.run_dir(run_id) / record.report_path
            job.report = RunReport.model_validate(json.loads(path.read_text())).model_dump(
                mode="json"
            )
            job.report_path = str(path)
        return record.status in TERMINAL_STATUSES


def fail_interrupted(runner):
    # A generator process cannot be resumed transparently. Preserve artifacts and
    # mark interrupted experiments failed so they never masquerade as complete data.
    with session_factory().begin() as db:
        for job in db.scalars(select(LabRun).where(LabRun.status.in_(["RUNNING", "STOPPING"]))):
            job.status = "FAILED"
            job.ended_at = db_now(db)
            job.error = {
                "code": "LAB_RUN_INTERRUPTED",
                "message": "Runner interrupted; partial artifacts retained. Start a new experiment.",
                "request_id": str(uuid4()),
                "retryable": True,
                "fields": None,
            }
            try:
                record = runner.store.get(str(job.id))
                record.status = RunStatus.FAILED
                record.error = job.error
                runner.store.save(record)
                runner.store.release_active(str(job.id))
            except KeyError:
                pass


def main():
    cfg = get_settings()
    if cfg.app_profile != "demo" or not cfg.lab_enabled:
        raise RuntimeError("The lab worker requires APP_PROFILE=demo and LAB_ENABLED=true")
    cfg.seed_key()
    runner = IntegratedRunner(
        store=AtomicRunStore(Path(cfg.lab_artifact_root)),
        script_root=Path(cfg.lab_script_root),
        private_fixture_root=Path(cfg.lab_private_fixture_root),
        target_origin=cfg.lab_target_origin,
        limits=limits(),
        k6_executable=cfg.lab_k6_executable,
    )
    stop = Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    logging.basicConfig(level=logging.INFO)
    # A connection-scoped lock fences runner ownership across process replicas.
    with get_engine().connect().execution_options(isolation_level="AUTOCOMMIT") as lease:
        if not lease.scalar(text("SELECT pg_try_advisory_lock(73120492)")):
            raise RuntimeError("Another lab worker owns the runner lease")
        fail_interrupted(runner)
        current = None
        while not stop.is_set():
            try:
                # Check the lease connection before touching jobs. Connection loss
                # terminates the worker; a replacement safely fails interrupted work.
                lease.execute(text("SELECT 1"))
                if current:
                    if sync_job(runner, current):
                        current = None
                else:
                    with session_factory().begin() as db:
                        job = db.scalar(
                            select(LabRun)
                            .where(LabRun.status == "QUEUED")
                            .order_by(LabRun.created_at)
                            .with_for_update(skip_locked=True)
                            .limit(1)
                        )
                        if job:
                            current = str(job.id)
                            job.status, job.started_at = "RUNNING", db_now(db)
                            payload = job.config
                    if current:
                        try:
                            placeholder = Path(cfg.lab_private_fixture_root) / current / "job.json"
                            write_private(placeholder, {})
                            runner.submit(
                                payload,
                                credential_fixture=placeholder,
                                app_commit=cfg.app_commit,
                                run_id=current,
                            )
                        except Exception:
                            with session_factory().begin() as db:
                                job = db.get(LabRun, UUID(current), with_for_update=True)
                                job.status, job.ended_at = "FAILED", db_now(db)
                                job.error = {
                                    "code": "LAB_RUN_FAILED",
                                    "message": "Runner preparation failed; inspect restricted artifacts.",
                                    "request_id": str(uuid4()),
                                    "retryable": True,
                                    "fields": None,
                                }
                            current = None
                stop.wait(0.25)
            except Exception:
                logger.error(
                    "Lab worker cannot safely maintain its lease or job projection; interrupted artifacts are retained"
                )
                stop.set()
        if current:
            runner.stop(current)
            # Bounded graceful drain; the job remains recoverable if killed.
            for _ in range(80):
                if sync_job(runner, current):
                    break
                Event().wait(0.1)


if __name__ == "__main__":
    main()

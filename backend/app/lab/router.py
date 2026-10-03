"""Owner scoped durable job API. The isolated worker executes measured workloads."""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy import select, text

from app.core import schemas as s
from app.core.clock import db_now
from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.idempotency import claim, complete
from app.core.pagination import paginate
from app.lab.models import LabLimits, RunConfig
from app.persistence.database import get_db
from app.persistence.models import LabRun
from app.security.authorization import require_organizer
from app.security.limits import enforce_limit

router = APIRouter(prefix="/admin/lab", tags=["lab"])
LAB_IMPLEMENTED = True
DB = Annotated[object, Depends(get_db)]
KEY = Annotated[UUID, Header(alias="Idempotency-Key")]


def lab_principal(request: Request, principal: s.Principal = Depends(require_organizer)):
    cfg = get_settings()
    if cfg.app_profile != "demo" or not cfg.lab_enabled:
        raise DomainError("NOT_FOUND", "Lab is unavailable in this deployment.", 404)
    enforce_limit(request, principal, "organizer")
    return principal


PRINCIPAL = Annotated[s.Principal, Depends(lab_principal)]


def limits():
    cfg = get_settings()
    return LabLimits(
        max_identities=min(50000, cfg.lab_max_identities),
        max_rps=min(2000, cfg.lab_max_rps),
        max_duration_seconds=min(300, cfg.lab_max_duration_seconds),
        max_trials=min(20, cfg.lab_max_trials),
        max_retries_per_actor=min(20, cfg.lab_max_retries_per_actor),
    )


def owned(db, run_id, principal, lock=False):
    statement = select(LabRun).where(LabRun.id == run_id)
    if principal.role != "admin":
        statement = statement.where(LabRun.owner_id == principal.id)
    if lock:
        statement = statement.with_for_update()
    run = db.scalar(statement)
    if run is None:
        raise DomainError("NOT_FOUND", "Run not found.", 404)
    return run


def summary(db, run):
    return s.RunSummary(
        run_id=run.id,
        status=run.status,
        scenario=run.scenario,
        started_at=run.started_at,
        ended_at=run.ended_at,
        server_time=db_now(db),
    )


@router.post("/runs", response_model=s.RunAccepted, status_code=202)
def start(body: s.RunRequest, request: Request, db: DB, principal: PRINCIPAL, key: KEY):
    payload = body.model_dump(mode="json")
    try:
        RunConfig.from_dict(payload, limits())
    except ValueError:
        raise DomainError(
            "VALIDATION_ERROR", "Run exceeds this deployment's configured limits.", 422
        ) from None
    planned = body.target_rps * body.duration_seconds * body.trials * (3 + body.retries_per_actor)
    if planned > 250000:
        raise DomainError(
            "VALIDATION_ERROR", "Reduce the run to at most 250000 planned HTTP requests.", 422
        )
    if body.scenario in {"shared_ip", "worker_restart", "redis_failure"}:
        raise DomainError(
            "INVALID_STATE", "This scenario requires the documented host-side controller.", 409
        )
    op = claim(db, principal.id, request.method, request.url.path, key, payload)
    if op.status != "COMPLETED":
        # Serialize job creation across replicas; the partial unique index is a second guard.
        db.execute(text("SELECT pg_advisory_xact_lock(73120491)"))
        active = db.scalar(
            select(LabRun.id).where(LabRun.status.in_(["QUEUED", "RUNNING", "STOPPING"]))
        )
        if active:
            raise DomainError("INVALID_STATE", "A lab run is already active.", 409)
        run = LabRun(
            id=uuid4(),
            owner_id=principal.id,
            scenario=body.scenario,
            config=payload,
            status="QUEUED",
            progress={
                "completed_steps": 0,
                "total_steps": body.trials,
                "message": "Queued for the isolated runner",
            },
        )
        db.add(run)
        complete(op, "lab_run", run.id)
    db.commit()
    return s.RunAccepted(run_id=op.result_id, status="QUEUED", server_time=db_now(db))


@router.get("/runs", response_model=s.Page[s.RunSummary])
def runs(
    db: DB, principal: PRINCIPAL, cursor: str | None = None, limit: int = Query(50, ge=1, le=100)
):
    statement = select(LabRun)
    if principal.role != "admin":
        statement = statement.where(LabRun.owner_id == principal.id)
    rows, next_cursor = paginate(db, statement, LabRun, cursor, limit)
    return s.Page(items=[summary(db, row) for row in rows], next_cursor=next_cursor)


@router.get("/runs/{run_id}", response_model=s.RunDetail)
def detail(run_id: UUID, db: DB, principal: PRINCIPAL):
    row = owned(db, run_id, principal)
    return s.RunDetail(
        **summary(db, row).model_dump(),
        config=row.config,
        progress=row.progress,
        error=row.error,
        report=row.report,
    )


@router.post("/runs/{run_id}/stop", response_model=s.RunStopped)
def stop(
    run_id: UUID, body: s.EmptyInput, request: Request, db: DB, principal: PRINCIPAL, key: KEY
):
    row = owned(db, run_id, principal)
    op = claim(db, principal.id, request.method, request.url.path, key, {})
    if op.status != "COMPLETED":
        row = owned(db, run_id, principal, lock=True)
        if row.status == "QUEUED":
            row.status, row.ended_at = "STOPPED", db_now(db)
            row.progress = {**row.progress, "message": "Stopped before execution"}
        elif row.status == "RUNNING":
            row.status = "STOPPING"
        complete(op, "lab_stop", row.id)
    db.commit()
    db.refresh(row)
    return s.RunStopped(run_id=row.id, status=row.status, server_time=db_now(db))


@router.get("/runs/{run_id}/report", response_model=s.RunReport | s.ReportPending)
def report(run_id: UUID, db: DB, principal: PRINCIPAL):
    row = owned(db, run_id, principal)
    return row.report or s.ReportPending(run_id=run_id, server_time=db_now(db))


@router.get("/runs/{run_id}/export", response_model=s.RunReport)
def export(run_id: UUID, db: DB, principal: PRINCIPAL):
    row = owned(db, run_id, principal)
    if row.report is None:
        raise DomainError("INVALID_STATE", "No measured report is available yet.", 409)
    report = s.RunReport.model_validate(row.report)
    return Response(
        report.model_dump_json(),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="report.json"'},
    )

"""P4 bootstrap skeleton; P4 replaces this router, consuming shared DTOs/LabRun."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.errors import DomainError
from app.core.schemas import (
    EmptyInput,
    Page,
    ReportPending,
    RunAccepted,
    RunDetail,
    RunReport,
    RunRequest,
    RunStopped,
    RunSummary,
)
from app.security.authorization import require_organizer

router = APIRouter(prefix="/admin/lab", tags=["lab"], dependencies=[Depends(require_organizer)])
LAB_IMPLEMENTED = False


def unavailable():
    raise DomainError("NOT_IMPLEMENTED", "Lab endpoint awaits Member 4.", 501)


@router.post("/runs", response_model=RunAccepted, status_code=202)
def start(body: RunRequest):
    unavailable()


@router.get("/runs", response_model=Page[RunSummary])
def runs(cursor: str | None = None, limit: int = Query(50, ge=1, le=100)):
    unavailable()


@router.get("/runs/{run_id}", response_model=RunDetail)
def run(run_id: UUID):
    unavailable()


@router.post("/runs/{run_id}/stop", response_model=RunStopped)
def stop(run_id: UUID, body: EmptyInput):
    unavailable()


@router.get("/runs/{run_id}/report", response_model=RunReport | ReportPending)
def report(run_id: UUID):
    unavailable()


@router.get("/runs/{run_id}/export", response_model=RunReport)
def export(run_id: UUID):
    unavailable()

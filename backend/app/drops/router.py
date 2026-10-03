from uuid import UUID

from fastapi import APIRouter, Query

from app.core import schemas as s
from app.core.errors import DomainError

router = APIRouter(tags=["drops"])


def unavailable():
    raise DomainError("NOT_IMPLEMENTED", "Domain endpoint is not yet implemented.", 501)


@router.get("/drops", response_model=s.Page[s.DropSummary])
def drops(
    q: str | None = None,
    category: str | None = None,
    phase: s.DropPhase | None = None,
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=100),
):
    unavailable()


@router.get("/drops/{drop_id}", response_model=s.DropDetail)
def drop(drop_id: UUID):
    unavailable()


@router.post(
    "/drops/{drop_id}/entries",
    response_model=s.EntryState,
    status_code=201,
    responses={200: {"model": s.EntryState}},
)
def enter(drop_id: UUID, body: s.EmptyInput):
    unavailable()


@router.get("/drops/{drop_id}/me", response_model=s.MyDropState)
def state(drop_id: UUID):
    unavailable()


@router.get("/entries", response_model=s.Page[s.Receipt])
def entries(cursor: str | None = None, limit: int = Query(50, ge=1, le=100)):
    unavailable()


@router.get("/entries/{entry_id}", response_model=s.Receipt)
def receipt(entry_id: UUID):
    unavailable()


@router.post("/reservations/{reservation_id}/confirm", response_model=s.EntryState)
def confirm(reservation_id: UUID, body: s.EmptyInput):
    unavailable()


@router.get("/admin/drops", response_model=s.Page[s.DropSummary])
def owned(cursor: str | None = None, limit: int = Query(50, ge=1, le=100)):
    unavailable()


@router.post("/admin/drops", response_model=s.DropDetail, status_code=201)
def create(body: s.DraftInput):
    unavailable()


@router.patch("/admin/drops/{drop_id}", response_model=s.DropDetail)
def edit(drop_id: UUID, body: s.DraftPatch):
    unavailable()


@router.post("/admin/drops/{drop_id}/publish", response_model=s.DropDetail)
def publish(drop_id: UUID, body: s.EmptyInput):
    unavailable()


@router.post("/admin/drops/{drop_id}/open", response_model=s.DropDetail)
def open_drop(drop_id: UUID, body: s.EmptyInput):
    unavailable()


@router.post("/admin/drops/{drop_id}/close", response_model=s.DropDetail)
def close(drop_id: UUID, body: s.EmptyInput):
    unavailable()


@router.post("/admin/drops/{drop_id}/draw", response_model=s.DrawStatus, status_code=202)
def draw(drop_id: UUID, body: s.EmptyInput):
    unavailable()


@router.get("/admin/drops/{drop_id}/draw", response_model=s.DrawStatus)
def draw_status(drop_id: UUID):
    unavailable()


@router.post("/admin/drops/{drop_id}/cancel", response_model=s.DropDetail)
def cancel(drop_id: UUID, body: s.CancelInput):
    unavailable()


@router.get("/admin/drops/{drop_id}/metrics", response_model=s.InventoryMetrics)
def metrics(drop_id: UUID):
    unavailable()


@router.get("/admin/drops/{drop_id}/audit", response_model=s.Page[s.AuditRecord])
def audit(drop_id: UUID, cursor: str | None = None, limit: int = Query(50, ge=1, le=100)):
    unavailable()


@router.get("/admin/drops/{drop_id}/entries", response_model=s.Page[s.EntryState])
def admin_entries(drop_id: UUID, cursor: str | None = None, limit: int = Query(50, ge=1, le=100)):
    unavailable()


@router.get(
    "/admin/drops/{drop_id}/entries/export",
    responses={200: {"content": {"text/csv": {"schema": {"type": "string"}}}}},
)
def export(drop_id: UUID):
    unavailable()


@router.post("/admin/drops/{drop_id}/eligibility", response_model=s.GrantSummary)
def grant(drop_id: UUID, body: s.GrantInput):
    unavailable()


@router.delete("/admin/drops/{drop_id}/eligibility/{user_public_id}", status_code=204)
def revoke(drop_id: UUID, user_public_id: str):
    unavailable()

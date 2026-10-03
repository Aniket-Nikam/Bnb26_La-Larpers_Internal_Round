import csv
import io
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy import func, select

from app.core import schemas as s
from app.core.clock import db_now
from app.core.errors import DomainError
from app.core.idempotency import claim, complete
from app.core.pagination import paginate
from app.drops import projections as view
from app.drops import service as svc
from app.persistence import models as m
from app.persistence.database import get_db
from app.security.authorization import get_principal, require_drop_access, require_organizer
from app.security.limits import enforce_limit

router = APIRouter(tags=["drops"])
DB = Annotated[object, Depends(get_db)]
KEY = Annotated[UUID, Header(alias="Idempotency-Key")]


def participant(request: Request, principal: s.Principal = Depends(get_principal)):
    action = "status"
    if request.method == "POST":
        action = "confirmation" if request.url.path.endswith("/confirm") else "entry"
    enforce_limit(request, principal, action)
    return principal


def organizer(request: Request, principal: s.Principal = Depends(require_organizer)):
    enforce_limit(request, principal, "organizer")
    return principal


PARTICIPANT = Annotated[s.Principal, Depends(participant)]
ORGANIZER = Annotated[s.Principal, Depends(organizer)]


def access(db, drop_id, principal, lock=False):
    require_drop_access(principal, drop_id)
    drop = svc.lock_drop(db, drop_id) if lock else db.get(m.Drop, drop_id)
    if drop is None:
        svc.not_found()
    svc.owned(drop, principal)  # domain defense even if a hook is misconfigured
    return drop


def render_result(db, op, receipt_result=False):
    if op.result_kind == "drop":
        return view.detail(db, db.get(m.Drop, op.result_id))
    if op.result_kind == "entry":
        return view.entry_state(db, db.get(m.Entry, op.result_id))
    if op.result_kind == "grant":
        return s.GrantSummary(**op.result_data, server_time=db_now(db))
    if op.result_kind == "draw":
        return view.draw_status(db, db.get(m.DrawRun, op.result_id))
    if op.result_kind == "removed":
        return Response(status_code=204)
    raise DomainError("INTERNAL_ERROR", "Unknown operation result.", 500)


def mutation(db, request, principal, key, payload, execute):
    op = claim(db, principal.id, request.method, request.url.path, key, payload)
    is_new = op.status != "COMPLETED"
    if is_new:
        kind, object_id, data = execute()
        complete(op, kind, object_id, data)
    db.commit()
    return render_result(db, op), is_new


@router.get("/drops", response_model=s.Page[s.DropSummary])
def drops(
    db: DB,
    q: str | None = Query(None, max_length=200),
    category: str | None = Query(None, max_length=80),
    phase: s.DropPhase | None = None,
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=100),
):
    statement = select(m.Drop).where(m.Drop.phase != "DRAFT")
    if q:
        statement = statement.where(m.Drop.title.icontains(q, autoescape=True))
    if category:
        statement = statement.where(m.Drop.category == category)
    if phase:
        statement = statement.where(m.Drop.phase == phase)
    rows, next_cursor = paginate(db, statement, m.Drop, cursor, limit)
    return s.Page(items=[view.summary(db, d) for d in rows], next_cursor=next_cursor)


@router.get("/drops/{drop_id}", response_model=s.DropDetail)
def drop(drop_id: UUID, request: Request, db: DB):
    value = db.get(m.Drop, drop_id)
    if value is None:
        svc.not_found()
    if value.phase == "DRAFT":
        try:
            principal = get_principal(request)
            svc.owned(value, principal)
        except DomainError:
            svc.not_found()
    return view.detail(db, value)


@router.post(
    "/drops/{drop_id}/entries",
    response_model=s.EntryState,
    status_code=201,
    responses={200: {"model": s.EntryState}},
)
def enter(
    drop_id: UUID,
    body: s.EmptyInput,
    request: Request,
    response: Response,
    db: DB,
    principal: PARTICIPANT,
    key: KEY,
):
    inserted = False

    def execute():
        nonlocal inserted
        entry, inserted = svc.enter(db, drop_id, principal)
        return "entry", entry.id, None

    result, new_op = mutation(db, request, principal, key, body.model_dump(), execute)
    response.status_code = 201 if new_op and inserted else 200
    return result


@router.get("/drops/{drop_id}/me", response_model=s.MyDropState)
def state(drop_id: UUID, db: DB, principal: PARTICIPANT):
    value = db.get(m.Drop, drop_id)
    if value is None or value.phase == "DRAFT":
        svc.not_found()
    entry = db.scalar(
        select(m.Entry).where(m.Entry.drop_id == drop_id, m.Entry.user_id == principal.id)
    )
    grant = db.scalar(
        select(m.EligibilityGrant).where(
            m.EligibilityGrant.drop_id == drop_id, m.EligibilityGrant.user_id == principal.id
        )
    )
    eligible = grant is not None and grant.revoked_at is None
    return s.MyDropState(
        entry=view.entry_state(db, entry) if entry else None,
        eligibility=s.Eligibility(
            eligible=eligible,
            reason=None if eligible else ("REVOKED" if grant else "INVITATION_REQUIRED"),
        ),
        server_time=db_now(db),
    )


@router.get("/entries", response_model=s.Page[s.Receipt])
def entries(
    db: DB, principal: PARTICIPANT, cursor: str | None = None, limit: int = Query(50, ge=1, le=100)
):
    rows, next_cursor = paginate(
        db, select(m.Entry).where(m.Entry.user_id == principal.id), m.Entry, cursor, limit
    )
    return s.Page(items=[view.receipt(db, e) for e in rows], next_cursor=next_cursor)


@router.get("/entries/{entry_id}", response_model=s.Receipt)
def receipt(entry_id: UUID, db: DB, principal: PARTICIPANT):
    entry = db.get(m.Entry, entry_id)
    if entry is None or entry.user_id != principal.id:
        svc.not_found()
    return view.receipt(db, entry)


@router.post("/reservations/{reservation_id}/confirm", response_model=s.EntryState)
def confirm(
    reservation_id: UUID,
    body: s.EmptyInput,
    request: Request,
    db: DB,
    principal: PARTICIPANT,
    key: KEY,
):
    from app.allocation.reservations import confirm as confirm_reservation

    def execute():
        entry = confirm_reservation(db, reservation_id, principal)
        return "entry", entry.id, None

    return mutation(db, request, principal, key, body.model_dump(), execute)[0]


@router.get("/admin/drops", response_model=s.Page[s.DropSummary])
def owned(
    db: DB, principal: ORGANIZER, cursor: str | None = None, limit: int = Query(50, ge=1, le=100)
):
    statement = select(m.Drop)
    if principal.role != "admin":
        statement = statement.where(m.Drop.owner_id == principal.id)
    rows, next_cursor = paginate(db, statement, m.Drop, cursor, limit)
    return s.Page(items=[view.summary(db, d) for d in rows], next_cursor=next_cursor)


@router.post("/admin/drops", response_model=s.DropDetail, status_code=201)
def create(body: s.DraftInput, request: Request, db: DB, principal: ORGANIZER, key: KEY):
    def execute():
        drop = svc.create(db, principal, body)
        return "drop", drop.id, None

    return mutation(db, request, principal, key, body.model_dump(mode="json"), execute)[0]


@router.patch("/admin/drops/{drop_id}", response_model=s.DropDetail)
def edit(
    drop_id: UUID, body: s.DraftPatch, request: Request, db: DB, principal: ORGANIZER, key: KEY
):
    require_drop_access(principal, drop_id)

    def execute():
        drop = access(db, drop_id, principal, lock=True)
        svc.edit(db, drop, principal, body)
        return "drop", drop.id, None

    return mutation(
        db, request, principal, key, body.model_dump(mode="json", exclude_unset=True), execute
    )[0]


def drop_command(db, request, principal, key, drop_id, body, command):
    require_drop_access(principal, drop_id)

    def execute():
        drop = access(db, drop_id, principal, lock=True)
        command(db, drop, principal)
        return "drop", drop.id, None

    return mutation(db, request, principal, key, body.model_dump(mode="json"), execute)[0]


@router.post("/admin/drops/{drop_id}/publish", response_model=s.DropDetail)
def publish(
    drop_id: UUID, body: s.EmptyInput, request: Request, db: DB, principal: ORGANIZER, key: KEY
):
    return drop_command(db, request, principal, key, drop_id, body, svc.publish)


@router.post("/admin/drops/{drop_id}/open", response_model=s.DropDetail)
def open_drop(
    drop_id: UUID, body: s.EmptyInput, request: Request, db: DB, principal: ORGANIZER, key: KEY
):
    return drop_command(db, request, principal, key, drop_id, body, svc.open_drop)


@router.post("/admin/drops/{drop_id}/close", response_model=s.DropDetail)
def close(
    drop_id: UUID, body: s.EmptyInput, request: Request, db: DB, principal: ORGANIZER, key: KEY
):
    from app.allocation.draw import close_drop

    return drop_command(db, request, principal, key, drop_id, body, close_drop)


@router.post("/admin/drops/{drop_id}/draw", response_model=s.DrawStatus, status_code=202)
def draw(
    drop_id: UUID, body: s.EmptyInput, request: Request, db: DB, principal: ORGANIZER, key: KEY
):
    from app.allocation.draw import trigger_draw

    require_drop_access(principal, drop_id)

    def execute():
        drop = access(db, drop_id, principal, lock=True)
        run = trigger_draw(db, drop, principal)
        return "draw", run.id, None

    return mutation(db, request, principal, key, body.model_dump(), execute)[0]


@router.get("/admin/drops/{drop_id}/draw", response_model=s.DrawStatus)
def draw_status(drop_id: UUID, db: DB, principal: ORGANIZER):
    access(db, drop_id, principal)
    run = db.scalar(select(m.DrawRun).where(m.DrawRun.drop_id == drop_id))
    if run is None:
        raise DomainError("DRAW_NOT_CREATED", "This drop has no frozen draw.", 404)
    return view.draw_status(db, run)


@router.post("/admin/drops/{drop_id}/cancel", response_model=s.DropDetail)
def cancel(
    drop_id: UUID, body: s.CancelInput, request: Request, db: DB, principal: ORGANIZER, key: KEY
):
    return drop_command(
        db,
        request,
        principal,
        key,
        drop_id,
        body,
        lambda db, d, p: svc.cancel(db, d, p, body.reason),
    )


@router.get("/admin/drops/{drop_id}/metrics", response_model=s.InventoryMetrics)
def metrics(drop_id: UUID, db: DB, principal: ORGANIZER):
    drop = access(db, drop_id, principal)
    entered = db.scalar(select(func.count()).select_from(m.Entry).where(m.Entry.drop_id == drop_id))
    run = db.scalar(select(m.DrawRun).where(m.DrawRun.drop_id == drop_id))
    eligible = (
        run.total_entries
        if run
        else db.scalar(
            select(func.count())
            .select_from(m.Entry)
            .join(m.EligibilityGrant, m.Entry.qualifying_grant_id == m.EligibilityGrant.id)
            .where(m.Entry.drop_id == drop_id, m.EligibilityGrant.revoked_at.is_(None))
        )
    )
    counts = dict(
        db.execute(
            select(m.Reservation.status, func.count())
            .where(m.Reservation.drop_id == drop_id)
            .group_by(m.Reservation.status)
        ).all()
    )
    offered, confirmed, expired = (
        counts.get(name, 0) for name in ("OFFERED", "CONFIRMED", "EXPIRED")
    )
    slots = db.scalar(
        select(func.count()).select_from(m.SeatSlot).where(m.SeatSlot.drop_id == drop_id)
    )
    active = select(m.Reservation).where(
        m.Reservation.drop_id == drop_id, m.Reservation.status.in_(["OFFERED", "CONFIRMED"])
    )
    owner_groups = (
        active.with_only_columns(m.Reservation.user_id, func.count().label("n"))
        .group_by(m.Reservation.user_id)
        .subquery()
    )
    duplicate_owners = db.scalar(
        select(func.coalesce(func.sum(owner_groups.c.n - 1), 0)).where(owner_groups.c.n > 1)
    )
    slot_groups = (
        active.with_only_columns(m.Reservation.seat_slot_id, func.count().label("n"))
        .group_by(m.Reservation.seat_slot_id)
        .subquery()
    )
    duplicate_slots = db.scalar(
        select(func.count()).select_from(slot_groups).where(slot_groups.c.n > 1)
    )
    return s.InventoryMetrics(
        drop_id=drop_id,
        capacity=drop.capacity,
        entered_count=entered,
        eligible_count=eligible,
        active_reservations=offered,
        confirmed_seats=confirmed,
        free_seats=drop.capacity - offered - confirmed,
        expired_reservations=expired,
        duplicate_active_owners=duplicate_owners,
        integrity_ok=not duplicate_owners
        and not duplicate_slots
        and offered + confirmed <= slots
        and (
            slots == drop.capacity
            if drop.phase != "DRAFT" and slots
            else drop.phase in {"DRAFT", "CANCELLED"}
        ),
        server_time=db_now(db),
    )


@router.get("/admin/drops/{drop_id}/audit", response_model=s.Page[s.AuditRecord])
def audit(
    drop_id: UUID,
    db: DB,
    principal: ORGANIZER,
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=100),
):
    access(db, drop_id, principal)
    rows, next_cursor = paginate(
        db, select(m.AuditEvent).where(m.AuditEvent.drop_id == drop_id), m.AuditEvent, cursor, limit
    )
    return s.Page(items=[s.AuditRecord.model_validate(a) for a in rows], next_cursor=next_cursor)


@router.get("/admin/drops/{drop_id}/entries", response_model=s.Page[s.EntryState])
def admin_entries(
    drop_id: UUID,
    db: DB,
    principal: ORGANIZER,
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=100),
):
    access(db, drop_id, principal)
    rows, next_cursor = paginate(
        db, select(m.Entry).where(m.Entry.drop_id == drop_id), m.Entry, cursor, limit
    )
    return s.Page(items=[view.entry_state(db, e) for e in rows], next_cursor=next_cursor)


@router.get(
    "/admin/drops/{drop_id}/entries/export",
    response_class=Response,
    responses={200: {"content": {"text/csv": {"schema": {"type": "string"}}}}},
)
def export(drop_id: UUID, db: DB, principal: ORGANIZER):
    access(db, drop_id, principal)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["public_entry_id", "status", "rank"])
    for entry in db.scalars(select(m.Entry).where(m.Entry.drop_id == drop_id).order_by(m.Entry.id)):
        state = view.entry_state(db, entry)
        writer.writerow([state.public_entry_id, state.status, state.rank])
    return Response(
        out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="entries.csv"'},
    )


@router.post("/admin/drops/{drop_id}/eligibility", response_model=s.GrantSummary)
def grant(
    drop_id: UUID, body: s.GrantInput, request: Request, db: DB, principal: ORGANIZER, key: KEY
):
    require_drop_access(principal, drop_id)

    def execute():
        drop = access(db, drop_id, principal, lock=True)
        return "grant", None, svc.grant(db, drop, principal, body)

    return mutation(db, request, principal, key, body.model_dump(), execute)[0]


@router.delete("/admin/drops/{drop_id}/eligibility/{user_public_id}", status_code=204)
def revoke(
    drop_id: UUID, user_public_id: str, request: Request, db: DB, principal: ORGANIZER, key: KEY
):
    require_drop_access(principal, drop_id)

    def execute():
        drop = access(db, drop_id, principal, lock=True)
        svc.revoke(db, drop, principal, user_public_id)
        return "removed", None, None

    return mutation(db, request, principal, key, {}, execute)[0]

"""The single shared durable model system. Security P2; lab P4; migrations P1."""

import secrets
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def public_id():
    return secrets.token_urlsafe(24)


class Identity:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)


class User(Identity, Base):
    __tablename__ = "users"
    public_id: Mapped[str] = mapped_column(String(64), unique=True, default=public_id)
    display_name: Mapped[str] = mapped_column(String(100))
    timezone: Mapped[str] = mapped_column(String(100), default="UTC")
    role: Mapped[str] = mapped_column(String(16), default="participant")
    __table_args__ = (CheckConstraint("role IN ('participant','organizer','admin')"),)


class AccessCredential(Identity, Base):
    __tablename__ = "access_credentials"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    digest: Mapped[str] = mapped_column(String(128), unique=True)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Session(Identity, Base):
    __tablename__ = "sessions"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    credential_id: Mapped[UUID] = mapped_column(ForeignKey("access_credentials.id"))
    token_digest: Mapped[str] = mapped_column(String(128), unique=True)
    csrf_secret: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Drop(Identity, Base):
    __tablename__ = "drops"
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(80))
    location_type: Mapped[str] = mapped_column(String(16))
    location_label: Mapped[str] = mapped_column(String(200))
    capacity: Mapped[int] = mapped_column(Integer)
    confirmation_seconds: Mapped[int] = mapped_column(Integer)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    mode: Mapped[str] = mapped_column(String(16), default="LOTTERY")
    phase: Mapped[str] = mapped_column(String(16), default="DRAFT", index=True)
    rules_version: Mapped[str] = mapped_column(String(32), default="v1.0")
    seed_commitment: Mapped[str | None] = mapped_column(String(64))
    encrypted_seed: Mapped[bytes | None] = mapped_column(LargeBinary)
    cancellation_reason: Mapped[str | None] = mapped_column(String(500))
    admission_sequence: Mapped[int] = mapped_column(Integer, default=0)
    admission_cursor: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        CheckConstraint("capacity BETWEEN 1 AND 500"),
        CheckConstraint("confirmation_seconds BETWEEN 1 AND 604800"),
        CheckConstraint("starts_at < ends_at"),
        CheckConstraint("location_type IN ('online','venue')"),
        CheckConstraint("mode IN ('LOTTERY','FCFS_DEMO')"),
        CheckConstraint(
            "phase IN ('DRAFT','SCHEDULED','OPEN','CLOSED','DRAWING','OFFERING','COMPLETED','CANCELLED')"
        ),
    )


class EligibilityGrant(Identity, Base):
    __tablename__ = "eligibility_grants"
    drop_id: Mapped[UUID] = mapped_column(ForeignKey("drops.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    credential_id: Mapped[UUID | None] = mapped_column(ForeignKey("access_credentials.id"))
    granted_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("drop_id", "user_id"),
        UniqueConstraint("id", "drop_id", "user_id"),
    )


class Entry(Identity, Base):
    __tablename__ = "entries"
    drop_id: Mapped[UUID] = mapped_column(ForeignKey("drops.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    qualifying_grant_id: Mapped[UUID] = mapped_column()
    public_entry_id: Mapped[str] = mapped_column(String(64), unique=True, default=public_id)
    receipt_id: Mapped[str] = mapped_column(String(64), unique=True, default=public_id)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    admission_sequence: Mapped[int | None] = mapped_column(Integer)
    __table_args__ = (
        UniqueConstraint("drop_id", "user_id"),
        UniqueConstraint("id", "drop_id", "user_id"),
        UniqueConstraint("drop_id", "admission_sequence"),
        ForeignKeyConstraint(
            ["qualifying_grant_id", "drop_id", "user_id"],
            ["eligibility_grants.id", "eligibility_grants.drop_id", "eligibility_grants.user_id"],
        ),
    )


class SeatSlot(Identity, Base):
    __tablename__ = "seat_slots"
    drop_id: Mapped[UUID] = mapped_column(ForeignKey("drops.id"))
    slot_number: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        UniqueConstraint("drop_id", "slot_number"),
        UniqueConstraint("id", "drop_id"),
        CheckConstraint("slot_number > 0"),
    )


class Reservation(Identity, Base):
    __tablename__ = "reservations"
    drop_id: Mapped[UUID] = mapped_column(ForeignKey("drops.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    entry_id: Mapped[UUID] = mapped_column()
    seat_slot_id: Mapped[UUID] = mapped_column()
    status: Mapped[str] = mapped_column(String(16), default="OFFERED")
    offered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["entry_id", "drop_id", "user_id"], ["entries.id", "entries.drop_id", "entries.user_id"]
        ),
        ForeignKeyConstraint(["seat_slot_id", "drop_id"], ["seat_slots.id", "seat_slots.drop_id"]),
        UniqueConstraint("entry_id"),
        CheckConstraint("status IN ('OFFERED','CONFIRMED','EXPIRED')"),
        CheckConstraint("expires_at > offered_at"),
        CheckConstraint("(status = 'CONFIRMED') = (confirmed_at IS NOT NULL)"),
        CheckConstraint("(status = 'EXPIRED') = (expired_at IS NOT NULL)"),
        Index(
            "uq_active_slot",
            "drop_id",
            "seat_slot_id",
            unique=True,
            postgresql_where=text("status IN ('OFFERED','CONFIRMED')"),
        ),
        Index(
            "uq_active_user",
            "drop_id",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('OFFERED','CONFIRMED')"),
        ),
    )


class DrawRun(Identity, Base):
    __tablename__ = "draw_runs"
    drop_id: Mapped[UUID] = mapped_column(ForeignKey("drops.id"), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="FROZEN")
    algorithm_version: Mapped[str] = mapped_column(String(32), default="hmac-sha256-v1")
    manifest_commitment: Mapped[str] = mapped_column(String(64))
    total_entries: Mapped[int] = mapped_column(Integer)
    processed_entries: Mapped[int] = mapped_column(Integer, default=0)
    next_rank: Mapped[int] = mapped_column(Integer, default=1)
    recoverable_error: Mapped[str | None] = mapped_column(String(200))
    __table_args__ = (
        CheckConstraint("status IN ('FROZEN','COMPUTING','PUBLISHED')"),
        CheckConstraint("next_rank > 0"),
        CheckConstraint("total_entries BETWEEN 0 AND 50000"),
    )


class FrozenEntry(Base):
    __tablename__ = "frozen_entries"
    draw_id: Mapped[UUID] = mapped_column(ForeignKey("draw_runs.id"), primary_key=True)
    entry_id: Mapped[UUID] = mapped_column(ForeignKey("entries.id"), primary_key=True)
    public_entry_id: Mapped[str] = mapped_column(String(64))
    __table_args__ = (UniqueConstraint("draw_id", "public_entry_id"),)


class DrawRank(Base):
    __tablename__ = "draw_ranks"
    draw_id: Mapped[UUID] = mapped_column(primary_key=True)
    entry_id: Mapped[UUID] = mapped_column(primary_key=True)
    rank: Mapped[int] = mapped_column(Integer)
    score_bytes: Mapped[bytes | None] = mapped_column(LargeBinary)
    __table_args__ = (
        ForeignKeyConstraint(
            ["draw_id", "entry_id"], ["frozen_entries.draw_id", "frozen_entries.entry_id"]
        ),
        UniqueConstraint("draw_id", "rank"),
        CheckConstraint("rank > 0"),
        CheckConstraint("score_bytes IS NULL OR octet_length(score_bytes) = 32"),
    )


class AuditEvent(Identity, Base):
    __tablename__ = "audit_events"
    drop_id: Mapped[UUID | None] = mapped_column(ForeignKey("drops.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    object_type: Mapped[str] = mapped_column(String(32))
    object_id: Mapped[UUID] = mapped_column()
    actor_public_id: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )


class IdempotencyOperation(Identity, Base):
    __tablename__ = "idempotency_operations"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    method: Mapped[str] = mapped_column(String(8))
    path: Mapped[str] = mapped_column(String(512))
    key: Mapped[UUID] = mapped_column()
    fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="CLAIMED")
    result_kind: Mapped[str | None] = mapped_column(String(32))
    result_id: Mapped[UUID | None] = mapped_column()
    result_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
    __table_args__ = (
        UniqueConstraint("user_id", "method", "path", "key"),
        CheckConstraint("status IN ('CLAIMED','COMPLETED')"),
    )


class LabRun(Identity, Base):
    __tablename__ = "lab_runs"
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    scenario: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="QUEUED")
    config: Mapped[dict] = mapped_column(JSONB)
    progress: Mapped[dict] = mapped_column(JSONB, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
    error: Mapped[dict | None] = mapped_column(JSONB)
    report: Mapped[dict | None] = mapped_column(JSONB)
    report_path: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        CheckConstraint("status IN ('QUEUED','RUNNING','STOPPING','STOPPED','COMPLETED','FAILED')"),
        Index(
            "uq_single_active_lab",
            text("(1)"),
            unique=True,
            postgresql_where=text("status IN ('QUEUED','RUNNING','STOPPING')"),
        ),
    )

"""
Shared SQLAlchemy ORM models — P1 area.
P2 reads User, AccessCredential, Session (EligibilityGrant for authorization).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    public_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, default=_uuid
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    # role: participant | organizer | admin — immutable through participant profile API
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="participant")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )

    credentials: Mapped[list["AccessCredential"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AccessCredential(Base):
    """
    Stores a keyed HMAC digest of the raw access code.
    The raw code is NEVER stored here.
    """
    __tablename__ = "access_credentials"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # HMAC-SHA256(CREDENTIAL_DIGEST_KEY, raw_code) stored as hex
    credential_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    label: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    user: Mapped["User"] = relationship(back_populates="credentials")

    __table_args__ = (
        Index("ix_access_credentials_user_id", "user_id"),
    )

    @property
    def is_valid(self) -> bool:
        from backend.app.core.clock import utc_now
        now = utc_now()
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and now >= self.expires_at:
            return False
        return True


class Session(Base):
    """
    Durable opaque session. Only the digest of the random token is stored.
    """
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # SHA-256(random_token) stored as hex — never the raw token
    token_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # Per-session CSRF secret (random bytes, stored server-side only)
    csrf_secret: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Track the IP and UA for audit purposes only — not for authorization
    created_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    user: Mapped["User"] = relationship(back_populates="sessions")

    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_token_digest", "token_digest"),
    )

    @property
    def is_valid(self) -> bool:
        from backend.app.core.clock import utc_now
        now = utc_now()
        if self.revoked_at is not None:
            return False
        if now >= self.expires_at:
            return False
        return True


class EligibilityGrant(Base):
    """
    Per-drop per-user grant. Participants cannot grant themselves this.
    Created only by organizer-provisioned setup.
    """
    __tablename__ = "eligibility_grants"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    drop_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )
    granted_by_user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), nullable=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("drop_id", "user_id", name="uq_eligibility_grants_drop_user"),
        Index("ix_eligibility_grants_drop_id", "drop_id"),
        Index("ix_eligibility_grants_user_id", "user_id"),
    )

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

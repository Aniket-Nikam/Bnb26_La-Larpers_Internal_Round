"""
Wall-clock adapter — P1 area.
Always use clock_timestamp()-equivalent; never transaction-start now().
"""
from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Fresh wall-clock UTC datetime (not cached to transaction start)."""
    return datetime.now(tz=timezone.utc)


def utc_now_naive() -> datetime:
    """Naive UTC datetime for SQLAlchemy comparisons where needed."""
    return datetime.utcnow()

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session


def db_now(db: Session) -> datetime:
    """Read wall clock in a NEW statement after acquiring required locks."""
    return db.scalar(select(func.clock_timestamp()))

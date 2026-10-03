import base64
from uuid import UUID

from app.core.errors import DomainError


def paginate(db, statement, model, cursor, limit):
    if cursor:
        try:
            value = UUID(base64.b64decode(cursor, altchars=b"-_", validate=True).decode())
        except (ValueError, UnicodeError):
            raise DomainError("VALIDATION_ERROR", "Invalid page cursor.", 422) from None
        statement = statement.where(model.id > value)
    rows = list(db.scalars(statement.order_by(model.id).limit(limit + 1)))
    next_cursor = None
    if len(rows) > limit:
        next_cursor = base64.urlsafe_b64encode(str(rows[limit - 1].id).encode()).decode()
    return rows[:limit], next_cursor

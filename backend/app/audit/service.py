from app.persistence.models import AuditEvent


def record(db, drop_id, event_type, object_type, object_id, principal=None, reason=None):
    db.add(
        AuditEvent(
            drop_id=drop_id,
            event_type=event_type,
            object_type=object_type,
            object_id=object_id,
            actor_public_id=principal.public_id if principal else None,
            reason=reason,
        )
    )

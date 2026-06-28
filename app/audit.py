from app.database import init_db, insert_audit_event, list_audit_events
from app.schemas import AuditEvent


def write_audit_event(event: AuditEvent) -> AuditEvent:
    init_db()
    insert_audit_event(event.model_dump(mode="json"))
    return event


def fetch_audit_events() -> list[AuditEvent]:
    init_db()
    return [AuditEvent.model_validate(event) for event in list_audit_events()]

from app.audit import write_audit_event
from app.database import init_db
from app.schemas import AuditEvent


def main() -> None:
    init_db()
    event = AuditEvent(
        request_id="seed-request-001",
        event_type="seeded_demo_event",
        request_payload={"message": "seeded"},
        extracted_intent={"action_type": "inventory_update"},
        validation_result={"decision": "allowed"},
        decision="allowed",
        approval_status="not_required",
        final_erp_response={"status": "seeded"},
    )
    write_audit_event(event)
    print("Seeded 1 audit event.")


if __name__ == "__main__":
    main()


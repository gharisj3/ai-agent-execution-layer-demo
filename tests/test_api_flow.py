from fastapi.testclient import TestClient

from app.main import app


def test_high_risk_payment_can_be_logged_after_approval() -> None:
    with TestClient(app) as client:
        payload = {
            "request_id": "api-flow-001",
            "source": "n8n_webhook",
            "raw_text": "Please process a vendor payment of 18500 USD to vendor-204 immediately.",
            "metadata": {
                "vendor_id": "VENDOR-204",
                "vendor_status": "active",
                "amount": 18500,
                "currency": "USD",
                "confidence": 0.95,
            },
        }

        decision = client.post("/guardrails/evaluate", json=payload).json()
        assert decision["decision"] == "approval_required"

        approval = client.post(
            "/approval/simulate",
            json={
                "request_id": "api-flow-001",
                "approver": "demo@example.com",
                "decision": "approve",
                "comments": "approved for test",
            },
        ).json()
        assert approval["approval_status"] == "approved"

        erp_result = client.post("/erp/vendor-payment", json=decision["extracted_intent"]).json()
        audit_result = client.post(
            "/audit/events",
            json={
                "request_id": "api-flow-001",
                "event_type": "test_flow",
                "request_payload": payload,
                "extracted_intent": decision["extracted_intent"],
                "validation_result": decision,
                "decision": decision["decision"],
                "approval_status": approval["approval_status"],
                "final_erp_response": erp_result,
            },
        )
        assert audit_result.status_code == 200

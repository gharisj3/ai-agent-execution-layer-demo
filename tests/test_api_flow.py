from fastapi.testclient import TestClient

from app.config import settings
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


def test_inactive_vendor_metadata_is_blocked() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/guardrails/evaluate",
            json={
                "request_id": "api-flow-002",
                "source": "n8n_webhook",
                "raw_text": "Please pay 2000 USD to vendor-410 for an invoice.",
                "metadata": {
                    "vendor_id": "VENDOR-410",
                    "vendor_status": "inactive",
                    "confidence": 0.96,
                },
            },
        )
        assert response.status_code == 200
        assert response.json()["decision"] == "blocked"


def test_missing_provider_key_returns_clear_error(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mock_mode", False)
    monkeypatch.setattr(settings, "default_llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "")
    with TestClient(app) as client:
        response = client.post(
            "/agent/extract",
            json={"raw_text": "Please update SKU-1 by 10 units after the count."},
        )
    assert response.status_code == 502
    assert "Configure its API key" in response.json()["detail"]


def test_validated_intent_can_be_evaluated_without_reextraction() -> None:
    intent = {
        "request_id": "api-flow-003",
        "action_type": "inventory_update",
        "inventory_item_id": "SKU-3",
        "inventory_delta": 10,
        "confidence": 0.98,
        "raw_text": "Update SKU-3 by 10 units after the cycle count.",
    }
    with TestClient(app) as client:
        response = client.post("/guardrails/evaluate-intent", json=intent)
    assert response.status_code == 200
    assert response.json()["decision"] == "allowed"

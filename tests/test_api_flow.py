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
            "/approval/decide",
            headers={"X-Reviewer-Token": "test-reviewer-token"},
            json={
                "request_id": "api-flow-001",
                "approver": "demo@example.com",
                "decision": "approve",
                "comments": "approved for test",
                "intent": decision["extracted_intent"],
            },
        ).json()
        assert approval["approval_status"] == "approved"

        executed = client.post(
            "/erp/vendor-payment",
            json=decision["extracted_intent"],
            headers={"X-Approval-Id": approval["approval_id"]},
        )
        assert executed.status_code == 200
        erp_result = executed.json()
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


def test_blocked_and_unapproved_actions_cannot_execute():
    with TestClient(app) as client:
        intent = {
            "request_id": "blocked-test",
            "action_type": "vendor_payment",
            "vendor_id": "V-1",
            "vendor_status": "inactive",
            "amount": 20000,
            "confidence": 0.99,
            "raw_text": "Synthetic blocked payment",
        }
        assert client.post("/erp/vendor-payment", json=intent).status_code == 403
        intent["vendor_status"] = "active"
        assert client.post("/erp/vendor-payment", json=intent).status_code == 403
        simulated = client.post(
            "/approval/simulate",
            json={"request_id": intent["request_id"], "decision": "approve"},
        )
        assert simulated.json()["simulation_only"] is True
        assert client.post("/erp/vendor-payment", json=intent).status_code == 403
        assert (
            client.post(
                "/approval/decide",
                json={
                    "request_id": intent["request_id"],
                    "decision": "approve",
                    "intent": intent,
                },
            ).status_code
            == 401
        )


def test_approval_is_bound_to_intent_and_cannot_be_replayed():
    with TestClient(app) as client:
        intent = {
            "request_id": "bound-test",
            "action_type": "inventory_update",
            "inventory_item_id": "SKU-1",
            "inventory_delta": 1000,
            "confidence": 0.99,
            "raw_text": "Synthetic inventory update",
        }
        response = client.post(
            "/approval/decide",
            headers={"X-Reviewer-Token": "test-reviewer-token"},
            json={
                "request_id": intent["request_id"],
                "decision": "approve",
                "intent": intent,
            },
        )
        assert response.status_code == 200
        auth = {"X-Approval-Id": response.json()["approval_id"]}
        changed = {**intent, "inventory_delta": 2000}
        assert (
            client.post("/erp/inventory-update", json=changed, headers=auth).status_code
            == 403
        )
        assert (
            client.post("/erp/inventory-update", json=intent, headers=auth).status_code
            == 200
        )
        assert (
            client.post("/erp/inventory-update", json=intent, headers=auth).status_code
            == 403
        )


def test_rejected_approval_does_not_allow_execution():
    with TestClient(app) as client:
        intent = {
            "request_id": "rejected-test",
            "action_type": "inventory_update",
            "inventory_item_id": "SKU-1",
            "inventory_delta": 1000,
            "confidence": 0.99,
            "raw_text": "Synthetic inventory update",
        }
        response = client.post(
            "/approval/decide",
            headers={"X-Reviewer-Token": "test-reviewer-token"},
            json={
                "request_id": intent["request_id"],
                "decision": "reject",
                "intent": intent,
            },
        )
        assert response.status_code == 200
        assert (
            client.post(
                "/erp/inventory-update",
                json=intent,
                headers={"X-Approval-Id": response.json()["approval_id"]},
            ).status_code
            == 403
        )


def test_later_rejection_invalidates_previous_approval():
    with TestClient(app) as client:
        intent = {
            "request_id": "reconsidered",
            "action_type": "inventory_update",
            "inventory_item_id": "SKU-1",
            "inventory_delta": 1000,
            "confidence": 0.99,
            "raw_text": "Synthetic inventory update",
        }
        headers = {"X-Reviewer-Token": "test-reviewer-token"}
        payload = {"request_id": intent["request_id"], "intent": intent}
        original = client.post(
            "/approval/decide", headers=headers, json={**payload, "decision": "approve"}
        )
        rejected = client.post(
            "/approval/decide", headers=headers, json={**payload, "decision": "reject"}
        )
        assert rejected.status_code == 200
        result = client.post(
            "/erp/inventory-update",
            json=intent,
            headers={"X-Approval-Id": original.json()["approval_id"]},
        )
        assert result.status_code == 403

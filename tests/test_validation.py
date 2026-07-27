from app.agent_service import extract_intent
from app.schemas import IncomingRequest


def test_agent_extracts_low_risk_inventory_request() -> None:
    payload = IncomingRequest(
        request_id="test-001",
        raw_text="Update SKU-100 by 25 units after cycle count.",
        metadata={"inventory_item_id": "SKU-100", "confidence": 0.9},
    )
    result = extract_intent(payload)
    assert result.action_type == "inventory_update"
    assert result.inventory_item_id == "SKU-100"
    assert result.confidence >= 0.75


def test_mock_extraction_preserves_vendor_status_metadata() -> None:
    payload = IncomingRequest(
        request_id="test-002",
        raw_text="Please pay 500 USD to vendor-42 for an approved invoice.",
        metadata={"vendor_status": "inactive", "confidence": 0.95},
    )
    assert extract_intent(payload).vendor_status == "inactive"

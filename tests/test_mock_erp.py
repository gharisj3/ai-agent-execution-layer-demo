from app.mock_erp import run_inventory_update, run_vendor_payment
from app.schemas import ActionType, ExtractedIntent


def test_mock_vendor_payment_returns_reference() -> None:
    intent = ExtractedIntent(
        request_id="erp-test-001",
        action_type=ActionType.vendor_payment,
        vendor_id="VENDOR-3",
        vendor_status="active",
        amount=500,
        currency="USD",
        confidence=0.99,
        raw_text="Pay vendor 500 USD",
    )
    result = run_vendor_payment(intent)
    assert result.success is True
    assert result.erp_reference.startswith("PAY-")


def test_mock_inventory_update_returns_reference() -> None:
    intent = ExtractedIntent(
        request_id="erp-test-002",
        action_type=ActionType.inventory_update,
        inventory_item_id="SKU-2",
        inventory_delta=12,
        confidence=0.99,
        raw_text="Add 12 units to SKU-2",
    )
    result = run_inventory_update(intent)
    assert result.success is True
    assert result.erp_reference.startswith("INV-")

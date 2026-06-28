from app.guardrails import evaluate_guardrails
from app.schemas import ActionType, ExtractedIntent


def test_payment_above_threshold_requires_approval() -> None:
    intent = ExtractedIntent(
        request_id="test-approval-001",
        action_type=ActionType.vendor_payment,
        vendor_id="VENDOR-9",
        vendor_status="active",
        amount=12000,
        currency="USD",
        confidence=0.95,
        raw_text="Pay vendor 12000 USD",
    )
    result = evaluate_guardrails(intent)
    assert result.decision == "approval_required"


def test_inactive_vendor_is_blocked() -> None:
    intent = ExtractedIntent(
        request_id="test-block-001",
        action_type=ActionType.vendor_payment,
        vendor_id="VENDOR-10",
        vendor_status="inactive",
        amount=2000,
        currency="USD",
        confidence=0.95,
        raw_text="Pay vendor 2000 USD",
    )
    result = evaluate_guardrails(intent)
    assert result.decision == "blocked"


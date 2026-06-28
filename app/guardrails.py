from app.config import settings
from app.schemas import ActionType, DecisionType, ExtractedIntent, GuardrailDecision


def evaluate_guardrails(intent: ExtractedIntent) -> GuardrailDecision:
    reasons: list[str] = []
    validated_fields = {
        "action_type_allowed": intent.action_type in {ActionType.vendor_payment, ActionType.inventory_update},
        "confidence_ok": intent.confidence >= settings.min_confidence,
        "vendor_id_present": bool(intent.vendor_id) if intent.action_type == ActionType.vendor_payment else True,
        "inventory_item_present": bool(intent.inventory_item_id) if intent.action_type == ActionType.inventory_update else True,
    }

    if not validated_fields["action_type_allowed"]:
        reasons.append("Unknown action type is blocked.")
        return _decision(intent, DecisionType.blocked, reasons, validated_fields, "high")

    if intent.action_type == ActionType.vendor_payment and not intent.vendor_id:
        reasons.append("Missing vendor ID fails validation.")

    if intent.action_type == ActionType.inventory_update and not intent.inventory_item_id:
        reasons.append("Missing inventory item ID fails validation.")

    if intent.confidence < settings.min_confidence:
        reasons.append(f"Confidence below {settings.min_confidence:.2f} requires review.")

    if intent.action_type == ActionType.vendor_payment and intent.vendor_status == "inactive":
        reasons.append("Payment to inactive vendor is blocked.")
        return _decision(intent, DecisionType.blocked, reasons, validated_fields, "high")

    if reasons and any("fails validation" in item for item in reasons):
        return _decision(intent, DecisionType.blocked, reasons, validated_fields, "high")

    if intent.action_type == ActionType.vendor_payment and (intent.amount or 0) > settings.payment_approval_threshold:
        reasons.append(
            f"Vendor payment above {settings.payment_approval_threshold:.0f} requires approval."
        )
        return _decision(intent, DecisionType.approval_required, reasons, validated_fields, "high")

    if intent.action_type == ActionType.inventory_update and abs(intent.inventory_delta or 0) > settings.inventory_approval_threshold:
        reasons.append(
            f"Inventory update above {settings.inventory_approval_threshold} units requires approval."
        )
        return _decision(intent, DecisionType.approval_required, reasons, validated_fields, "medium")

    if intent.confidence < settings.min_confidence:
        return _decision(intent, DecisionType.approval_required, reasons, validated_fields, "medium")

    reasons.append("All deterministic checks passed.")
    return _decision(intent, DecisionType.allowed, reasons, validated_fields, "low")


def _decision(
    intent: ExtractedIntent,
    decision: DecisionType,
    reasons: list[str],
    validated_fields: dict[str, bool],
    risk_level: str,
) -> GuardrailDecision:
    next_step = {
        DecisionType.allowed: "execute_mock_erp",
        DecisionType.approval_required: "request_human_approval",
        DecisionType.blocked: "reject_request",
    }[decision]
    return GuardrailDecision(
        request_id=intent.request_id,
        decision=decision,
        reasons=reasons,
        requires_approval=decision == DecisionType.approval_required,
        risk_level=risk_level,
        validated_fields=validated_fields,
        next_step=next_step,
        extracted_intent=intent,
    )


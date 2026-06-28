from __future__ import annotations

from uuid import uuid4

from app.schemas import ActionType, ERPActionResult, ExtractedIntent


def run_vendor_payment(intent: ExtractedIntent) -> ERPActionResult:
    return ERPActionResult(
        request_id=intent.request_id,
        action_type=ActionType.vendor_payment,
        success=True,
        erp_reference=f"PAY-{uuid4().hex[:10].upper()}",
        message="Mock vendor payment accepted by ERP simulator.",
        payload={
            "vendor_id": intent.vendor_id,
            "amount": intent.amount,
            "currency": intent.currency or "USD",
            "status": "posted",
        },
    )


def run_inventory_update(intent: ExtractedIntent) -> ERPActionResult:
    return ERPActionResult(
        request_id=intent.request_id,
        action_type=ActionType.inventory_update,
        success=True,
        erp_reference=f"INV-{uuid4().hex[:10].upper()}",
        message="Mock inventory update accepted by ERP simulator.",
        payload={
            "inventory_item_id": intent.inventory_item_id,
            "inventory_delta": intent.inventory_delta,
            "status": "updated",
        },
    )


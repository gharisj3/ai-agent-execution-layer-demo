import hashlib
import hmac
import json
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException

from app.agent_service import extract_intent
from app.audit import fetch_audit_events, write_audit_event
from app.config import settings
from app.database import consume_approval, init_db, record_approval
from app.guardrails import evaluate_guardrails
from app.mock_erp import run_inventory_update, run_vendor_payment
from app.schemas import (
    ActionType,
    ApprovalDecisionRequest,
    ApprovalRequest,
    ApprovalStatus,
    AuditEvent,
    DecisionType,
    ERPActionResult,
    ExtractedIntent,
    GuardrailDecision,
    IncomingRequest,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AI Agent Execution Layer Demo",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-agent-execution-layer-demo"}


@app.post("/agent/extract", response_model=ExtractedIntent)
def agent_extract(payload: IncomingRequest) -> ExtractedIntent:
    return extract_intent(payload)


@app.post("/guardrails/evaluate", response_model=GuardrailDecision)
def guardrail_evaluate(payload: IncomingRequest) -> GuardrailDecision:
    intent = extract_intent(payload)
    return evaluate_guardrails(intent)


@app.post("/erp/vendor-payment", response_model=ERPActionResult)
def erp_vendor_payment(
    intent: ExtractedIntent, x_approval_id: str | None = Header(default=None)
) -> ERPActionResult:
    if intent.action_type != ActionType.vendor_payment:
        raise HTTPException(
            status_code=400, detail="Action type must be vendor_payment."
        )
    return _execute_checked(intent, x_approval_id)


@app.post("/erp/inventory-update", response_model=ERPActionResult)
def erp_inventory_update(
    intent: ExtractedIntent, x_approval_id: str | None = Header(default=None)
) -> ERPActionResult:
    if intent.action_type != ActionType.inventory_update:
        raise HTTPException(
            status_code=400, detail="Action type must be inventory_update."
        )
    return _execute_checked(intent, x_approval_id)


def _intent_hash(intent: ExtractedIntent) -> str:
    encoded = json.dumps(intent.model_dump(mode="json"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _execute_checked(
    intent: ExtractedIntent, approval_id: str | None
) -> ERPActionResult:
    decision = evaluate_guardrails(intent)
    if decision.decision == DecisionType.blocked:
        raise HTTPException(status_code=403, detail="Guardrails blocked this action.")
    if decision.requires_approval and (
        not isinstance(approval_id, str)
        or not consume_approval(approval_id, intent.request_id, _intent_hash(intent))
    ):
        raise HTTPException(
            status_code=403, detail="A matching unused approval is required."
        )
    operation = (
        run_vendor_payment
        if intent.action_type == ActionType.vendor_payment
        else run_inventory_update
    )
    result = operation(intent)
    write_audit_event(
        AuditEvent(
            request_id=intent.request_id,
            event_type="mock_execution",
            extracted_intent=intent.model_dump(mode="json"),
            validation_result=decision.model_dump(mode="json"),
            decision=decision.decision.value,
            approval_status="approved"
            if decision.requires_approval
            else "not_required",
            final_erp_response=result.model_dump(mode="json"),
        )
    )
    return result


@app.post("/approval/decide")
def approval_decide(
    payload: ApprovalDecisionRequest,
    x_reviewer_token: str | None = Header(default=None),
) -> dict[str, str]:
    if not settings.approval_api_key:
        raise HTTPException(
            status_code=503, detail="APPROVAL_API_KEY is not configured."
        )
    if not x_reviewer_token or not hmac.compare_digest(
        x_reviewer_token, settings.approval_api_key
    ):
        raise HTTPException(status_code=401, detail="Invalid reviewer token.")
    if payload.request_id != payload.intent.request_id:
        raise HTTPException(
            status_code=422, detail="Request and intent identifiers must match."
        )
    decision = evaluate_guardrails(payload.intent)
    if decision.decision == DecisionType.blocked:
        raise HTTPException(
            status_code=403, detail="Blocked actions cannot be approved."
        )
    if not decision.requires_approval:
        raise HTTPException(
            status_code=400, detail="This action does not require approval."
        )
    approval_id = str(uuid4())
    record_approval(
        approval_id,
        payload.request_id,
        _intent_hash(payload.intent),
        payload.decision,
        payload.approver,
        payload.comments,
    )
    write_audit_event(
        AuditEvent(
            request_id=payload.request_id,
            event_type="reviewer_decision",
            extracted_intent=payload.intent.model_dump(mode="json"),
            decision=payload.decision,
            approval_status="approved" if payload.decision == "approve" else "rejected",
            request_payload={
                "approval_id": approval_id,
                "approver": payload.approver,
                "comments": payload.comments,
            },
        )
    )
    return {
        "approval_id": approval_id,
        "approval_status": "approved" if payload.decision == "approve" else "rejected",
    }


@app.post("/approval/simulate")
def approval_simulate(payload: ApprovalRequest) -> dict[str, str | bool]:
    status = (
        ApprovalStatus.approved.value
        if payload.decision == "approve"
        else ApprovalStatus.rejected.value
    )
    return {
        "request_id": payload.request_id,
        "approval_status": status,
        "approver": payload.approver,
        "comments": payload.comments,
        "simulation_only": True,
    }


@app.get("/audit/events", response_model=list[AuditEvent])
def audit_events() -> list[AuditEvent]:
    return fetch_audit_events()


@app.post("/audit/events", response_model=AuditEvent)
def create_audit_event(payload: AuditEvent) -> AuditEvent:
    return write_audit_event(payload)

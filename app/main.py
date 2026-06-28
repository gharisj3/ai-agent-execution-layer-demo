from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.agent_service import extract_intent
from app.audit import fetch_audit_events, write_audit_event
from app.database import init_db
from app.guardrails import evaluate_guardrails
from app.mock_erp import run_inventory_update, run_vendor_payment
from app.schemas import (
    ActionType,
    ApprovalRequest,
    ApprovalStatus,
    AuditEvent,
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
def erp_vendor_payment(intent: ExtractedIntent) -> ERPActionResult:
    if intent.action_type != ActionType.vendor_payment:
        raise HTTPException(status_code=400, detail="Action type must be vendor_payment.")
    return run_vendor_payment(intent)


@app.post("/erp/inventory-update", response_model=ERPActionResult)
def erp_inventory_update(intent: ExtractedIntent) -> ERPActionResult:
    if intent.action_type != ActionType.inventory_update:
        raise HTTPException(status_code=400, detail="Action type must be inventory_update.")
    return run_inventory_update(intent)


@app.post("/approval/simulate")
def approval_simulate(payload: ApprovalRequest) -> dict[str, str]:
    status = ApprovalStatus.approved.value if payload.decision == "approve" else ApprovalStatus.rejected.value
    return {
        "request_id": payload.request_id,
        "approval_status": status,
        "approver": payload.approver,
        "comments": payload.comments,
    }


@app.get("/audit/events", response_model=list[AuditEvent])
def audit_events() -> list[AuditEvent]:
    return fetch_audit_events()


@app.post("/audit/events", response_model=AuditEvent)
def create_audit_event(payload: AuditEvent) -> AuditEvent:
    return write_audit_event(payload)


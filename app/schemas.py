from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ActionType(str, Enum):
    vendor_payment = "vendor_payment"
    inventory_update = "inventory_update"


class DecisionType(str, Enum):
    allowed = "allowed"
    approval_required = "approval_required"
    blocked = "blocked"


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    not_required = "not_required"


class IncomingRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    source: str = Field(default="n8n_webhook", min_length=2)
    raw_text: str = Field(min_length=10)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractedIntent(BaseModel):
    request_id: str
    action_type: ActionType
    vendor_id: str | None = None
    vendor_name: str | None = None
    vendor_status: Literal["active", "inactive", "unknown"] = "unknown"
    inventory_item_id: str | None = None
    inventory_delta: int | None = None
    amount: float | None = None
    currency: str | None = None
    reason: str = Field(default="unspecified")
    confidence: float = Field(ge=0.0, le=1.0)
    extracted_by: str = "mock"
    raw_text: str

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class GuardrailDecision(BaseModel):
    request_id: str
    decision: DecisionType
    reasons: list[str] = Field(default_factory=list)
    requires_approval: bool
    risk_level: Literal["low", "medium", "high"]
    validated_fields: dict[str, bool] = Field(default_factory=dict)
    next_step: str
    extracted_intent: ExtractedIntent


class ApprovalRequest(BaseModel):
    request_id: str
    approver: str = Field(default="demo.approver@example.com")
    decision: Literal["approve", "reject"]
    comments: str = Field(default="")


class ERPActionResult(BaseModel):
    request_id: str
    action_type: ActionType
    success: bool
    erp_reference: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    executed_at: datetime = Field(default_factory=utcnow)


class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str
    event_type: str
    request_payload: dict[str, Any] = Field(default_factory=dict)
    extracted_intent: dict[str, Any] = Field(default_factory=dict)
    validation_result: dict[str, Any] = Field(default_factory=dict)
    decision: str = ""
    approval_status: str = ApprovalStatus.pending.value
    final_erp_response: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)


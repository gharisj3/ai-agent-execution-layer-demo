from __future__ import annotations

import json
import re

import requests

from app.config import settings
from app.schemas import ActionType, ExtractedIntent, IncomingRequest


def extract_intent(payload: IncomingRequest) -> ExtractedIntent:
    if settings.mock_mode or settings.default_llm_provider == "mock":
        return _mock_extract(payload)
    if settings.default_llm_provider == "openai" and settings.openai_api_key:
        return _openai_extract(payload)
    if settings.default_llm_provider == "groq" and settings.groq_api_key:
        return _groq_extract(payload)
    return _mock_extract(payload)


def _mock_extract(payload: IncomingRequest) -> ExtractedIntent:
    text = payload.raw_text.lower()
    action_type = (
        ActionType.vendor_payment if "payment" in text or "vendor" in text else ActionType.inventory_update
    )
    vendor_status = "inactive" if "inactive" in text else "active" if "active" in text else "unknown"
    confidence = 0.91
    if "uncertain" in text or "maybe" in text:
        confidence = 0.62

    amount_match = re.search(r"(\d+(?:,\d{3})*(?:\.\d{1,2})?)", payload.raw_text)
    amount = float(amount_match.group(1).replace(",", "")) if amount_match and action_type == ActionType.vendor_payment else None

    units_match = re.search(r"(\d+)\s*(?:units|unit)", text)
    inventory_delta = int(units_match.group(1)) if units_match and action_type == ActionType.inventory_update else None

    vendor_id_match = re.search(r"(vendor[-_\s]?\d+|v-\d+)", text)
    item_id_match = re.search(r"(sku[-_\s]?\d+|item[-_\s]?\d+)", text)

    return ExtractedIntent(
        request_id=payload.request_id,
        action_type=action_type,
        vendor_id=vendor_id_match.group(1).replace(" ", "").upper() if vendor_id_match else payload.metadata.get("vendor_id"),
        vendor_name=payload.metadata.get("vendor_name"),
        vendor_status=vendor_status,
        inventory_item_id=item_id_match.group(1).replace(" ", "").upper() if item_id_match else payload.metadata.get("inventory_item_id"),
        inventory_delta=inventory_delta if inventory_delta is not None else payload.metadata.get("inventory_delta"),
        amount=amount if amount is not None else payload.metadata.get("amount"),
        currency=payload.metadata.get("currency", "USD"),
        reason=payload.metadata.get("reason", "Parsed from raw request"),
        confidence=payload.metadata.get("confidence", confidence),
        extracted_by="mock",
        raw_text=payload.raw_text,
    )


def _openai_extract(payload: IncomingRequest) -> ExtractedIntent:
    system_prompt = _provider_prompt(payload.raw_text)
    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.openai_model,
            "input": system_prompt,
        },
        timeout=20,
    )
    response.raise_for_status()
    content = response.json().get("output_text", "{}")
    data = json.loads(content)
    data["request_id"] = payload.request_id
    data["raw_text"] = payload.raw_text
    data["extracted_by"] = f"openai:{settings.openai_model}"
    return ExtractedIntent.model_validate(data)


def _groq_extract(payload: IncomingRequest) -> ExtractedIntent:
    system_prompt = _provider_prompt(payload.raw_text)
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.groq_model,
            "messages": [{"role": "user", "content": system_prompt}],
            "temperature": 0,
        },
        timeout=20,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    data = json.loads(content)
    data["request_id"] = payload.request_id
    data["raw_text"] = payload.raw_text
    data["extracted_by"] = f"groq:{settings.groq_model}"
    return ExtractedIntent.model_validate(data)


def _provider_prompt(raw_text: str) -> str:
    return (
        "Extract a JSON object for either vendor_payment or inventory_update. "
        "Return fields: action_type, vendor_id, vendor_name, vendor_status, "
        "inventory_item_id, inventory_delta, amount, currency, reason, confidence. "
        f"Source text: {raw_text}"
    )


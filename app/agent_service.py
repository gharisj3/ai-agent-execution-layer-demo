from __future__ import annotations

import json
import re

import requests
from pydantic import ValidationError

from app.config import settings
from app.schemas import ActionType, ExtractedIntent, IncomingRequest


class IntentExtractionError(RuntimeError):
    """Raised when a configured LLM provider cannot return valid intent."""


def extract_intent(payload: IncomingRequest) -> ExtractedIntent:
    if settings.mock_mode or settings.default_llm_provider == "mock":
        return _mock_extract(payload)
    if settings.default_llm_provider == "openai" and settings.openai_api_key:
        return _openai_extract(payload)
    if settings.default_llm_provider == "groq" and settings.groq_api_key:
        return _groq_extract(payload)
    raise IntentExtractionError(
        f"LLM provider '{settings.default_llm_provider}' is not available. "
        "Configure its API key or set MOCK_MODE=true and DEFAULT_LLM_PROVIDER=mock."
    )


def _mock_extract(payload: IncomingRequest) -> ExtractedIntent:
    text = payload.raw_text.lower()
    action_type = (
        ActionType.vendor_payment if "payment" in text or "vendor" in text else ActionType.inventory_update
    )
    detected_vendor_status = (
        "inactive" if "inactive" in text else "active" if "active" in text else "unknown"
    )
    vendor_status = payload.metadata.get("vendor_status", detected_vendor_status)
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
    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={"model": settings.openai_model, "input": system_prompt},
            timeout=20,
        )
        response.raise_for_status()
        body = response.json()
        content = body.get("output_text") or _openai_output_text(body)
        return _validate_provider_output(content, payload, f"openai:{settings.openai_model}")
    except (requests.RequestException, ValueError, KeyError, ValidationError) as exc:
        raise IntentExtractionError(f"OpenAI intent extraction failed: {exc}") from exc


def _groq_extract(payload: IncomingRequest) -> ExtractedIntent:
    system_prompt = _provider_prompt(payload.raw_text)
    try:
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
        return _validate_provider_output(content, payload, f"groq:{settings.groq_model}")
    except (requests.RequestException, ValueError, KeyError, IndexError, ValidationError) as exc:
        raise IntentExtractionError(f"Groq intent extraction failed: {exc}") from exc


def _openai_output_text(body: dict) -> str:
    for output_item in body.get("output", []):
        for content_item in output_item.get("content", []):
            if content_item.get("type") == "output_text" and content_item.get("text"):
                return content_item["text"]
    raise ValueError("provider response did not contain output text")


def _validate_provider_output(
    content: str, payload: IncomingRequest, extracted_by: str
) -> ExtractedIntent:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    data = json.loads(cleaned)
    data["request_id"] = payload.request_id
    data["raw_text"] = payload.raw_text
    data["extracted_by"] = extracted_by
    return ExtractedIntent.model_validate(data)


def _provider_prompt(raw_text: str) -> str:
    return (
        "Extract a JSON object for either vendor_payment or inventory_update. "
        "Return fields: action_type, vendor_id, vendor_name, vendor_status, "
        "inventory_item_id, inventory_delta, amount, currency, reason, confidence. "
        "Return JSON only, without Markdown fences. "
        f"Source text: {raw_text}"
    )

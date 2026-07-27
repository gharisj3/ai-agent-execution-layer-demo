# 3–5 Minute Portfolio Demo

## Preparation

Start the stack with `docker compose up --build`, import the [n8n workflow](../workflows/n8n-ai-execution-layer-demo.json), and open the API docs at `http://localhost:8000/docs`. The workflow uses `http://api:8000` because both services share the Compose network.

## 1. Frame the Architecture (30 seconds)

Show the workflow canvas and explain:

> The AI proposes structured intent. Pydantic validates its shape. Deterministic guardrails—not the LLM—authorize, escalate, or block the action. The ERP and approval steps are simulations.

Point out extraction, guardrails, three decision paths, mock ERP execution, and audit logging.

## 2. Allowed Inventory Update (45 seconds)

Extract and evaluate the low-risk request:

```bash
curl -X POST http://localhost:8000/agent/extract \
  -H "Content-Type: application/json" \
  -d @sample_payloads/low_risk_inventory_update.json

curl -X POST http://localhost:8000/guardrails/evaluate \
  -H "Content-Type: application/json" \
  -d @sample_payloads/low_risk_inventory_update.json
```

Highlight `inventory_item_id`, `inventory_delta`, `confidence`, and the `allowed` result. When sent through the active n8n webhook, it proceeds to the mock inventory endpoint and writes an audit event.

## 3. Approval-Required Payment (60 seconds)

```bash
curl -X POST http://localhost:8000/guardrails/evaluate \
  -H "Content-Type: application/json" \
  -d @sample_payloads/high_risk_vendor_payment.json
```

Show `approval_required` and the reason: USD 18,500 exceeds the default USD 10,000 threshold. In the n8n demo path, `/approval/simulate` returns approval and the mock payment runs.

Be explicit that automatic approval is a visual demo convenience. A real implementation needs authenticated, authorized human approval tied to the exact request.

## 4. Blocked Inactive Vendor (45 seconds)

```bash
curl -X POST http://localhost:8000/guardrails/evaluate \
  -H "Content-Type: application/json" \
  -d @sample_payloads/inactive_vendor_payment.json
```

Show `blocked`, the inactive-vendor reason, and `next_step: reject_request`. The blocked path never calls the mock ERP.

## 5. Audit and Closing Message (30 seconds)

```bash
curl http://localhost:8000/audit/events
```

Show that workflow-created audit events preserve the original request, extracted intent, decision, approval state, final result, and timestamp.

Close with:

> AI can reason. Deterministic systems should control execution. This demo is a reference architecture—not a production ERP connector, approval system, or payment engine.

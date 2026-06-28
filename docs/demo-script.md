# 3-Minute Demo Script

## Goal

Show that AI can help extract intent, but execution still belongs inside deterministic orchestration with approval and auditing.

## Steps

1. Start the API and n8n stack.
2. Open the n8n workflow and show the webhook trigger, extraction step, guardrail branch, approval branch, ERP call, and audit log call.
3. Send the low-risk inventory payload:

```bash
curl -X POST http://localhost:8000/agent/extract -H "Content-Type: application/json" -d @sample_payloads/low_risk_inventory_update.json
```

4. Explain the extracted fields and confidence score.
5. Send the same payload to `/guardrails/evaluate` and show the `allowed` decision.
6. Execute the inventory update against the mock ERP endpoint.
7. Show the resulting audit entry in `/audit/events`.
8. Send the high-risk vendor payment payload to `/guardrails/evaluate`.
9. Show that the result is `approval_required` because the amount is above threshold.
10. Call `/approval/simulate` with `approve`.
11. Execute the vendor payment endpoint.
12. Show the final audit trail and explain why this is safer than direct agent execution.


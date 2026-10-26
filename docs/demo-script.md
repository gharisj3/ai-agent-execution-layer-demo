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
10. Show that the n8n branch returns pending review without executing the high-risk action. A direct call to the ERP route is refused without a matching approval.
11. As a separate reviewer, call `/approval/decide` with `X-Reviewer-Token`, the same request ID, decision and exact extracted intent. The reviewer token must be configured locally as `APPROVAL_API_KEY` and must not be provided to the agent.
12. Execute the exact intent with `X-Approval-Id` from the decision response. Show the audit rows and that changing the intent or reusing the approval is refused. `/approval/simulate` is illustrative only and cannot authorize execution.

These are mock ERP operations. The shared reviewer token and caller-provided reviewer label do not replace production reviewer identity, trusted ERP state or audit integrity controls.


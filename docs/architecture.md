# Architecture Notes

## Intent

The demo separates reasoning from execution:

- FastAPI `/agent/extract` produces structured intent.
- Pydantic schemas enforce shape and typing.
- Guardrails evaluate business rules deterministically.
- n8n owns orchestration and branching.
- Mock ERP endpoints simulate controlled execution.
- Audit storage records what happened and why.

## Components

### API layer

- `app/main.py`: FastAPI routes and lifecycle setup
- `app/agent_service.py`: mock-first extraction with optional provider calls
- `app/guardrails.py`: deterministic control logic
- `app/mock_erp.py`: fake write endpoints
- `app/audit.py` and `app/database.py`: audit persistence

### Workflow layer

The n8n workflow provides:

- webhook intake
- one extraction-and-guardrail request to `/guardrails/evaluate`
- branch on `allowed`, `approval_required`, or `blocked`
- a pending-review response that does not execute high-risk actions
- mock ERP execution
- audit write-back

Separately, `/approval/decide` authenticates a configured reviewer token and records an intent-bound decision. ERP routes recheck guardrails and atomically consume a matching, unused approval for high-risk actions. `/approval/simulate` cannot produce that approval. Reviewer labels and intent business facts are still demo inputs; production identity and authoritative ERP lookups remain future work.

## Why n8n Matters Here

n8n is the visible control plane. It makes the path from request to action reviewable and deterministic. The LLM is treated as a reasoning component, not as the final authority.

## Suggested Extensions

- add SSO-backed human approvals
- add signed audit trails
- add RBAC-scoped action allow-lists
- replace mock ERP calls with adapter services behind service accounts


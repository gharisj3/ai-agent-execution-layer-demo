# Security Notes

## Scope

This repository demonstrates an execution-control pattern. It does not implement a complete security architecture and must not be connected directly to production ERP or financial systems.

The default mock mode needs no external credentials. `.env.example` contains empty provider-key values; keep real keys only in an untracked `.env` or a proper secrets manager.

## Production Considerations

A production implementation may require:

- authentication for users, services, and approvers
- authorization, RBAC, separation of duties, and action allow-lists
- secrets management and credential rotation
- TLS/encrypted transport and network isolation
- environment separation and hardened database access
- rate limiting, input limits, and abuse controls
- idempotency keys, transaction controls, and replay protection
- validated ERP master data and scoped service accounts
- durable approval records bound to request content
- audit retention, access controls, integrity/tamper resistance, and redaction
- monitoring, alerting, incident response, and recovery procedures
- data classification, minimization, retention, residency, and governance

## Current Demo Gaps

- API endpoints are unauthenticated.
- The n8n approval is automatically simulated.
- Mock ERP endpoints do not independently verify a guardrail decision.
- SQLite audit records are not encrypted or tamper-resistant.
- n8n uses local-demo credentials and HTTP endpoints.
- No real ERP, payment, identity, or compliance control is included.

Self-hosting does not automatically provide GDPR, SOC 2, or other regulatory compliance. Those outcomes depend on the complete implementation, organization, hosting, contracts, subprocessors, policies, and evidence.

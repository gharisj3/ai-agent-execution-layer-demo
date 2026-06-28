# Security Notes

## Important Disclaimer

This repository is a demo only. It should not be wired to a production ERP without additional controls.

## Minimum Controls Before Any Real ERP Use

- authenticated service-to-service calls
- role-based access control
- approval design aligned to finance and operations policy
- centralized logging and alerting
- rate limiting and replay protection
- secret rotation and secure storage
- environment separation
- vendor and item master-data validation
- stronger audit retention and tamper detection

## Compliance Note

Self-hosting can improve infrastructure control, but it does not automatically provide GDPR or local regulatory compliance. Compliance depends on deployment choices, contracts, subprocessors, retention rules, access design, and data handling processes.


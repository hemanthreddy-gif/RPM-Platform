# Lightweight Phase 0 threat model

This is an early design checklist, not a security certification. It uses STRIDE to identify where
later phases need controls and tests.

| Area | Main risk | Planned control | Evidence status |
| --- | --- | --- | --- |
| API identity | Someone impersonates a user | Password, MFA, token and role controls in Phase 2 | Pending |
| Patient data | A user reads another person's information | Relationship, consent, query filters and PostgreSQL RLS in Phase 2 | Pending |
| Observation intake | A request is replayed or altered | Scoped idempotency and provenance in Phase 3 | Pending |
| Alert path | An unsafe or nondeterministic decision | Pure rules package and import contract; rule tests in Phase 4 | Boundary in place; logic pending |
| AI path | Prompt injection or unsupported content | Fake default, no tool access, strict schemas and fact validation in Phases 7–8 | Pending |
| Images | Malicious or overly revealing upload | Private storage, type/size validation and re-encoding in Phase 7 | Pending |
| Background work | Accepted work is lost after a failure | Transactional outbox and persistent retries in Phases 3–4 | Pending |

Never treat an unimplemented future control as current protection.

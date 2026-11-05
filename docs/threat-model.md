# Phase 10 threat model — synthetic educational demo

This is a living engineering threat model, not a certification, privacy assessment, clinical
validation, or claim of regulatory compliance. It covers only synthetic data. Clinical decisions
remain in the deterministic `clinical_rules` package; AI, messaging, devices, and scanners do not
create clinical approval or human monitoring.

## Data-flow boundary

```text
Browser or paired device -> FastAPI auth/validation/authorization -> PostgreSQL transaction
  (observation, deterministic alert, audit, idempotency, outbox) -> Celery/Redis -> in-app delivery
Meal image -> validation/re-encode -> private S3-compatible object store -> authorised review
Verified facts -> optional AI provider -> validation/template fallback
FHIR export -> relationship/consent checks -> audited R4-subset JSON
```

## STRIDE analysis and evidence

| Flow / STRIDE threat | Control | Evidence / test |
| --- | --- | --- |
| Auth: spoofed credentials or account enumeration | Argon2id, generic login/reset failure, lockout, auth rate limit, MFA for privileged roles | `test_identity_security.py`; Phase 10 rate-limiter test |
| Auth: replayed or stolen refresh/access token | Rotating hashed refresh tokens, refresh revocation, JWT expiry, `token_valid_after` invalidation after reset/logout | identity service/router; migration `0012_phase10_security`; focused identity regression suite |
| API: tampered/cross-patient request | JWT role checks, relationship/consent checks, transaction-local RLS, typed request schemas | Phase 2–9 PostgreSQL access tests; import contract |
| Ingestion: duplicate, flood, or repudiated reading | Actor/device-scoped idempotency, immutable observations, audit in same transaction, rate limits | Phase 3/9 idempotency acceptance tests; Phase 10 limiter test |
| Device: spoofed paired device | Hash-only pairing token scoped to URL device, device source/provenance, no patient-data read capability | `test_phase9_interop.py`; device PostgreSQL acceptance tests |
| Alerts: altered/nondeterministic decision | Pure deterministic evaluator, isolated imports, atomic alert/event/outbox persistence | clinical boundary tests; Phase 4 atomicity suite |
| Worker: lost/replayed delivery or Redis outage | PostgreSQL outbox, idempotent delivery, retry/dead-letter state, late acknowledgements, `/ready` visible Redis status | Phase 4 failure/dead-letter tests; Phase 10 retry configuration and readiness test |
| Object storage: malicious upload or disclosure | JPEG/PNG allow-list, byte/pixel limits, Pillow verify/re-encode strips metadata, private bucket, authorised read, opaque 503 | `test_meal_photo_review.py` |
| AI: injected input or unsafe/fabricated prose | Fake by default, no tools/DB, facts-only packet, validator, deterministic patient template fallback | Phase 8 red-team/validator tests |
| Export: disclosure or misleading FHIR output | Relationship/consent/audit checks; restricted R4 subset; uncoded glucose omitted rather than guessed | Phase 9 FHIR HTTP/integration tests |
| API/UI: browser injection, framing, data cache | Explicit CORS allow-list, strict API CSP, no-frame/nosniff/referrer/permission headers, `no-store` | `test_phase10_hardening.py`; ZAP baseline in CI |
| Supply chain/secrets | Locked dependencies, pip-audit, npm audit, Gitleaks in CI | `.github/workflows/ci.yml`; see dated scan exception until remote CI evidence exists |
| Availability: database/broker/storage/provider failure hidden from operators | Liveness separate from `/ready`; visible object-store error; provider/template fallback; durable alert path independent of Redis | `/ready` Phase 10 regression; meal storage and writer fallback tests |

## Open exceptions

The owned impacts, compensating controls, and expiry dates are in
[`security-exceptions.md`](security-exceptions.md). Expired or unexplained exceptions cannot pass
a public-demo release gate.

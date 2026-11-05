# RPM Platform architecture

## Status and purpose

This is the working architecture record for a local, synthetic-data-only educational prototype.
The repository implements synthetic patient and physician workflows through Phase 11. Human
evaluation and release-gate work remain open; no clinical validation is claimed.

## Planned shape

The project will be a modular monolith:

```text
Patient and physician web app      Device simulator
                 \                 /
                  authenticated API
                         |
       validation + authorization + audit logging
                         |
        observation service -> pure clinical rules
                         |
 PostgreSQL transaction: observation, alert, idempotency,
                  audit, and outbox event
                         |
        persistent workers -> local notification sinks

Optional AI path, kept separate:
private image or verified facts -> provider -> strict validation
              -> patient confirmation or physician review
```

Implemented foundation components are a Next.js/TypeScript frontend with a backend-health page,
FastAPI/Python `/health` and `/api/v1/ping` endpoints, a fake AI provider placeholder, and Docker
Compose configuration for PostgreSQL 16, Redis, Celery, SeaweedFS (S3-compatible local object
storage), MailHog, backend, and frontend.
The schema, synthetic records, authorization and audit paths are implemented; see [progress](PROGRESS.md) for verification and gaps.

## Non-negotiable boundaries

| Area | Decision |
| --- | --- |
| Clinical alerts | Only a pure deterministic rules engine can decide them; AI cannot participate. |
| Data integrity | Observation, alert, audit, idempotency response, and outbox write share one database transaction. |
| AI | Default is `AI_PROVIDER=fake`; it is optional, has no database/shell/tool access, and its output is untrusted. |
| Nutrition | Program code calculates nutrients from a recorded food dataset/version; AI may only estimate food/portion. |
| Permissions | Every patient-data read/write is authorized and audited. Physician access needs an active relationship and purpose-specific consent; administrators have no clinical reads. |
| Data history | Observations are immutable. Corrections append a superseding observation, retaining original units and times. |
| Module ownership | Modules own tables and use services/DTOs; they do not import another module's ORM models. Only audit writes `audit_log`. |

## Primary runtime flows

1. A patient or device submits a reading. The API authenticates, validates, and authorizes it;
   the rules engine receives explicit history and evaluation time; all durable records commit
   together. Synthetic-demo urgent guidance is returned synchronously, while durable outbox workers
   perform later delivery/retry work.
2. A meal image is validated and stored privately. An authorized physician can add a comment.
   This selected workflow does not recognize foods, estimate portions or calculate nutrients.
3. Analytics make a typed facts packet from stored sources. An optional provider can draft
   physician-only prose; validation checks its claim references. Patient-visible facts are
   deterministically rendered, and provider failure falls back to templates.

Phase 8 currently implements this flow only for authorized observation and explicit
self-reported-dose sources. The facts packet records source identifiers, time window, sample size,
units, and insufficient-data state. It makes no meal/nutrition inference in the selected workflow. Patient text is a deterministic source-linked template; no provider
text is patient-visible. Real provider-backed physician prose and asynchronous publication remain
deferred pending a selected provider and a later bounded slice.

Phase 9 adds a device-token boundary that authenticates a paired device before server-side code
enters a trusted worker database context solely to reuse the existing observation/alert transaction.
Tokens are stored as hashes and are scoped to one device; they do not grant patient-data reads.
Messaging is a separate consent-gated, audited, non-emergency path and cannot create clinical
alerts. The FHIR interface is read-only, explicitly limited to a synthetically mapped R4 subset,
and omits glucose records without recorded specimen/coding provenance rather than guessing codes.

## Planned module boundaries

- `clinical_rules`: standalone pure Python models, evaluator, and versioned rules.
- Domain modules: identity, patients, observations, targets, alerts, medications, nutrition,
  messaging, insights, devices, FHIR, and audit.
- `ai`: provider adapters, food pipeline, analytics, and summary writer. It cannot write clinical
  tables.
- `workers`: durable outbox consumers and scheduled jobs; authorization/consent is rechecked.

## Known gaps and decisions still needed

- No clinician has approved thresholds, message text, or demo-rule activation. Do not imply one.
- The chosen meal-photo review workflow has no food recognition or nutrition calculations.
- No provider/model is selected because the fake provider is sufficient for development and tests.
- Public-demo isolation, reset safeguards, deployment, release-gate verification, usability testing
  and clinician/faculty feedback remain open. See [progress](PROGRESS.md).

## ADR status

- [ADR 001](adr/001-modular-monolith.md): modular monolith.
- [ADR 002](adr/002-postgres-before-timescaledb.md): PostgreSQL before TimescaleDB.
- [ADR 003](adr/003-dependency-baselines.md): Phase 0 runtime and fake-AI baselines.
- [ADR 004](adr/004-local-object-storage.md): local S3-compatible storage deviation.
- [ADR 005](adr/005-oidc-migration-path.md): replace local prototype identity before non-demo use.
- [ADR 006](adr/006-medication-provenance-and-self-report.md): preserve physician-authored
  medication versions and distinguish schedules from patient self-reports.

- [ADR 007](adr/007-demo-deployment-boundary.md): separate image candidates from public deployment.

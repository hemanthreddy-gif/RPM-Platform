# Phase 3 plan — observations and monitoring targets

## Scope

Implement the authenticated, audited backend ingestion/read/correction/target paths for synthetic
glucose, blood pressure, heart rate, and SpO2 observations. Alert evaluation is deliberately
deferred to Phase 4; this phase writes a durable `ObservationRecorded` outbox event only.

## Steps

1. Add typed schemas and pure validation/conversion helpers, including explicit glucose unit
   conversion and measurement-time/quality rules.
2. Add observation service and routes with actor-scoped idempotency records, response replay,
   immutable correction records, filtered/paginated reads, and daily aggregate calculations.
3. Add physician-only versioned targets, with relationship/consent enforcement and patient
   read access.
4. Audit each patient-data read/write and persist the observation, idempotency response, audit
   entry, and outbox event in one transaction.
5. Add focused unit/API tests and run the Phase 3 backend checks. Database-only concurrency and
   RLS tests remain contingent on the local PostgreSQL service.

## Safety decisions

- The authenticated patient identity is the only manual-entry provenance; request fields cannot
  claim device or imported sources.
- Observations are never updated. A correction appends a new record linked by `supersedes_id`.
- All clinical rule/alert work is deferred to Phase 4; no thresholds or guidance are introduced.
- Unusual-value handling is a validation-quality flag only, never a clinical assessment.

# Phase 4 plan — deterministic clinical rules, alerts, and notifications

## Scope

Implement only deterministic, synthetic-demo alert evaluation and alert lifecycle infrastructure.
The rules remain unreviewed illustrative fixtures and are not clinical guidance. No AI participates.

## Rules and boundary tests

| Rule | Required boundaries |
| --- | --- |
| GLU_LOW_L2 | 53, 54, 55 mg/dL |
| GLU_LOW_L1 | 53, 54, 69, 70 mg/dL; L2 suppression |
| GLU_HIGH_URGENT | 299, 300, 301 mg/dL |
| BP_CRISIS | systolic 179/180; diastolic 119/120 |
| BP_LOW | systolic 89/90; dizziness/fainting escalation |
| SPO2_LOW | 89/90/91/92 percent |

## Steps

1. Create isolated Pydantic models, strict YAML loader, and pure evaluator under `clinical_rules`.
2. Add unreviewed, demo-only versioned fixture rules and reviewed-style deterministic message keys.
3. Add alert persistence/lifecycle/deduplication/outbox service that runs inside the observation
   transaction, plus notification adapters and retry state.
4. Wire synchronous single-reading evaluation into ingestion and physician lifecycle APIs with
   authorization/audit checks; retain scheduled pattern/no-data work for workers.
5. Add boundary, lifecycle, dedupe, import-isolation, golden-fixture, and retry tests. Run mutation
   testing and all required local checks; record actual results and unresolved database evidence.

## Completion work log (2026-11-04)

1. Complete pure target-pattern evaluation (fasting glucose and component-specific BP averages)
   and scheduled orchestration without adding clinical thresholds.
2. Make notification attempts retryable, bounded, dead-lettered, and idempotent at the database
   boundary; retain every attempt as durable state.
3. Add opt-in `rpm_test` PostgreSQL integration coverage for atomicity, idempotency, lifecycle,
   escalation, delivery retry/dead-letter, RLS, and immutable correction history.
4. Run the required static, unit, PostgreSQL, and mutation checks; record only observed evidence
   in the progress and safety-case documents.

## Safety decisions

- Every rule has `requires_clinician_approval: true`; only explicit synthetic demo mode activates it.
- Rules receive observation/history/context/evaluation time explicitly and perform no I/O.
- Urgent guidance includes the permanent non-emergency-service limitation.
- Missing clinician review and database-backed concurrency/retry evidence block Phase 4 completion.

## Handoff status (2026-11-04)

The implementation and database acceptance slice is complete. Migration `0005_alert_delivery_integrity`
is applied to `rpm` and `rpm_test`; all 7 PostgreSQL integration tests pass, and the full backend
suite passes with 45 tests. Clinical-rules coverage is 96%. The repository-wide coverage result is
63%, below the 80% target, and mutmut produced no usable score in the disposable Linux run, so
those remain tracked quality follow-ups rather than claimed evidence. Phase 5 may proceed while
preserving the synthetic-only boundary and the explicit `requires_clinician_approval` review gap.

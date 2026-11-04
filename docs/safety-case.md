# Initial hazard log

This early hazard log documents gaps before they are implemented. It does not claim clinical
validation or regulatory compliance.

| Hazard | Cause | Planned control | Evidence / current gap | Residual risk owner |
| --- | --- | --- | --- | --- |
| Unsafe alert | AI or hidden logic makes a decision | Pure deterministic clinical rules only | Import boundary exists; rules not implemented until Phase 4 | Project owner |
| Missed alert | Rule or delivery failure | Pure evaluator, boundary tests, transactional alert/event/outbox/audit writes, persistent retry and dead-letter state | `backend/tests/test_clinical_rule_evaluator.py`; `backend/tests/test_phase4_postgres_integration.py` | Project owner; fixtures remain unreviewed |
| Wrong-patient data | Broken authorization | Roles, active relationship, purpose-specific consent, RLS, audit, and restricted worker identity | `test_worker_physician_consent_and_admin_rls` in `backend/tests/test_phase4_postgres_integration.py` | Project owner; local synthetic DB only |
| Unsafe AI text | Fabricated or injected output | Fake default, schema/fact validation, physician review | AI feature not implemented | Project owner |
| Incorrect nutrition estimate | Model or dataset error | Code calculation, range, patient confirmation | Data not licensed/supplied | Project owner |
| Stale data treated as current | Missing timestamp/data-age display | UTC provenance and UI age indicator | Not implemented | Project owner |

## Phase 4 verification record

- Clinical-rules unit and boundary tests pass locally, including explicit fasting-glucose and
  blood-pressure target-pattern edge cases. The package remains free of application, database,
  clock, worker, and AI imports.
- Mutation testing was attempted on 2026-11-04 with locked mutmut 3.8.1 in a disposable Linux
  container. The 26 clinical-rules tests passed, but mutmut reported `0 files mutated, 0 ignored,
  4 unmodified` and stopped because it found no test case for a generated mutant. No mutation
  score or survivor claim is made; the runner's source-copy isolation needs investigation before
  this can count as mutation evidence. Native Windows mutmut remains unsupported.
- PostgreSQL integration tests are opt-in and require `DATABASE_URL` ending in `/rpm_test`.
  The test module covers atomic trigger/outbox/audit writes, lifecycle transitions, retry and
  dead-letter state, 30-minute escalation, worker/physician/admin access, correction history,
  and concurrent idempotency. After applying migration `0005_alert_delivery_integrity`, all 7
  integration tests passed against the disposable local database.
- Phase 4 fixtures remain synthetic, unreviewed, and gated by `requires_clinician_approval: true`;
  no clinical validation or clinician approval is claimed.

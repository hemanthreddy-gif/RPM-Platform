# Phase 5 plan — synthetic medication schedules and self-reported adherence

## Scope

Implement the medication module only for the synthetic educational demo.  Prescription versions
are physician-authored records, while dose status is explicitly patient self-report.  This phase
does not provide medication-change advice, clinical validation, clinician approval of alert
fixtures, production deployment, nutrition, or AI-driven decisions.

## Steps

1. Add an additive PostgreSQL migration for versioned medication schedules, dose-event source and
   reporting provenance, generic medication-reminder delivery state, and RLS/trigger protections.
2. Implement typed medication API contracts and a service for physician-only version creation,
   patient/physician reads, self-reported dose updates, audited access, and explicitly labelled
   7/14/30-day adherence summaries.
3. Add deterministic, timezone-aware worker functions that generate the next seven days of doses
   idempotently, supersede obsolete pending schedules on a change, mark overdue reports unknown,
   and send only allowlisted safety-warning reminder templates during the configured late window.
4. Add the non-threshold `MED_MISSED_PATTERN` synthetic fixture and pass self-reported missed
   events through the existing pure pattern evaluator.  It creates no medication recommendation.
5. Add unit and PostgreSQL integration coverage for Asia/Kolkata conversion, idempotent generation,
   mid-window schedule changes, patient write denial, self-report labelling, template provenance,
   and the isolated pattern path.  Run the required checks and record exact evidence.

## Quality debt carried from Phase 4

Repository-wide test coverage was 63%, below the 80% target, although `clinical_rules` coverage
was 96%.  The locked mutmut run did not produce a usable score (`0 files mutated, 4 unmodified`).
These remain explicit follow-up work and are not represented as resolved by Phase 5.

## Safety decisions

- A missing report is `pending` or subsequently `unknown`, never `missed`.
- Only a patient report can set `taken`, `missed`, or `skipped`; it records actor and time.
- Reminder content is an allowlisted synthetic-demo safety warning with source/template provenance,
  not generated medication advice.  AI is not involved.
- `MED_MISSED_PATTERN` responds only to an actual self-reported missed event and carries the
  existing synthetic-demo and `requires_clinician_approval` gates; it defines no threshold.

## Functional acceptance evidence (2026-11-04)

- Migration `0006_medication_adherence` was reviewed by rendering the SQL, then applied only to
  the disposable local synthetic `rpm` and `rpm_test` databases. Both report migration head.
- The five Phase 5 PostgreSQL tests pass against `rpm_test`: Asia/Kolkata UTC+05:30 conversion,
  idempotent dose generation, a mid-window schedule change, overdue-to-unknown behavior, and
  patient create/edit denial. Additional integration coverage verifies physician-authored version
  provenance, a patient self-report with a concern flag, the synthetic missed-report rule path,
  self-reported adherence, and sent/expired reminder delivery evidence.
- Full backend verification against `rpm_test` passed with 55 tests. The required 80% repository
  coverage gate remains open at 65%; `clinical_rules` is 96%. Mutmut still has no valid score.
  Therefore functional Phase 5 acceptance is complete, but the repository-wide quality gate is
  not complete and remains tracked follow-up work.

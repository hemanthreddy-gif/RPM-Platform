# ADR 006: Preserve medication provenance and separate schedules from self-report

## Status

Accepted, 2026-11-04, for the synthetic educational demo only.

## Decision

Medication rows retain the current physician-authored synthetic prescription, while immutable
`medication_versions` retain every authored payload and `medication_schedules` retain every
effective schedule. The worker generates future `dose_events` from the schedule in the patient's
IANA timezone. A schedule change supersedes only future, unresolved generated events; it never
rewrites a patient report.

`taken`, `missed`, and `skipped` are patient self-reports with actor, timestamp, and optional
concern-flag provenance. An unreported scheduled dose stays `pending` and later becomes `unknown`;
it is never inferred to be `missed`. Adherence percentages use only reported statuses and are
labelled `self_reported`.

Reminder content uses a technical allowlist of non-advisory synthetic safety-warning template IDs
and records the template source. The application and AI do not generate medication-change advice.

## Consequences

The phase adds worker/RLS/trigger complexity but avoids silently treating absence as nonadherence.
The `MED_MISSED_PATTERN` fixture can react only to an actual self-reported missed dose and remains
synthetic, unreviewed, and behind the existing demo switch. This decision is not a clinical
validation, clinician approval, medication recommendation, or production prescribing workflow.

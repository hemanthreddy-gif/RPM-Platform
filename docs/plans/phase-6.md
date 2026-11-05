# Phase 6 plan — patient and physician core flows

## Scope and safety

Build a usable frontend only for implemented synthetic-demo capabilities: identity, observations,
alerts, targets, and self-reported medication adherence. Keep nutrition and insights as explicit
placeholders. The permanent synthetic-data, non-emergency, and no-real-time-supervision notices
remain visible. No UI invents clinical guidance, approval, provider monitoring, AI decisions, or
medication-change advice.

Phase 4–5 quality debt carries forward unchanged: repository coverage is 65% against the 80%
target and mutmut has no usable score. That debt is not represented as resolved by this phase.

## Screens

| Role | URL | Content |
| --- | --- | --- |
| Public | `/login` | Login, MFA continuation, and synthetic-demo notice. |
| Patient | `/patient` | Latest readings, active alert state, medication summary, and safe logging actions. |
| Patient | `/patient/log` | Accessible glucose/BP/heart-rate/SpO2 forms and offline queue state. |
| Patient | `/patient/trends` | 7/30-day visual and table alternatives, targets, data age, and provenance. |
| Patient | `/patient/medications`, `/patient/alerts`, `/patient/settings` | Self-reporting, alert status, consents/privacy placeholders. |
| Physician | `/physician` | Alert/data-age ordered overview and directory controls. |
| Physician | `/physician/patients/[id]` | Overview, monitoring, medications, alerts, and nutrition/insights placeholders. |
| Admin | `/admin` | Explicitly no clinical-data access. |

## Component structure

`components/app-shell` provides role-aware navigation and permanent safety notice.
`components/observations` owns record forms, trend/table alternatives, age/provenance labels, and
offline submission status. `components/medications` renders self-report actions without advice.
`components/alerts` renders only server-supplied guidance. `lib/auth` owns token lifecycle and
role guarding; `lib/offline` owns identity-bound IndexedDB queue records and idempotency keys.
`lib/api/generated` is regenerated from the backend OpenAPI spec by an npm script; hand-written
clients only adapt generated endpoint types to UI needs.

## Steps

1. Generate typed API contracts from the backend OpenAPI spec; implement token storage, refresh,
   logout, MFA continuation, and role-bound route guards.
2. Build the mobile patient flows, accessible forms, API feedback states, and an identity-isolated
   observation queue with explicit offline safety language.
3. Build desktop physician overview/detail flows, target/editor and alert lifecycle controls, with
   data age and provenance visible in all monitoring views.
4. Add PWA manifest/service-worker boundaries that never cache authenticated API responses or
   signed images, then add tests for queue reconnect, expiry, and account switch.
5. Add component/accessibility tests and a real Playwright patient-to-physician scenario against
   configured synthetic services. Verify at 360 px and record only observed results.

## Implementation evidence (2026-11-04)

- The local Compose demo enables only deterministic synthetic-rule fixtures. Its backend image now
  includes those fixtures; no clinical validation or clinician approval is implied.
- `/patients/me`, `/physician/patients`, patient detail reads, and alert lifecycle data are live,
  authorized, RLS-scoped, and audited. The worklist requires an active relationship and monitoring
  consent; administrators remain excluded from clinical reads.
- The Playwright fixture creates a distinct fabricated `example.com` identity on each run, labels
  its display name and registration identifier as synthetic, grants monitoring consent, and creates
  the relationship through normal APIs. No fixture is a real person.
- `npm --prefix frontend run test:e2e` passed (1 test, 5.3s) against local Compose services. It
  verifies an unreviewed 53 mg/dL synthetic fixture value (`<54` fixture boundary, not clinical
  advice), server wording, 360px no-overflow, Axe no violations, physician acknowledgement, and
  patient-visible `acknowledged` status.

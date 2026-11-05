# Phase 9 plan — controlled communication, device ingestion, and FHIR R4 subset

## Scope and safety boundary

This Phase 9 slice implements the backend interoperability boundary for the synthetic educational
demo. It adds only patient–physician communication, paired-device ingestion, a local simulator,
and read-only FHIR R4 JSON mapping. It does not claim clinical interoperability, device
certification, real-time monitoring, clinician review, or terminology completeness. The permanent
synthetic-demo and non-emergency boundaries apply to every new surface.

The Phase 4–8 coverage and mutation-test debt remains open. The missing licensed nutrition data
continues to block meal-derived analytics; Phase 9 does not alter that decision.

## Authorized implementation

1. Create private patient–physician message threads only after monitoring relationship/consent
   authorization; persist messages/read receipts with RLS, audit all reads/writes, return unread
   counts, and add a fixed configurable response-time/non-emergency disclosure. Appointment
   requests are structured non-clinical messages. No keyword check can create an alert until an
   explicitly reviewed clinical rule exists.
2. Add device records with one-time pairing tokens stored only as hashes; device readings use a
   scoped token, a device-owned idempotency key, UTC receipt time, authenticated `device` source,
   and the same structural validation, deterministic alert evaluator, atomic audit/outbox path as
   manual observations. Duplicate/out-of-order sends must retain data integrity; late sync is
   provenance, not a diagnosis.
3. Add a local `tools/device_simulator` CLI for synthetic glucose and BP payloads, including
   jitter, duplicates, out-of-order sends, and offline-burst replay. It uses no real identity,
   hardware, or credential default.
4. Add read-only FHIR R4 JSON mappers/endpoints for patient, practitioner, supported observations,
   medication request/statement, and patient Bundle. The supported mapping accepts only explicit
   recorded coding metadata for glucose; it will not invent a generic LOINC code or specimen/method.
   BP uses a documented panel/component subset. A strict local R4-subset validator verifies
   resource type, version, required fields, references, and allowed coding/unit combinations;
   no claim of full FHIR validation is made.

## Explicitly deferred

- A browser end-to-end scenario for pairing, messaging, and stale-device presentation; the focused
  component/API paths are implemented, but this workflow is not browser-automated.
- Keyword-driven clinical attention banners or message-triggered alert rules, because no reviewed
  message-event clinical rule exists.
- Device vendor integrations, device registration beyond the authenticated local API, and push/email
  delivery.
- Generic glucose coding, terminology-service validation, and any assertion of full FHIR R4
  conformance. Uncoded observations remain visible through the native API but are excluded from
  FHIR export with an explicit reason.

## Verification plan

Add unit tests for token hashing, duplicate/reordered payload handling, safe simulator construction,
message access controls, mapper/validator behavior, and synthetic round trips. Render the migration
SQL; run PostgreSQL RLS and HTTP/device acceptance only against the documented disposable synthetic
database. Finish with backend static checks and full pytest, recording unrun checks exactly.

## Implementation evidence (2026-11-05)

- Added `0010_phase9_interop`, consent-scoped message-thread/read-receipt tables
  and hashed paired-device token metadata. It is applied, with `0009` and audit-owned
  `0011_audit_append`, to the disposable synthetic `rpm` and `rpm_test` databases.
- Added audited message-thread, message, read-receipt, unread-count, device-pairing, device-list,
  device-reading, and limited FHIR R4 subset endpoints. Device readings use `ObservationCreate`
  conversion and the established synchronous evaluator/outbox path; their idempotency scope is the
  authenticated device ID. The raw pairing token is returned once at pairing time and is not stored.
- Added `tools/device_simulator`, which requires caller-supplied local device credentials and can
  generate synthetic duplicate/reordered/offline-burst payloads. It has no real-device integration.
- Focused unit tests passed (4 tests) for explicit glucose coding, BP components, malformed device
  payloads, and message validation. Static checks, migration rendering, and full backend pytest
  passed; the full suite reported 108 passed, 16 database-integration skips, 55% overall coverage,
  and 96% clinical-rules coverage. The later disposable-PostgreSQL acceptance run covers duplicate
  and reordered device ingestion and unrelated-physician message denial.

## Completion continuation (2026-11-05)

- Added the patient Settings device/message UI and a physician monitoring presentation of each
  authorized device's last receipt time. A missing receipt is visibly labelled “No device sync
  recorded — review data age.” This is informational only: it sets no clinical stale threshold,
  does not create an alert, and does not imply clinician review.
- Added a FastAPI `TestClient` round trip using a signed synthetic patient identity and the
  disposable PostgreSQL session. It authorizes and audits `Patient`, `Observation?patient=`, and
  `Patient/$everything` HTTP reads, checks returned resource IDs/types, and exercises the actual
  R4-subset serialization path. The optional Observation date filter now omits its bind parameter
  when absent; medication export uses the owned `start_date` rather than a nonexistent timestamp.
- `test_phase9_postgres_integration.py` passes 3 tests with `DATABASE_URL` set to `rpm_test`.
  Backend Ruff and mypy pass; frontend lint, typecheck, and Vitest pass (3 files, 4 tests).
  A non-IP test-client host is intentionally omitted from the audit IP field; valid IP literals
  continue to be retained.
- The complete backend command passes with `108 passed, 19 skipped`, 55% overall coverage, and
  96% clinical-rules coverage. The default `npm --prefix frontend run build` is blocked in this
  Windows environment by a Next 16.4.5 Turbopack CSS-worker process error while processing
  `app/globals.css`; the equivalent `npm --prefix frontend run build -- --webpack` production build
  succeeds. Lint, typecheck, and Vitest remain green. The Turbopack failure is not reported as a
  successful default build.

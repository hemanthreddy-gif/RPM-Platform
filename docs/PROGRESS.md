# Build progress

- Active phase / bounded slice: Phase 5 synthetic medication versions, scheduled-dose generation,
  reminders, and explicitly self-reported adherence. Phase 4 implementation and PostgreSQL
  evidence are preserved; its repository-wide coverage and mutation-score gaps remain tracked
  quality debt. Qualified clinical review remains absent.
- Branch and last verified commit: Local repository initialized on 2026-11-04. No commit, remote,
  branch selection, push, or tag was requested.
- Completed behaviour and key files: FastAPI `/health` and `/api/v1/ping`; request-id JSON logging;
  a default `AI_PROVIDER=fake`; a Next.js health page and route-group placeholders; Docker Compose
  configuration using SeaweedFS for free local S3-compatible storage; backend/frontend lock files;
  import-linter contract; CI; pre-commit configuration;
  Phase 0 ADRs; lightweight threat model and hazard log; and a disposable backup/restore script.
  Phase 1 adds Alembic migration `0001_initial_schema`, PostgreSQL immutability/append-only
  triggers, runtime-role restrictions, deterministic synthetic cohort tooling, and its named edge
  scenarios. The user applied the migration locally and seeded 50 synthetic patients with seed 42
  and anchor date 2026-10-01 (SHA-256
  `41307ffccff3f2afebb8d9289af06ac5361ee9d9a6d14bb932e306a56e5a747f`).
  The user also verified the observation immutability trigger locally: an attempted `UPDATE`
  returned `observations are immutable; append a superseding record instead`.
  The user verified the audit-log trigger in a rolled-back transaction: the temporary insert
  succeeded and its attempted update returned `audit_log is append-only`; no test audit record
  was retained.
  Phase 2 adds migration `0002_identity_security`, patient-only registration, trusted privileged
  provisioning, Argon2id passwords, JWT access tokens, hashed rotating refresh tokens, lockout,
  TOTP enrollment, consent APIs, audited relationship assignment, object authorization, baseline
  auth rate limiting/CORS controls, and [ADR 005](adr/005-oidc-migration-path.md). No UI,
  observations, alerts, or clinical rules were added.
  Phase 3 now adds `0003_observation_target_rls`, typed structural observation validation,
  glucose mmol/L-to-mg/dL conversion (18.016), manual authenticated provenance, actor-scoped
  idempotency replay/conflict handling, immutable corrections, durable `ObservationRecorded`
  outbox records, audited observation creation/read/correction, and basic authorized history
  reads. Alert evaluation is explicitly deferred to Phase 4.
  It also now provides physician-only, relationship/consent-gated, append-only target versions;
  patient/physician latest-target reads; and UTC daily min/max/mean/count aggregation for scalar
  observation types. Blood-pressure components remain source-record fields rather than being
  reduced to an invented scalar aggregate. Observation history now has bounded offset pagination,
  type and offset-aware date filters, and supersession-aware reads. No default target range was
  invented because none is clinician-reviewed; an absent patient target remains absent.
  Concurrent idempotency-key conflicts roll back the losing observation/audit/outbox transaction
  and replay the winning response. A target-based sampled-reading percentage endpoint rejects
  absent or incomplete physician-defined target ranges rather than manufacturing one.
  Phase 4 adds an isolated Pydantic clinical-rules package, strict external YAML fixture loader,
  explicit-evaluation-time deterministic evaluator, and five clearly unreviewed synthetic-demo
  fixtures. All retain `requires_clinician_approval: true`; no fixture is an approved threshold or
  real clinical guidance. Boundary tests cover the implemented glucose rules and prove the package
  imports no application/AI infrastructure. Alert persistence, lifecycle APIs, notifications,
  scheduled pattern/no-data work are implemented; mutation testing remains unavailable in native
  Windows.
  The synchronous single-reading path now evaluates the explicit synthetic-demo switch only,
  persists alert trigger/deduplication events and notification outbox records in the observation
  transaction, returns deterministic urgent guidance carrying the non-emergency-service notice,
  and provides audited, relationship-gated physician acknowledge/resolve endpoints. Notification
  delivery adapters, scheduled pattern/no-data evaluation, escalation execution, and the required
  database safety tests are implemented and covered by the PostgreSQL integration suite.
  The alert outbox now has an idempotent local in-app delivery worker, durable delivery-attempt and
  failure/retry state, and a scheduled worker that escalates unacknowledged synthetic urgent alerts
  after the fixture's 30-minute timeline, preserving an alert event and a new outbox request.
  Pattern/no-data rules, dead-letter completion policy, and database-backed safety/concurrency tests
  are verified. Mutation tooling produced no usable score and remains a follow-up item.
- Acceptance checks: `docker compose config --quiet` passed. A temporary
  `clinical_rules -> ai` import made `lint-imports` fail, then passed after removal. The user ran
  `docker compose up --build` locally and opened the frontend: it displayed `Backend status: ok`
  and `AI provider: fake` beneath the synthetic-data disclaimer. No clinical, patient-data, or
  live-AI feature has been implemented.
- Verification: 2026-11-04: `uv sync --project backend --locked --all-extras` passed;
  `uv run --project backend ruff check backend`, `ruff format --check`, `mypy backend/app`,
  `lint-imports`, and `python -m pytest backend/tests --cov=app --cov-report=term-missing` passed
  (3 tests, 85% overall coverage; FastAPI emitted one third-party deprecation warning).
  `npm --prefix frontend run lint`, `typecheck`, `test:run` (1 test), `test:e2e` (1 configured
  placeholder), and `build` passed. `npm --prefix frontend ci` first hit a Windows EPERM lock on
  the generated Lightning CSS binary in this isolated environment; `npm install --prefix frontend`
  restored the exact locked packages successfully. Run `npm ci` in normal local PowerShell before
  committing or starting future phases.
  Phase 2: `uv lock --project backend`, `uv run --project backend ruff check backend`, `ruff
  format --check backend`, `mypy backend/app`, and `lint-imports` passed. The backend pytest
  command passed (9 tests, 58% overall coverage after unexercised API routes were added; one
  third-party FastAPI/TestClient deprecation warning). Docker-backed migration and required
  raw-SQL RLS/connection-reuse integration tests remain unverified because this terminal cannot
  access the user's Docker Desktop named pipe.
  Phase 3 initial slice: `ruff check`, `ruff format --check`, `mypy backend/app`, backend pytest
  (13 tests), and `lint-imports` passed; pytest emitted the same third-party TestClient
  deprecation warning. Target routes/versioning, list filters/pagination, daily aggregation,
  Hypothesis conversion tests, simultaneous idempotency retries, and PostgreSQL-backed
  transaction/RLS checks remain to be implemented and verified.
  Phase 4 rules, alert path, and workers: `uv lock --project backend`, Ruff, formatting, mypy, pytest (23 tests),
  and import-linter passed; pytest emitted the same third-party TestClient deprecation warning.
  The user approved and the assistant applied Alembic migration `0004_alert_worker_rls` to the
  disposable local synthetic PostgreSQL database; `alembic current` reported it as `head`.
- Remote CI: Not run; there is no repository remote or authorized push.
- Decisions / ADR links: [ADR 001](adr/001-modular-monolith.md),
  [ADR 002](adr/002-postgres-before-timescaledb.md),
  [ADR 003](adr/003-dependency-baselines.md), and
  [ADR 004](adr/004-local-object-storage.md), and [ADR 005](adr/005-oidc-migration-path.md). The MinIO image originally referenced by the guide
  was unavailable from Docker Hub during the user's Compose run, so SeaweedFS was adopted behind
  the same local S3-compatible boundary. `docs/prd.md` records synthetic-only, fake-AI, and
  unreviewed-threshold assumptions.
- Blockers, missing licensed data, or human review: The assistant's terminal cannot reach the
  user's Docker Desktop named pipe. IFCT 2017 data/licence and qualified review of clinical
  fixtures remain future human prerequisites. The build has no real patient data or paid AI.
- Next safe step: Complete Phase 4 alert persistence/lifecycle/notification implementation and
  safety tests, then run Phase 2–4 PostgreSQL acceptance tests against the disposable synthetic
  database. Configure non-development JWT/MFA/provisioning secrets before any use beyond the local
  synthetic demo.

## Phase 4 continuation verification (2026-11-04)

- Added deterministic pattern edge handling: fasting glucose ignores future readings and requires
  the configured latest-five window; BP target averages enforce rule type and explicit evaluation
  window. Added golden edge-case tests for strict target boundaries.
- Hardened notification delivery: adapter exceptions become durable failed attempts, successful
  attempts are recorded in `job_attempts`, and terminal failures remain idempotent dead letters.
  No-data worker alerts now also enqueue `AlertNotificationRequested` outbox work.
- Static checks passed: `uv run --project backend ruff check backend`, `uv run --project backend
  ruff format --check backend`, `uv run --project backend mypy backend/app`, and
  `uv run --project backend lint-imports --config backend/.importlinter`.
- Clinical-rule tests passed: `uv run --project backend python -m pytest
  backend/tests/test_clinical_rule_evaluator.py backend/tests/test_clinical_rules_boundary.py -q`
  (26 tests). A broader non-HTTP run passed its available tests with 7 PostgreSQL tests skipped
  when the database was unavailable.
- Full backend pytest is not currently green in this Windows environment: existing FastAPI
  `TestClient` health/auth tests hang during client startup with the installed Starlette/httpx
  combination. This is an environment/tooling blocker, not a pass.
- PostgreSQL integration was attempted with the documented `rpm_test` URL. All 7 opt-in tests
  passed after migration `0005_alert_delivery_integrity` was applied. The full backend suite also
  passed: 45 tests, 1 deprecation warning, 63% overall coverage, and 96% clinical-rules coverage.
- Mutation testing ran in a disposable Linux container with locked mutmut 3.8.1. The 26 selected
  tests passed, but mutmut reported `0 files mutated, 0 ignored, 4 unmodified` and stopped because
  no test case covered a generated mutant. This is not a mutation score; source-copy isolation
  needs investigation. Native Windows mutmut remains unsupported.
- Phase 4 implementation and PostgreSQL acceptance evidence are complete. The phase remains open
  for the 80% overall coverage target and a valid mutation run with survivor review. Next safe
  step: fix the mutmut source-copy configuration and add the missing non-clinical test coverage
  needed for the repository-wide 80% gate.

## Phase 4 handoff to Phase 5 (2026-11-04)

Phase 4 implementation is complete for the synthetic educational demo. Delivered scope includes:

- Pure isolated clinical-rules models, YAML loading, single-reading evaluation, fasting-glucose
  and BP target-pattern evaluation, explicit evaluation timestamps, no-data evaluation, boundary
  tests, golden edge cases, and import isolation.
- Synchronous alert persistence in the observation transaction, deduplication, alert events,
  notification outbox records, deterministic urgent guidance, audited physician acknowledge and
  resolve endpoints, escalation after the 30-minute fixture timeline, and worker RLS identity.
- Durable in-app notification delivery with retry scheduling, idempotent sent state, durable
  failures, and dead-letter state. No-data workers also enqueue notification requests.
- Migration `0005_alert_delivery_integrity`, applied to both local synthetic databases.
- PostgreSQL evidence: all 7 Phase 4 integration tests passed against `rpm_test`, covering
  atomicity, concurrent idempotency, lifecycle transitions, escalation, retry/dead-letter behavior,
  RLS and consent access, admin denial, correction history, and rollback safety.

Phase 4 quality follow-ups are intentionally carried into later engineering work: overall coverage
is 63% versus the repository-wide 80% target, while `clinical_rules` is 96% versus its 95% target.
The locked mutmut run executed the selected tests in a disposable Linux container but generated no
usable mutation score (`0 files mutated, 4 unmodified`), so survivor analysis is pending. Fixtures
remain synthetic, unreviewed, and gated by `requires_clinician_approval: true`; no clinical
validation or clinician approval is claimed.

Phase 5 may begin with these follow-ups tracked as explicit quality debt. The next phase must not
expand into real clinical guidance, production deployment, AI alert decisions, nutrition, or
medication behavior.

## Phase 5 implementation start (2026-11-04)

- Added migration `0006_medication_adherence` for physician-owned current medication records plus
  append-only authored versions and versioned schedules, timezone-aware generated dose events, schedule
  supersession provenance, concern flags, reminder delivery state, RLS, and write guards.
  It has been rendered with Alembic static SQL but has not been applied to a database in this
  terminal.
- Added `medications` API/service contracts: physicians create a new version on every medication
  edit; authorized patients and physicians read current records; only patients self-report a
  dose; 7/14/30-day adherence responses carry `self_reported: true`; concern notes create
  physician-visible, audited flags. Missing reports remain `pending` or `unknown`, never missed.
- Added Celery worker functions that generate the next seven local calendar days idempotently,
  supersede only future unresolved events on a changed schedule, mark overdue events `unknown`,
  and deliver allowlisted, non-advisory synthetic reminder warnings within the configurable late
  window. No AI participates and no medication-change advice is generated.
- Added `MED_MISSED_PATTERN`, which responds only to a real self-reported missed dose through the
  pure pattern path. It remains synthetic-demo-only and `requires_clinician_approval: true`; it
  defines no medication threshold or clinical recommendation. [ADR 006](adr/006-medication-provenance-and-self-report.md)
  records the provenance model.
- `uv run --project backend alembic -c backend/alembic.ini upgrade head --sql` rendered the
  complete migration chain through `0006_medication_adherence`. The reviewed migration was then
  applied only to local disposable synthetic `rpm` and `rpm_test`; both report head.
- PostgreSQL Phase 5 acceptance tests passed against `rpm_test`: Asia/Kolkata offset conversion,
  idempotent generation, schedule changes, unknown-not-missed status, patient create/edit denial,
  physician-authored version provenance, patient concern flags, self-reported adherence, the
  synthetic missed-report path, and sent/expired reminder delivery evidence.
- Final local verification against `rpm_test` passed: `uv run --project backend ruff check
  backend`; `uv run --project backend ruff format --check backend`; `uv run --project backend
  mypy backend/app`; `uv run --project backend lint-imports --config backend/.importlinter`; and
  `uv run --project backend python -m pytest backend/tests --cov=app --cov-report=term-missing`
  (55 passed; one third-party Starlette/TestClient deprecation warning; 65% overall coverage and
  96% `clinical_rules` coverage).
- Functional Phase 5 acceptance evidence is complete. The repository-wide 80% coverage target
  and a valid mutmut score with survivor analysis remain open quality debt, so Phase 5 is not
  complete under the repository’s full quality gate. No clinical validation or clinician approval
  is claimed.

## Phase 6 start (2026-11-04)

- Created [Phase 6 plan](plans/phase-6.md) with the route/screen inventory and shared component
  structure. Phase 4–5 coverage/mutation debt is explicitly carried forward unchanged.
- Added role-aware `/login`, `/patient`, `/physician`, and `/admin` route foundations, including
  patient logging/trend/medication/alert/settings views and physician directory/detail placeholder
  tabs. All role shells display the synthetic-demo, non-emergency, no-real-time-supervision notice.
- Added typed API-client scaffolding, session storage/role guards, login MFA input, logout/refresh
  client methods, an identity-isolated IndexedDB observation queue with stable idempotency keys,
  and a cache-free service worker/PWA manifest. The offline UI states that server-side alerts have
  not been evaluated.
- Frontend checks passed: `npm --prefix frontend run lint`, `typecheck`, `test:run` (1 test), and
  `build`. The first build attempt overlapped a prior Next process; the retry passed. Component,
  offline-queue, accessibility, and true patient-to-physician Playwright coverage remain Phase 6
  work; no Phase 6 acceptance claim is made yet.
- Added reconnect replay for queued observations: it is bound to the authenticated identity,
  preserves the original idempotency key, and only clears the identity-scoped queue after every
  submission succeeds. Failed replays remain visible for retry. Figma UI/UX work created editable
  mobile patient and desktop physician screens in [RPM Platform — Phase 6 Core Flows](https://www.figma.com/design/tnelcnyuzE3WEWNsauRxjn).
  The remaining live-data, accessibility, 360px, and browser-flow work is recorded below.

## Phase 6 live-data and acceptance completion (2026-11-04)

- Completed live synthetic-demo API wiring: authenticated patient profile, consent-scoped physician
  worklist/detail reads, server-supplied alert status/guidance, and physician acknowledgement are
  rendered from the API. Each clinical-data read is authorized and audited; worklist and alert
  queries establish transaction-local database identity before relying on RLS. Admins retain no
  clinical read route.
- Corrected browser integration boundaries: the client now targets the browser-reachable local API,
  CORS permits `Idempotency-Key`, Compose enables deterministic synthetic fixtures only, and the
  backend image ships the versioned rule fixtures. Offline replay keeps its original idempotency key,
  is identity-bound, and clears only after all submissions succeed. Queue tests cover successful
  replay, retained failed work, and account isolation.
- Added valid fabricated end-to-end data creation in Playwright. Every run creates unique clearly
  synthetic names, `example.com` addresses, and `SYN-E2E-*` registration identifiers; it grants
  monitoring consent and provisions the active relationship using real local APIs. Nothing uses
  a real identity, real patient data, clinician approval, or clinical validation.
- Accessibility/viewport evidence: `@axe-core/playwright` reports no violations on the patient
  mobile home, and the 360px assertion confirms no horizontal document overflow. Semantic landmarks,
  skip navigation, labelled controls, focus styles, table captions, and permanent safety notice
  are present.
- Real local browser evidence: `npm --prefix frontend run test:e2e` passed (1 test, 5.3s). It logs
  a 53 mg/dL **unreviewed synthetic fixture** value (`<54` fixture boundary, not medical advice),
  observes the server-provided synthetic urgent wording, signs in an MFA physician with the active
  relationship, acknowledges the alert, and confirms the patient can see `acknowledged`.
- Phase 4–5 quality debt remains: repository coverage is below 80% and mutmut has no valid score.
  Final local checks also passed: `npm --prefix frontend run lint`, `typecheck`, `test:run`
  (3 tests), `build`, and `test:e2e`; `uv run --project backend ruff check backend`, `ruff format
  --check`, `mypy backend/app`, `lint-imports`, and `python -m pytest backend/tests
  --cov=app --cov-report=term-missing` against disposable `rpm_test` (55 passed, 1 third-party
  Starlette deprecation warning, 64% overall coverage, 96% clinical-rules coverage). No clinical
  validation or clinician approval is claimed.

## Phase 7 meal-photo review fallback (2026-11-04)

- The documented Food photo analysis and nutrition module is blocked honestly: no licensed IFCT
  2017 (or alternative Indian) dataset, licence record, or USDA subset was supplied. The project
  therefore does not generate nutrition values, call an AI provider, identify foods, compare food
  with goals, or make a suitability/clinical claim. The decision and deferred scope are recorded
  in [Phase 7 plan](plans/phase-7.md).
- Implemented the authorized fallback: a patient uploads a JPEG/PNG meal-plate photo; the server
  verifies and re-encodes it as a metadata-free private JPEG, stores only an opaque key, SHA-256,
  content type, and size in PostgreSQL, and serves it only through an authenticated, audited,
  `no-store` endpoint. The patient and a physician with an active monitoring relationship can
  view it; the physician may create an append-only, explicitly non-clinical comment. The patient
  can see those comments. No image URL is public or service-worker cached.
- Added migration `0007_meal_photo_review`, which adds photo metadata and an append-only
  `meal_photo_comments` table. Its RLS policies restrict meal reads to active monitoring consent,
  restrict meal creation to the owning patient, and restrict comment creation to the authorized
  physician. The migration was statically rendered but not applied in this terminal.
- Added the S3-compatible storage boundary from ADR 004 using configured SeaweedFS/S3 settings,
  plus `Pillow` for server-side re-encoding and `boto3` for the generic S3 client. This does not
  depend on a SeaweedFS-specific API. The patient and physician UI says the photo is not analysed
  for nutrition, allergies, ingredients, or medical suitability and that comments are not medical
  advice. The permanent synthetic-demo notice remains present.
- Verification passed: `uv lock --project backend`; `uv sync --project backend --locked
  --all-extras`; `uv run --project backend ruff check backend`; `uv run --project backend ruff
  format --check backend`; `uv run --project backend mypy backend/app`; `uv run --project backend
  lint-imports --config backend/.importlinter`; `uv run --project backend python -m pytest
  backend/tests/test_meal_photo_review.py -q` (7 passed); the two new opt-in PostgreSQL RLS tests
  skip without `rpm_test`; and `uv run --project backend alembic -c backend/alembic.ini upgrade
  head --sql`. Frontend `npm --prefix frontend run lint`,
  `typecheck`, and `test:run` passed (4 tests). `npm --prefix frontend run build` remains blocked
  in this environment by a Next/Turbopack CSS-worker spawn failure; it failed both in the sandbox
  and outside it, before application compilation completed.
- Full backend pytest without the unavailable disposable PostgreSQL database passed 48 tests with
  14 integration tests skipped and reported 53% overall coverage (the previously recorded 64%
  was measured against `rpm_test`). The 80% target, the 64% baseline debt, and the invalid mutmut
  run remain unresolved; no quality gate is claimed as complete.
- Next safe step: apply and review migration `0007_meal_photo_review` in the disposable synthetic
  database, verify a private SeaweedFS upload/view/comment flow and RLS denial paths, then obtain
  and licence the required nutrition datasets before starting the actual Phase 7 AI/nutrition
  pipeline.

## Phase 7 meal-photo review fallback completion (2026-11-04)

- The fallback is now complete. Migrations `0007_meal_photo_review` and
  `0008_meal_photo_comment_grants` were applied to both disposable synthetic `rpm` and `rpm_test`
  databases. The latter fixes a live-test finding: RLS policies alone do not grant the constrained
  runtime role permission to reach the comments table, so it grants only `SELECT, INSERT`; no
  update or delete privilege is granted.
- Real PostgreSQL evidence passed: `$env:DATABASE_URL='.../rpm_test'; uv run --project backend
  python -m pytest backend/tests/test_phase7_postgres_integration.py -q` (2 passed). It proves the owning
  patient cannot mutate a meal, the authorized related physician can add a comment but cannot
  alter it, and an unrelated physician cannot read the meal.
- Real browser evidence passed: `npm --prefix frontend run test:e2e` (1 passed, 8.3s). The test
  creates only unique synthetic `example.com` identities, uploads a synthetic PNG as the patient,
  verifies the active related physician can see the image and add a non-clinical comment, then
  verifies that the patient sees that comment. A browser-test lifecycle bug found during this flow
  was fixed by retaining the submitted form reference before awaiting upload.
- Final local checks passed against `rpm_test`: Ruff, formatting, mypy, import-linter, and
  `python -m pytest backend/tests --cov=app --cov-report=term-missing` (64 passed, 1 third-party
  Starlette/TestClient deprecation warning, 63% overall coverage, 96% clinical-rules coverage).
  Frontend lint, typecheck, Vitest (4 tests), and E2E passed. The native Next/Turbopack production
  build remains an environment failure in this terminal, although the rebuilt Compose frontend
  served the passing browser scenario. The 80% coverage goal and invalid mutmut run remain open
  project-quality debt; no nutrition or clinical-validation claim is made.
- Next safe step: obtain and record licences for IFCT/another suitable Indian data source and a
  USDA subset before any food-identification or nutrient-calculation work begins.

## Phase 8 deterministic analytics and grounded-insights foundation (2026-11-04)

- Added pure, caller-supplied analytics for glucose mean/SD, explicitly labelled percentage of
  *sampled readings* in a physician-defined range (never CGM time in range), fasting sampled
  first-to-last change, BP component means, and a BP/self-reported-missed-dose association.
  Every fact retains source IDs, a time window, sample size and an insufficient-data state. Dose
  absence is never interpreted as missed. Meal-to-glucose/carbohydrate analytics are deliberately
  absent: the Phase 7 food/nutrition licence blocker remains.
- Added a typed facts packet and deterministic patient renderer. Patient-visible text is derived
  only from supported fact IDs and includes the synthetic-demo / not-for-medical-use label. A
  provider draft is untrusted physician-only data: it must cite known non-insufficient facts and
  cannot introduce a number absent from them or prohibited diagnosis/prescribing language.
  Provider errors and invalid drafts fall back to the same deterministic template; no provider is
  selected or called in this slice.
- Added migration `0009_grounded_insights`: `ai_artifacts` now has monitoring-consent RLS,
  immutable content/version provenance, review timestamps, and an explicit prior-approval
  invalidation timestamp when a physician creates a new summary version. Authorized, audited API
  endpoints list insights and let only a related, consent-gated physician create, review, reject,
  or revise a draft. Administrators remain excluded through the shared authorization boundary.
- Verified locally: `uv run --project backend ruff check backend`; `uv run --project backend ruff
  format --check backend`; `uv run --project backend mypy backend/app`; `uv run --project backend
  lint-imports --config backend/.importlinter`; `uv run --project backend python -m pytest
  backend/tests/test_phase8_grounded_insights.py -q` (56 passed); and `uv run --project backend
  alembic -c backend/alembic.ini upgrade head --sql` all passed. The full backend command
  `uv run --project backend python -m pytest backend/tests --cov=app --cov-report=term-missing`
  passed (104 passed, 16 PostgreSQL integration tests skipped, 1 third-party Starlette/TestClient
  deprecation warning, 55% overall coverage, 96% clinical-rules coverage).
- The carried quality debt is not resolved: the required 80% repository coverage target is still
  unmet and mutmut still has no valid score. The migration has been statically rendered only in
  this terminal; PostgreSQL RLS/version-invalidation checks, Celery daily/weekly publication,
  real-provider selection, and the patient/physician insight UI are deferred. No clinical
  validation, clinician approval, or nutrition claim is made.
- Next safe step: run `0009_grounded_insights` and focused RLS/version-invalidation tests against
  the disposable synthetic database, then separately authorize any provider/worker/UI work. Keep
  the nutrition-data licensing prerequisite in place before adding meal-derived analytics.

## Phase 9 backend interoperability foundation (2026-11-05)

- Added migration `0010_phase9_interop`, consent-scoped patient/physician message
  threads, read receipts/unread counts, hashed one-time paired-device tokens, device sync metadata,
  RLS, and constrained grants. Messaging returns a permanent non-emergency/expected-response-time
  notice and is deliberately separate from clinical alerts; no message keyword makes a clinical
  decision because no reviewed message-event rule exists.
- Added device pairing/listing and token-authenticated device reading APIs. A device token is
  checked while scoped to its URL device record, then trusted server code uses the same observation
  shape, unit conversion, deterministic evaluator, audit/outbox transaction, and device-scoped
  idempotency semantics as the established ingestion path. Raw pairing tokens are never stored or
  logged. The included simulator only posts synthetic user-supplied local credentials.
- Added an explicitly restricted read-only FHIR R4 JSON subset: Patient, Observation search,
  MedicationRequest/MedicationStatement in a patient Bundle, and strict subset structure checks.
  BP uses the documented panel/component mapping. Glucose is exported only with recorded LOINC
  blood-specimen metadata and supported UCUM units; uncoded/native observations are not converted
  to invented generic codes. This is not a claim of full FHIR R4 conformance or clinical coding
  validation.
- Local verification passed: focused Phase 9 tests (4 passed), Ruff, format, mypy, import-linter,
  static Alembic SQL rendering, and full backend pytest (108 passed, 16 PostgreSQL integration
  tests skipped, 1 third-party TestClient deprecation warning, 55% overall coverage and 96%
  clinical-rules coverage). The 80% coverage target and invalid mutmut result remain carried debt.
- Migration application, PostgreSQL RLS/relationship-denial tests, actual duplicate/reordered
  simulator ingestion, device alert equivalence, FHIR HTTP round trips, frontend messaging/device
  views, stale-device display, and any full FHIR validator/terminology-service work remain
  deferred. No clinician approval, real-device certification, or real-time monitoring claim is
  made.
- Next safe step: apply/review `0009` and `0010` in disposable synthetic `rpm_test`, write and run
  the Phase 8/9 PostgreSQL acceptance tests (especially device token/RLS/idempotency and unrelated
  physician messaging denial), then separately authorize frontend work.

## Phase 9 database acceptance continuation (2026-11-05)

- Applied `0009_grounded_insights`, `0010_phase9_interop`, and `0011_audit_append` to disposable
  synthetic `rpm` and `rpm_test`; both are at head. The original Phase 9 revision name exceeded
  Alembic's existing 32-character version column, so its transaction rolled back cleanly before
  the identifier was shortened and successfully reapplied.
- Live RLS testing found that constrained device ingestion could not retain its mandatory audit
  event. `0011_audit_append` adds an audit-owned `SECURITY DEFINER` append function with only an
  execute grant to the runtime role; no module receives direct audit-table write access.
- `$env:DATABASE_URL='.../rpm_test'; uv run --project backend python -m pytest
  backend/tests/test_phase9_postgres_integration.py -q` passed (2): duplicate device sends replay
  one `source=device` observation, and an unrelated physician cannot read a message thread.
  Out-of-order simulator, FHIR HTTP round trips, and frontend views remain unfinished Phase 9 work.

## Phase 9 presentation and FHIR HTTP continuation (2026-11-05)

- Added patient Settings device pairing/listing and consent-scoped non-emergency messaging views.
  The physician patient-monitoring view now lists each authorized device's last receipt time and
  visibly says “No device sync recorded — review data age” when absent. This is a data-age cue,
  not a clinical threshold, alert, clinician-review claim, or real-time monitoring claim.
- Added an authenticated FastAPI HTTP round trip with a signed synthetic patient JWT and disposable
  PostgreSQL session override. It reads `/api/v1/fhir/Patient/{id}`, `/api/v1/fhir/Observation?patient={id}`,
  and `/api/v1/fhir/Patient/{id}/$everything`, asserting R4-subset resource types and synthetic IDs.
  The medication request uses the schema-owned `start_date`; no invented creation time is exposed.
  The no-date Observation query now omits the nullable bind parameter, fixing PostgreSQL's
  untyped-null failure.
- The audit writer preserves valid request IPs but maps non-IP test-client hosts to null before the
  PostgreSQL `inet` cast. This retains append-only auditing without fabricating an IP address.
- Local verification passed: `$env:DATABASE_URL='.../rpm_test'; uv run --project backend python -m
  pytest backend/tests/test_phase9_postgres_integration.py -q` (3 passed, one third-party TestClient
  deprecation warning); `uv run --project backend ruff check backend`; `uv run --project backend
  mypy backend/app`; `npm --prefix frontend run lint`; `npm --prefix frontend run typecheck`; and
  `npm --prefix frontend run test:run` (3 files, 4 tests). `git diff --check` passed.
- Full backend verification subsequently passed: `uv run --project backend ruff check backend`,
  `ruff format --check`, `mypy`, import-linter, and `python -m pytest backend/tests
  --cov=app --cov-report=term-missing` (108 passed, 19 skipped, 55% overall and 96%
  clinical-rules coverage; one third-party TestClient deprecation warning). The default frontend
  build, `npm --prefix frontend run build`, is blocked by a Next 16.4.5 Turbopack CSS-worker process
  error while processing `app/globals.css`; `npm --prefix frontend run build -- --webpack` succeeds.
  Lint, typecheck, and Vitest remain green. The Turbopack failure is not attributed to a passed
  default build.
- Remaining debt: browser E2E for the Phase 9 workflow, the default Turbopack build failure,
  80% overall coverage, and a valid mutmut score. The synthetic-demo boundary, lack of clinical
  validation/approval claims, and Phase 7 nutrition-data licensing blocker remain unchanged.

## Phase 10 security and reliability hardening (2026-11-05)

- Added `docs/plans/phase-10.md`, a current STRIDE threat model, explicit dated release-gate
  exceptions, and a performance-evidence document that deliberately has no fabricated numbers.
  The plan and docs preserve the synthetic-demo, non-emergency, unreviewed-clinical-fixture, and
  fake-AI boundaries; no clinical validation or clinician approval is claimed.
- Hardened the API with an explicit CORS origin allow-list, per-source auth/ingestion limits,
  UUID-validated correlation IDs, no-store/no-frame/nosniff/referrer/permissions headers, and a
  default-deny API CSP. New `/ready` reports PostgreSQL/Redis dependency state while `/health`
  remains a dependency-free liveness endpoint. Request IDs are included in new observation/alert
  outbox metadata, worker retries are explicit, and sent alert deliveries emit an
  observation-recorded-to-notification-sent duration metric without logging patient content.
- Added migration `0012_phase10_security`: a user access-token invalidation epoch. Current-token
  authorization now checks active identity and the epoch; logout/password reset revoke refresh
  tokens and invalidate older access tokens. The migration was statically rendered only, never
  applied, because this terminal lacks Docker Desktop access.
- CI now defines locked Python dependency audit, production npm audit, Gitleaks, bounded public
  OpenAPI Schemathesis, and a public-endpoint ZAP baseline. `tools/backup_restore_smoke.ps1` now
  restores only into a separately named disposable database with `ON_ERROR_STOP` and cleanup. The
  k6 harness requires caller-provided tokens for 1,000 distinct synthetic patients; no token,
  patient data, or benchmark number is stored in the repository.
- Local verification passed: `backend\\.venv\\Scripts\\python.exe -m ruff check backend`, `ruff
  format --check backend`, `mypy backend\\app`, `backend\\.venv\\Scripts\\lint-imports.exe --config
  backend\\.importlinter`, and focused Phase 10/identity/upload pytest (`15 passed`). Static
  Alembic render to `0012_phase10_security` passed. Frontend `lint`, `typecheck`, and `test:run`
  passed (3 files, 4 tests); `git diff --check` passed.
- Exact blockers/not-passes: the full backend pytest command stalled after 26 test markers in this
  Windows environment; `docker compose ps` and the restore prerequisite failed with denied access
  to Docker Desktop's named pipe; no local pip-audit/npm-audit/Gitleaks/Schemathesis/ZAP execution
  was performed because those are CI evidence and remote CI has not run. Default `npm --prefix
  frontend run build` still fails in Turbopack while processing `app/globals.css` and creating its
  CSS worker. An attempted `--webpack` build also failed with `EPERM` creating
  `frontend/.next/types/app/(patient)/patient`. Neither build is reported as a pass.
- Carried debt remains: the 80% overall-coverage target is unmet, mutmut has no valid score with
  survivor review, the default Turbopack build is failing, and the Phase 9 browser workflow lacks
  E2E coverage. The open security/reliability evidence exceptions have owner, impact, compensating
  control, and 2026-12-05 expiry in `docs/security-exceptions.md`.
- Next safe step: on a machine with Docker Desktop, review and apply `0012` only to disposable
  synthetic databases; run the clean restore, full backend/integration suite, the 1,000-patient k6
  test, and remote CI scanners; record actual results or close/renew the dated exceptions before
  any public-demo release work. Stop here before Phase 11 evaluation/safety-case scope.

## Phase 10 verification completion (2026-11-05)

- Completed the previously unavailable local infrastructure evidence without crossing the Phase 10
  boundary. Reviewed migration `0012_phase10_security` was applied only to disposable synthetic
  `rpm` and `rpm_test`, both reporting head. `tools/backup_restore_smoke.ps1` passed after
  restoring into its dedicated `rpm_restore_smoke` database with `ON_ERROR_STOP`, verifying the
  restored `users` table, and dropping that database. The script was corrected after an initial
  false-positive attempt exposed PowerShell stream redirection flattening the dump; that attempt
  is not claimed as a pass.
- `k6 run tools/load/observations.js` completed 1,000 one-per-patient synthetic submissions using
  five VUs against a separately named disposable `rpm_phase10_load` database: 14.9 seconds,
  0/1,000 HTTP failures, request p50/p95/p99 71.93/95.61/115.98 ms, and synchronous alert-creation
  p50/p95/p99 25.12/38.55/45.29 ms. `docs/eval/performance.md` records the machine/workload limits;
  these are not production, clinical, or real-time-monitoring claims.
- Reliability fault evidence: after `docker compose stop redis`, an authenticated synthetic
  observation on the isolated service returned 201 while `/ready` returned 503; after
  `docker compose start redis`, `/ready` returned 200. This confirms Redis unavailability is
  visible without dropping accepted synchronous recording/alert work. Object-storage and AI
  provider failure paths remain covered by the passing meal-photo and grounded-insights tests.
- Exact local verification: the focused suite spanning Phase 4/5/7/8/9 integration plus Phase 10,
  identity, and meal-photo tests passed **90 tests** against disposable `rpm_test` (one third-party
  Starlette/TestClient deprecation warning). Ruff, formatting, mypy, and import-linter passed.
  `pip-audit --path backend\.venv\Lib\site-packages` found no known vulnerabilities (the local
  project package is not on PyPI); `npm --prefix frontend audit --omit=dev --audit-level=high`
  found 0 vulnerabilities; and Schemathesis selected two public operations and passed all 20
  generated cases. Frontend lint, typecheck, and Vitest passed (3 files, 4 tests). `git diff
  --check` passed.
- Not passes: the local ZAP image pull did not complete; remote GitHub CI has not run because this
  worktree has not been pushed. That remaining release-gate exception has a demo-maintainer owner,
  impact, compensating workflow, and 2026-12-05 expiry in `docs/security-exceptions.md`. The full
  backend suite remains unverified after its prior Windows stall. The default Next 16.4.5 Turbopack
  build still fails at `app/globals.css` because its CSS worker exits before connection. The 80%
  coverage target and valid mutmut score with survivor review remain carried quality debt.
- Removed only the temporary Phase 10 load container/database/token artifacts after recording the
  results. No real identities, credentials, patient data, clinical validation, or clinician
  approval record was used or created. Stop here at the Phase 10 boundary; the next safe action is
  to review actual remote CI before considering any later-phase or public-demo work.

## Phase 11 evaluation slice (2026-11-05)

- Added `docs/plans/phase-11.md`, `backend/eval/report.py`,
  `backend/tests/test_phase11_evaluation.py`, generated `docs/eval/report.md`, and replaced the
  outdated initial hazard log in `docs/safety-case.md`. One command regenerates the report:
  `backend\.venv\Scripts\python.exe backend/eval/report.py` (or
  `uv run --project backend python backend/eval/report.py`).
- The offline run measured 200 simple deterministic AI-off summaries (0 unsupported-number,
  uncited-claim, or banned-content findings), 50/50 existing adversarial regression cases, and
  seven labelled synthetic fixture boundary cases (TP 4, TN 3, FP 0, FN 0). The report records
  denominators, narrowly scoped methods, measured local evaluator timing, and limitations. The
  labels follow the same unreviewed demo fixtures and are not independent clinical evidence.
- Food image evaluation is blocked: the repository has a photo-review feature but no food
  recognition/portion/nutrient pipeline, licensed dataset, images, or human answer key. A tested
  paired-results metric helper exists, but no image pipeline or food result is claimed. Human
  usability sessions and clinician/faculty review remain pending. No clinician approval, clinical
  validation, real-patient use, or standards compliance is claimed. Phase 11 remains incomplete.
- Verification: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_phase11_evaluation.py
  backend/tests/test_phase8_grounded_insights.py -q` passed 58 tests; report regeneration passed;
  `backend\.venv\Scripts\python.exe -m ruff check backend`, `ruff format --check backend`,
  `mypy backend/app`, and `backend\.venv\Scripts\lint-imports.exe --config backend/.importlinter`
  passed. Frontend `npm --prefix frontend run lint`, `typecheck`, and `test:run` passed (3 files,
  4 tests). `git diff --check` passed with CRLF conversion warnings.
- Full backend `backend\.venv\Scripts\python.exe -m pytest backend/tests --cov=app
  --cov-report=term-missing` stalled after 26 progress markers and was interrupted; no coverage
  result is claimed. `npm --prefix frontend run build` failed in the existing Turbopack CSS-worker
  startup path. `npm --prefix frontend run test:e2e` failed before the test ran because the
  sandbox lacks the Playwright Chromium executable. Remote CI and local ZAP remain unverified;
  the dated Phase 10 release-gate exception, 80% overall coverage target, valid mutmut score and
  survivor review, and Turbopack debt remain open. No deployment or remote action was performed.
- Next safe step within Phase 11: obtain licensed labelled meal images and a supported evaluation
  pipeline, conduct and record human usability and clinician/faculty feedback, address the named
  evaluation gaps, and rerun all required checks in a configured environment. Stop before Phase 12.

## Phase 11 continuation: selected meal-photo review workflow (2026-11-05)

- The user confirmed that patient meal-photo submission followed by physician comments is the
  selected alternative to automated food recognition and nutrient estimation. This supersedes the
  prior entry's proposed need for a labelled food dataset and food-estimation pipeline. The report
  marks nutrient and recognition metrics not applicable; it does not claim automated estimates.
- `backend/eval/report.py` now executes the synthetic meal-photo unit checks and reports passed,
  failed and skipped counts; failure or inability to run is not reported as a pass. It also
  evaluates twelve synthetic glucose and blood-pressure fixture scenarios. Added a regression
  test for failed/skipped meal-check reporting. `docs/eval/human-protocol.md` prepares reproducible
  usability tasks, SUS collection and threshold/wording feedback without inventing findings.
  The safety case now addresses inaccurate or misunderstood physician meal comments.
- Regenerated `docs/eval/report.md`: 7 photo-review unit checks passed; 200 deterministic AI-off
  summaries had zero detected unsupported-number, uncited-claim and banned-content findings;
  50/50 existing adversarial cases passed; 12 fixture-labelled alert scenarios yielded TP 7,
  TN 5, FP 0, FN 0. The limitations and denominators are in the report; these are not clinical
  evidence, independent ground truth, real-user results, or review of comment quality.
- Focused `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_phase11_evaluation.py
  backend/tests/test_phase8_grounded_insights.py backend/tests/test_meal_photo_review.py
  backend/tests/test_clinical_rule_evaluator.py -q` passed 90 tests before the additional reporting
  regression was added; `backend\.venv\Scripts\python.exe -m pytest
  backend/tests/test_phase11_evaluation.py -q` then passed 3 tests. The report regeneration passed.
  Backend Ruff, format, mypy and import contracts passed before the final reporting-only edit;
  frontend lint, typecheck and Vitest passed (3 files, 4 tests).
- The full backend coverage command stalled again after 26 markers and was interrupted; no new
  overall coverage result is claimed. `npm --prefix frontend run build` again failed at the
  Turbopack CSS worker. `npm --prefix frontend run test:e2e` failed before test execution because
  Chromium is absent in the sandbox. Docker Desktop access was denied in this terminal, so no
  fresh PostgreSQL meal-authorization run was claimed. Previous Phase 10 integration evidence is
  preserved above. Remote CI and ZAP, 80% coverage, valid mutmut score/survivor review and the
  dated release-gate exception remain open. No deployment, clinical approval, or clinical
  validation was performed or implied.
- Phase 11 remains open for actual usability sessions with at least five volunteers, documented
  clinician/faculty feedback, and required verification in a configured environment. The next
  safe step is to run the prepared human protocol and record actual findings; stop before Phase 12.

## Phase 12 preparation (2026-11-05)

- User authorized continuation into Phase 12 while finishing possible Phase 11 work. The offline
  evaluation report was regenerated and the combined focused Phase 11 tests passed 91 cases.
  Actual five-person usability sessions and clinician/faculty feedback remain pending and are
  not represented as completed. The selected meal workflow remains photo submission and comments.
- Added `docs/plans/phase-12.md`, candidate `backend/Dockerfile.demo` and
  `frontend/Dockerfile.demo`, and [ADR 007](adr/007-demo-deployment-boundary.md). They are
  multi-stage and use non-root runtime users; builds remain unverified because Docker access was
  denied. Added `.env` exclusion to both build contexts. The existing local development images
  and Compose workflow remain in place. No public deployment configuration or reset is claimed.
- Corrected the server-side frontend health fetch to use `BACKEND_INTERNAL_URL` in Compose while
  retaining the browser-facing URL; `frontend/tests/health.test.ts` verifies this distinction.
  Rewrote the stale root README and architecture descriptions; added `CHANGELOG.md`,
  `CONTRIBUTING.md`, `docs/adr/README.md`, `docs/demo-script.md`,
  `docs/deployment-readiness.md`, and sourced `docs/regulatory-notes.md`. The user selected MIT;
  added `LICENSE` with the contributor copyright notice. No screenshot or video is claimed.
- Verification: `backend\.venv\Scripts\python.exe backend/eval/report.py` passed;
  `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_phase11_evaluation.py
  backend/tests/test_phase8_grounded_insights.py backend/tests/test_meal_photo_review.py
  backend/tests/test_clinical_rule_evaluator.py -q` passed 91 tests; Ruff, format, mypy and
  import-linter passed. `npm --prefix frontend run lint`, `typecheck`, and `test:run` passed
  (3 files, 4 tests), including the new health test. `docker compose config --quiet`, local
  documentation-link existence check and `git diff --check` passed. `docker build -f
  backend/Dockerfile.demo backend` failed before build due to denied Docker buildx lock access;
  Docker Desktop daemon access was also denied, so neither candidate image was verified.
- The full backend coverage command stalled after 26 markers and was interrupted. Default frontend
  build again failed creating the Turbopack CSS worker. `npm --prefix frontend run test:e2e`
  failed before running the test because sandbox Chromium is absent. No local Git history secret
  scanner was available; one commit is present, but a clean history is not claimed. Remote CI and
  ZAP remain unverified. The 80% overall coverage, valid mutmut score and survivor review, and
  Phase 10 dated release-gate exception remain open. A ten-minute fresh quick start is unverified.
- Phase 12 remains incomplete. In particular, public synthetic account restrictions, tenant
  isolation, private provisioning/admin controls, external messaging and AI spending safeguards,
  a tested environment-scoped nightly reset, production HTTPS configuration and a deploy script
  must be implemented and verified. A hosting target and explicit deployment authorization remain
  necessary; no deployment, reset, tag, push, clinical approval, validation or compliance claim
  occurred. Follow [deployment readiness](deployment-readiness.md), then complete the human
  evaluation and outstanding checks before proposing release.

## Phase 11/12 automated review and release work (2026-11-05)

- At the user's request, performed a synthetic code walkthrough, recorded in
  `docs/eval/automated-walkthrough.md`, and linked it from the regenerated evaluation report.
  This is not participant feedback, a SUS score, clinician/faculty review, or approval; those
  human evidence gaps remain disclosed. The user requested eventual deployment followed by a new
  public GitHub repository; no hosting target has been supplied, and the selected GitHub connector
  does not expose repository creation. No deployment or push has taken place.
- Fixed observation submission to reuse the same idempotency key when an online request has an
  uncertain result; server validation rejections are displayed rather than mislabeled as network
  errors. Offline replay now removes only each acknowledged item, keeping items concurrently
  enqueued, and logout no longer destroys the identity-bound offline queue. Server-provided alert
  guidance is shown during submission and replay, and incomplete sync is visible. Added structural
  positive-number checks, prevented double-click submission, and stopped inventing glucose meal
  timing. Fixed blood-pressure UI units and unstable meal-photo fetch dependencies.
- Added migration `0013_bp_components` for blood-pressure observations without scalar original
  values while preserving component values and requiring scalar originals for other types. Updated
  the response type and unit validation; added schema and PostgreSQL regression tests. Static SQL
  rendering passed via `backend\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade
  0012_phase10_security:0013_bp_components --sql`. The migration has **not been applied or
  integration-tested**: Docker/Desktop database access remains unavailable in this sandbox.
- Verification: `npm --prefix frontend run lint`, `typecheck`, and `test:run` passed (5 files,
  9 tests), including lost-response idempotency, rejection, server guidance, concurrent queue
  insertion and the component-only blood-pressure form. Backend Ruff, format, mypy and import
  contracts passed. `backend\.venv\Scripts\python.exe -m pytest backend/tests
  --ignore=backend/tests/test_health.py --cov=app --cov-report=term-missing` passed 114, skipped
  20 and reported 55% coverage; this is a partial suite with database integration skipped and
  does not satisfy the 80% gate. `test_health.py` was excluded because the full suite had stalled
  there on this host. The full suite, browser E2E, production build, image builds, remote CI, ZAP,
  valid mutation score/survivor review and Git-history secret scan remain unverified. The dated
  Phase 10 exception remains open. `docker compose config --quiet` and `git diff --check` passed.
- A production deploy remains blocked by unimplemented restricted demo identities, isolation,
  guarded reset, private administration, outbound-message and spend controls, missing compatible
  hosting access, and required tests. The connected Sites runtime cannot directly host this
  FastAPI/Celery/PostgreSQL/Redis stack. Do not deploy development defaults or mark either phase
  complete. Next: run migration and integration tests on a disposable synthetic database; finish
  and verify the public-demo controls; obtain a compatible host; then deploy and create/push the
  requested public repository with actual CI and secret-scan evidence.
- Follow-up verification on the final edits: frontend lint/typecheck passed and Vitest passed
  5 files / 9 tests; default Next/Turbopack build again failed while starting the CSS worker.
  Backend Ruff, format, mypy and import contracts passed. A temporary ASGITransport replacement
  for the hanging health tests also stalled and was reverted; no test was weakened or skipped in
  the canonical suite. PostgreSQL and full browser checks remain pending.

## Localhost deployment and verification (2026-11-05)

- The user selected localhost. `docker compose` was available outside the restricted sandbox.
  Reviewed migration `0013_bp_components` was applied first to the disposable synthetic
  `rpm_test` database, then to the existing synthetic `rpm` development database after testing.
  No database, volume or storage reset was performed.
- The first full backend run exposed a bind-parameter mistake in the new PostgreSQL regression
  test; corrected it and reran. The full suite then passed 137 tests with 66% overall coverage
  and one third-party warning. The 80% overall gate remains unmet. A later full-suite run after
  additional CORS/worker changes stalled and was interrupted; do not treat that later run as a
  pass. The final focused `test_phase10_hardening.py` run passed 7 tests.
- Changed local Compose host ports to `127.0.0.1` for frontend, backend, PostgreSQL and object
  storage; the development stack is not a public deployment. `docker compose up -d --build`
  built and started it without deleting volumes. `GET /health` returned `ok` and `AI_PROVIDER=fake`;
  `GET /ready` reported database and Redis ready; the home page showed the exact synthetic-data
  disclaimer and backend healthy status. The address is `http://localhost:3000`.
- The initial browser scenario reached meal-photo upload but failed because CORS preflights
  consumed the auth rate limit. Adjusted middleware to exclude preflights while retaining the
  limit on real authentication attempts; added a regression. The synthetic browser E2E passed
  1 test after respecting the existing rate window (1.2 minutes). Frontend lint, typecheck and
  Vitest passed (5 files, 9 tests). A separate Linux `docker build -f frontend/Dockerfile.demo
  --build-arg NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 frontend` succeeded including the
  production Next build; this does not claim the native Windows build passed.
- Fixed the local worker's database URL, declared the already-locked `packaging==26.3` as a
  runtime dependency needed by Kombu's Redis transport, registered the scheduled task modules,
  and added a local Celery scheduler. Worker and scheduler are running; the worker connected to
  PostgreSQL and Redis, registered all seven scheduled tasks, and processed pending in-app outbox
  work. Local development worker runs as root and is not a production deployment. No real patient
  data, clinical validation, clinician approval or human usability findings are claimed.
- Public-demo isolation, restricted public identities, guarded reset, safe secret management,
  non-root deployment, release-gate exceptions, coverage, mutation score/survivor review, remote
  CI, ZAP and Git history secret scanning remain unresolved. No public deployment, public GitHub
  repository, commit, push, tag or scheduled data reset was created. The user requested a public
  repository after completion; do not imply it exists. Next: address these outstanding gates and
  publish only after reviewing the exact changes and history for secrets.

## Local access from the home page (2026-11-05)

- The user reported seeing only the local health page. Added links to sign in and to create a
  synthetic patient account, plus a patient-only registration form using the existing backend API.
  It asks for fictional details and explains that physician accounts are separately provisioned;
  it exposes no role selection and does not invent credentials or clinician approval.
- Rebuilt the localhost frontend with `docker compose up -d --build frontend`; the running local
  server now serves the new links. `npm --prefix frontend run lint`, `typecheck`, and `test:run`
  passed (5 files, 9 tests). `npm --prefix frontend run test:e2e --
  tests/e2e/synthetic-registration.spec.ts` passed (1 test), creating a fictional test account
  and reaching the patient home. `git diff --check` passed. Public deployment and earlier quality
  and review gaps remain open; no real patient data should be entered.

## Demo entry redesign (2026-11-05)

- Replaced the health-only landing screen with a responsive introduction, illustrated synthetic
  dashboard, feature descriptions, and patient/physician entry points. Reworked sign-in, patient
  registration, and added physician access information. Patient account creation continues to
  use the existing patient-only endpoint; physician accounts remain trusted-provisioned and MFA
  protected. No clinician approval or real patient use is implied. Illustrations are labelled.
- `npm --prefix frontend run lint`, `typecheck`, and `test:run` passed (5 files, 9 tests).
  `npm --prefix frontend run test:e2e -- tests/e2e/synthetic-registration.spec.ts` passed (1
  synthetic account). The local Compose frontend was rebuilt and the landing page was inspected
  in the in-app browser. The new entry design does not change the patient/physician dashboard
  interiors; existing release, coverage and human-review gaps remain open.

## Distinct patient and physician workspaces (2026-11-05)

- Redesigned the local patient workspace with a green personal navigation and separate entry cards
  for glucose, blood pressure, heart rate and oxygen saturation. Each card uses its own submission
  and idempotency key, unit and offline retry path; blood-pressure components remain paired.
  Redesigned the physician workspace with a separate blue worklist and patient-directory layout.
  Existing authorization, clinical rules, data sources, synthetic-only scope and server alert text
  remain unchanged. No Figma file was supplied or modified.
- The user requested removal of disclaimers. Automatic approval review rejected a local rebuild
  that removed the repository's required synthetic-data and not-for-medical-use notices. Restored
  the notices and completed the redesign with them in place; no approval or clinical validation
  is implied. The active local frontend was rebuilt with the notices retained.
- `npm --prefix frontend run lint`, `typecheck` and `test:run` passed (5 files, 10 tests), including
  a test for four simultaneously visible reading fields and blood-pressure submission. The first
  browser run found low-contrast text; colors were corrected. `npm --prefix frontend run test:e2e`
  then passed both synthetic scenarios (2 tests, including patient-to-physician, axe and mobile
  overflow checks). `git diff --check` passed. Earlier coverage, mutation, public-demo, clinical
  review and remote CI gaps remain open.

## Single-save and sign-in refinement (2026-11-05)

- Replaced individual reading buttons with one **Save readings** action. Entered readings are
  validated before submission and sent as separate existing observation transactions, each with
  its own idempotency key. Results are shown per reading; successful or queued values clear while
  rejected or uncertain values remain visible. Empty parameters are not submitted. The explicit
  offline buttons were removed; the existing durable retry behavior remains active for a lost
  connection. The UI does not claim the individual transactions are atomic.
- Added accessible show/hide password controls to sign-in and patient registration. Physician
  sign-in now rejects patient credentials rather than silently opening the patient workspace;
  actual role and MFA remain determined by the server. Added physician account setup links, which
  lead to trusted-provisioning information; they do not create physician accounts. The existing
  provision endpoint does not supply an MFA bootstrap to the new physician, so a complete safe
  physician self-onboarding workflow remains unimplemented. No public privileged role was added.
- The user again requested removing the patient disclaimer. It remains after the earlier automatic
  approval review rejected removing the mandatory synthetic-demo and non-medical-use notice; the
  scope and clinical-safety boundaries are unchanged. No clinician approval is claimed.
- Verification: `npm --prefix frontend run lint`, `typecheck`, and `test:run` passed (6 files,
  12 tests), including all-four-reading, individual key, password-toggle, role mismatch and blood
  pressure checks. After correcting password-label accessibility and rerunning tests sequentially
  to respect the auth rate limit, `npm --prefix frontend run test:e2e -- --workers=1` passed both
  synthetic browser scenarios (2 tests). The localhost frontend was rebuilt; `git diff --check`
  passed. Public-demo, coverage, mutation, clinical-review and release-gate gaps remain open.

## Public repository preparation (2026-11-05)

- The user requested a new public GitHub repository. Reviewed the non-ignored candidate files;
  excluded the generated `frontend/tsconfig.tsbuildinfo` change from the proposed commit without
  discarding it. A domain-only check found only example addresses and no flagged patient-text
  fields; this limited check is not a proof that all content is safe for publication.
- `docker run ... zricethezav/gitleaks:v8.28.0 git /repo --redact=100` scanned the one existing
  commit and reported one generic-key finding. Inspection confirmed it was the synthetic fixture
  identifier `spo2.low.urgent`, not a credential. `.gitleaksignore` documents and excludes that
  exact commit/file/rule/line fingerprint. The history scan with that exception passed. A separate
  scan of 235 current candidate files found only the same reviewed identifier; the worktree scan
  was not a zero-finding pass. The temporary candidate copy was removed. No credentials or real
  patient data were intentionally included.
- Before publication, backend Ruff, format, mypy and import contracts passed. Frontend lint,
  typecheck and Vitest passed (6 files, 12 tests); the last synthetic browser run passed 2 tests.
  The most recent full backend suite was attempted but stalled; earlier local evidence and the
  80% overall-coverage gap, unvalidated mutation result, unreviewed fixtures, incomplete physician
  onboarding and remote CI status remain as recorded above. The application is a synthetic-only
  demo and is not ready for real-patient use or public hosting. A public source repository is not
  itself a public deployment. The GitHub connector did not offer repository creation, and browser
  sign-in was pending when this entry was written. No push or remote CI success is claimed here.
- The public repository `hemanthreddy-gif/RPM-Platform` was created for the user-requested
  publication. At the time of this entry it was empty; the reviewed push and remote CI still had
  to be verified. Its existence is not a clinical deployment or release approval.
- The first remote CI run for commit `7f342fc` was observed at
  `https://github.com/hemanthreddy-gif/RPM-Platform/actions/runs/42054589113`: backend and
  frontend jobs passed, but security scans failed at the Python dependency audit because its
  requirements export included the editable local project with hashes. The subsequent security
  scan, fuzz and ZAP steps were skipped. The backend job had not set `DATABASE_URL`, so its
  PostgreSQL-dependent tests were not established as having run. Updated CI to omit the local
  project from the locked dependency export, use Python 3.12 for pip-audit, and migrate and test
  against the dedicated `rpm_test` service. The updated remote run must be verified separately.

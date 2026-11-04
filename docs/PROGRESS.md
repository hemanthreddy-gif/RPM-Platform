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
- Local verification passed: `uv run --project backend ruff check backend`; `uv run --project
  backend ruff format --check backend`; `uv run --project backend mypy backend/app`; `uv run
  --project backend lint-imports --config backend/.importlinter`; and `uv run --project backend
  python -m pytest backend/tests --cov=app --cov-report=term-missing` (41 passed, 12 skipped,
  one third-party Starlette/TestClient deprecation warning, 53% overall coverage and 96%
  `clinical_rules` coverage). `uv run --project backend alembic -c backend/alembic.ini upgrade
  head --sql` rendered the complete migration chain through `0006_medication_adherence` without a
  database connection.
- PostgreSQL Phase 5 tests cover Asia/Kolkata offset conversion, idempotent generation, schedule
  changes, unknown-not-missed status, and patient create/edit denial, but remain unexecuted here:
  this terminal still cannot access the user’s Docker Desktop database. Apply the reviewed
  migration only to the disposable synthetic `rpm`/`rpm_test` databases, then run those opt-in
  tests before calling Phase 5 complete.
- Quality debt deliberately remains open: overall coverage decreased from the prior 63% to 53%
  because the new service/worker paths require PostgreSQL integration execution. The 80% overall
  gate and a valid mutmut score with survivor analysis have not been met.

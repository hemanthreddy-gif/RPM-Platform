# Phase 10 plan — security and reliability evidence

## Scope and safety boundary

This phase hardens the synthetic educational demo and records testable evidence. It does not add
clinical thresholds, clinician approval, real-patient support, deployment, or claims of security
certification, clinical validation, or regulatory compliance. Existing deterministic clinical-rule
and transactional observation/alert boundaries remain unchanged. The Phase 4–9 80% overall
coverage gap, invalid mutmut result, and Windows default Turbopack build failure remain explicitly
tracked unless independently resolved with evidence.

## Authorized implementation

1. Replace the Phase 0 checklist with a current STRIDE threat model covering API/authentication,
   observation/device ingestion, uploads/object storage, workers/outbox, AI, exports, and
   operational dependencies. Map each threat to implemented controls, regression tests, or an
   owned, dated exception.
2. Add narrowly scoped request rate limits for authentication and ingestion, response security
   headers/strict CSP, explicit allow-list CORS, generic credential-failure responses, refresh
   token revocation enforcement, and upload validation that fails visibly. Cover the boundary
   behaviour without logging credentials or patient content.
3. Add `/ready` dependency status beside the existing liveness endpoint, correlation propagation
   across API/outbox workers, and an observation-to-notification latency metric. Preserve accepted
   synchronous observation/alert transactions if Redis is unavailable; asynchronous delivery must
   remain visibly pending/retryable rather than silently disappear.
4. Make worker retry/dead-letter configuration explicit and test retries/dead letters plus
   graceful, visible Redis, object-storage, and AI-provider failure paths. Do not make an external
   service a hidden precondition for core recording/alerts.
5. Add CI evidence for pinned dependency audit, secret scanning, Schemathesis OpenAPI fuzzing, and
   a non-production OWASP ZAP baseline. Record tools or environment prerequisites as documented
   exceptions rather than claiming a remote run.
6. Retain and document the disposable-only backup/restore smoke script; add a safe test seam and
   record exactly whether a clean-database restore could run in this environment. Add a reproducible
   k6 load-test harness and `docs/eval/performance.md`; publish only actual measurements.

## Verification plan

Run focused security/reliability tests, then backend Ruff, formatting, mypy, import contracts and
the full backend suite. Run frontend lint, typecheck, Vitest, and the default build separately;
record the known Turbopack failure exactly if it persists. Run the locally available audit/security
commands and the backup/restore/load harness only against disposable synthetic infrastructure.
Update `docs/PROGRESS.md` with commands, results, exceptions, owners, impact, compensating
controls, expiry, and the next safe phase boundary.

## Implementation evidence (2026-11-05)

- Added a strict API CORS allow-list, per-source auth/ingestion sliding-window limits, no-store,
  no-frame, nosniff, referrer, permissions, and default-deny CSP response headers. Request IDs are
  UUID-validated before logging and propagate into new observation/alert outbox payloads.
- Added `/ready` with explicit PostgreSQL/Redis state while `/health` remains external-dependency
  free. Alert delivery logs the measured observation-recorded-to-notification-sent duration when
  an alert is observation-backed. Celery tasks use late acknowledgement, publish retry, and bounded
  exponential task retries; existing PostgreSQL retry/dead-letter records remain authoritative.
- Added migration `0012_phase10_security` for the user-level access-token invalidation epoch.
  Logout and password reset revoke refresh tokens and invalidate issued access tokens; the current
  principal dependency checks active user state and the epoch before authorizing a request.
- Replaced the Phase 0 checklist with a STRIDE model and added CI jobs for pip-audit, npm audit,
  Gitleaks, bounded unauthenticated Schemathesis, and ZAP baseline. Added the disposable-only
  restore smoke hardening and a 1,000-patient-token k6 harness. The remaining owned exception is
  remote CI status for this unpushed worktree; it is recorded in `docs/security-exceptions.md`.
- The reviewed `0012_phase10_security` migration was applied only to disposable synthetic `rpm`
  and `rpm_test` databases. The hardened restore smoke test passed against a separate
  `rpm_restore_smoke` database and removed that database afterward. Its earlier PowerShell stream
  redirection bug was corrected: the script now copies the SQL dump without flattening it, restores
  with `ON_ERROR_STOP`, and checks the restored `users` table.
- A k6 run against `rpm_phase10_load` completed 1,000 distinct synthetic-patient submissions over
  five virtual users in 14.9 seconds with no HTTP failures. Exact p50/p95/p99 values are in
  `docs/eval/performance.md`; they remain local engineering evidence only.
- Local checks passed: project-venv Ruff, format check, mypy, import-linter; the focused
  database/security suite (90 passed, one third-party Starlette/TestClient deprecation warning);
  `pip-audit` (no known vulnerabilities; the local project package is not on PyPI); production
  `npm audit` (0 vulnerabilities); and bounded public Schemathesis (20/20 generated cases passed
  for `/health` and `/api/v1/ping`). The configured local ZAP image pull did not finish in this
  terminal; its workflow remains configured but local ZAP is not reported as passed. Frontend
  lint, typecheck, and Vitest (3 files, 4 tests) passed. `git diff --check` passed.
- A controlled local Redis outage accepted an authenticated synthetic observation (201) while
  `/ready` accurately returned 503, then returned 200 after Redis restarted. Object-storage and
  provider failure paths remain covered by the passing focused upload/grounded-insights tests;
  no accepted observation is routed through Redis.
- The full backend pytest command remains unverified in this Windows environment after its prior
  stall. Default `npm --prefix frontend run build` still fails in Turbopack while processing
  `app/globals.css` and creating its CSS worker. The carried 80% coverage and valid-mutmut-score
  debt are unchanged. These are not passes.

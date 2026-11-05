# RPM Platform — project handoff and remaining work

**Snapshot:** 2026-11-05 · **Repository:** [hemanthreddy-gif/RPM-Platform](https://github.com/hemanthreddy-gif/RPM-Platform) · **Reference commit:** `5d034b4` before this handoff was written.

> **Demo with synthetic data. Not for medical use.** This is an educational research prototype,
> not an emergency service or a clinically validated system. No clinician has approved its rule
> fixtures. Do not enter real patient information.

The owner wants a polished, working local demonstration with distinct patient and physician
experiences. They believe substantial work remains; **no validated completion percentage or
schedule has been measured**. Do not present the 12-phase build guide or a successful CI run as
proof the project is complete, safe for real care, or ready for public hosting. The next assistant
should use [AI_INSTRUCTIONS.md](AI_INSTRUCTIONS.md) together with this document.

## How to read the records

The source and tests are the immediate evidence; [PROGRESS.md](PROGRESS.md) is the chronological
engineering log, with newer entries superseding old ones. Its opening Phase 5 statement and some
older plan/architecture language are historical, not the current overall status. The
[build guide](build-guide.md) is a blueprint, not proof that every acceptance criterion has been
met. Its older nutrition-model description was superseded by the owner's meal-photo-and-comment
choice. Some generated reports still say remote CI/ZAP is unverified; the later evidence below
supersedes that text for the specific commit, without closing other gaps. The original source
blueprint may be unavailable; do not reconstruct or invent it.

## What exists

| Area | Implemented slice | Important limits |
| --- | --- | --- |
| Foundation and data | FastAPI/Python backend, Next.js frontend, PostgreSQL, Redis/Celery, SeaweedFS local object storage, Compose, migrations through `0013_bp_components`, deterministic synthetic seed tooling. | Local development stack; use disposable synthetic databases only. Container candidates and operational readiness are not a production deployment. |
| Identity and access | Patient-only public registration; trusted physician/admin provisioning; hashed passwords, access/refresh tokens, MFA, relationship and purpose-specific consent checks, audit and database restrictions. | **Physician onboarding is incomplete:** provisioning does not offer a complete safe first-time MFA bootstrap. A physician cannot simply self-register; do not bypass MFA or create a public privileged signup. |
| Observations and alerts | Typed glucose, BP, pulse and oxygen observations; original units and times, immutable corrections, scoped idempotency, transactional observation/alert/audit/outbox writes and deterministic rules. Synthetic rule fixtures and escalation/delivery workers exist. | Rules and wording are unreviewed, demo-only and gated; `requires_clinician_approval` stays true. No diagnosis, prescription or real-time care is provided. |
| Medication | Physician-authored versions/schedules, generated dose events, reminders and explicitly patient self-reported adherence. | Missing reports are pending/unknown, not inferred missed; no medication advice. |
| Patient and physician UI | Responsive landing/sign-in, patient registration, distinct workspaces, reading cards, physician worklist and patient detail. One Save action submits filled measurements individually and displays each result; offline retry retains per-observation idempotency. | The multiple reading submissions are **not one atomic batch**. Some UI and accessibility work remains; an end-to-end demo needs safely provisioned synthetic physician credentials and relationships. |
| Meals | Private validated meal-photo upload and authorized physician comments. | **Selected alternative:** no automated food identification, portion estimation or nutrition computation. Do not promise nutrients or revive a food-AI requirement without a new product decision. |
| Insights | Typed source-linked analytic facts, deterministic patient text and validation/fallback for untrusted provider drafts. | The recorded evaluation uses simple AI-off synthetic cases. It does not establish semantic faithfulness or clinical utility. |
| Communication and interoperability | Consent-gated synthetic messaging, device-token ingestion and simulator; limited read-only FHIR R4 subset. | Messaging is not an emergency channel; no reviewed message-event rule. No real devices, external delivery or full FHIR conformance claim. |
| Evaluation and docs | [Safety case](safety-case.md), [evaluation report](eval/report.md), [performance report](eval/performance.md), [human protocol](eval/human-protocol.md), threat model, ADRs, README and MIT license. | Automated walkthroughs cannot replace participant sessions, SUS results or clinician/faculty feedback. No approval record exists. |
| Repository and local operation | Public source repo on `main`; local demo was started at `http://localhost:3000`, loopback-bound. | Local availability changes with Docker/service state. Public GitHub source is **not** a public app deployment. No hosted demo or safe scheduled reset is claimed. |

## Verified evidence, with dates and limits

- [GitHub Actions run 42055557504](https://github.com/hemanthreddy-gif/RPM-Platform/actions/runs/42055557504), for `5d034b4`, completed backend, frontend and security jobs successfully. Backend applied migrations on a disposable PostgreSQL service and passed **139 tests**, with **67% overall coverage** and one warning. This is below the **80%** overall target. The repository also sets a **95% clinical_rules** target; verify its current figure from the exact run before claiming it.
- The remote frontend job passed install, lint, typecheck, **12 Vitest tests**, and production build. The configured security job passed dependency audits, secret scanning, limited public-endpoint Schemathesis and a ZAP baseline; the scope and options in [.github/workflows/ci.yml](../.github/workflows/ci.yml) matter. A green scan is not a security certification. Browser E2E is not part of this workflow.
- On the previous local revision, `npm --prefix frontend run test:e2e -- --workers=1` passed **2** synthetic browser scenarios, including patient-to-physician, meal-photo and an axe check. It creates synthetic records and requires configured services and Playwright browser binaries. Results are not human usability research.
- The final publication history scan found no leaks after an **exact historical false-positive exception** for the synthetic `spo2.low.urgent` message identifier; see [../.gitleaksignore](../.gitleaksignore). Do not broaden or remove the context without review. A separate worktree scan found that same identifier, not a zero-finding result.
- The prior Windows native Next/Turbopack build failed starting its CSS worker; the Linux Docker candidate build and GitHub Actions build succeeded on their recorded revisions. Do not conflate these environments. Full local backend runs have also stalled intermittently; a previous configured local run passed **137 tests, 66%**.
- Mutation testing produced **no valid score**; survivor review is pending. Do not turn the earlier `0 files mutated` output into a score. The local 1,000-patient load run is described in [eval/performance.md](eval/performance.md), with its machine and scope limits.

## Prioritized work remaining

### P0 — make the local demo complete and safe to operate

1. **Physician onboarding and access.** Design a trusted, auditable provisioning and first-time MFA enrollment flow; specify actor, secret handling, expiry, replay prevention and recovery. Implement it through the owning identity module, not a public role selector. Add permission, token, MFA, failure and negative tests; run a real end-to-end scenario with a synthetic physician, active relationship and monitoring consent. Provide clear local setup instructions without committing credentials.
2. **Reliable patient and physician journeys.** Review registration, sign-in, reading entry, partial failure, duplicate retries, timestamps/data age, meal-photo comments, alerts, navigation and role switching on mobile and desktop. Retain a single Save action with explicit per-reading results and per-record idempotency. Do not silently drop accepted or queued work. Test keyboard navigation, loading/empty/error states and data authorization; avoid fabricated dashboard metrics.
3. **UI/UX polish.** Improve both workspaces consistently while preserving their distinct patient and physician purposes. Verify actual links, flows, text contrast, responsive behavior and screen-reader labels. Keep the required synthetic-data and non-emergency disclosures. The previous attempt to remove them was rejected by automatic approval review.

### P1 — engineering evidence and quality

4. **Coverage and mutation testing.** Reach and demonstrate 80% overall and 95% clinical_rules coverage with meaningful tests, not tests that mirror implementation. Fix the mutmut source-copy/runner problem in a disposable supported environment, generate a valid score and review survivors; test every configured boundary. Preserve import isolation.
5. **Permissions and reliability.** Expand database and API integration coverage for wrong-patient access, revoked consent and relationships, admin denial, image access, device tokens, concurrent idempotency, transaction rollback, correction provenance, outbox retry/dead-letter, Redis/object-store/provider failures and worker identity. Verify the Phase 9 browser workflow rather than assuming unit tests cover it.
6. **Evaluation.** Expand synthetic alert scenarios and clearly distinguish evaluator latency from observation-to-alert and notification delivery latency. Strengthen independent checks of rendered claims and adversarial/provider-output validation. Report denominators, zero-denominator handling and failures. Food-model metrics are not applicable to the chosen photo-comment feature.
7. **Human work.** If the project owner decides to pursue the guide's research evaluation, conduct actual usability sessions with at least five participants and an appropriate SUS instrument; obtain actual clinician/faculty feedback and record dates, roles, findings and disposition. An AI-only walkthrough can identify issues but cannot be relabeled as participants, SUS, clinician review or approval. Neither this handoff nor any prior run claims them.

### P2 — public-demo release, only if requested

8. Implement and verify restricted synthetic patient/physician identities, tenant isolation, private admin/provisioning, no external messaging, fake AI or a global spend cap, upload/abuse limits, secrets and HTTPS. A nightly reset must target only a separately identified demo database/object store and be tested for wrong environment, concurrency, failures and auditability. No reset should run merely because a schedule exists.
9. Use non-root runtime images, pinned dependencies and storage choices, secure networking, backup/restore and a rehearsed deploy/rollback. The checked-in local worker runs as root and `docker-compose.yml` is development-only. Reassess the dated exceptions and verify the latest CI, logs and actual deployment. See [deployment-readiness.md](deployment-readiness.md), [security-exceptions.md](security-exceptions.md) and [threat-model.md](threat-model.md).
10. Update README, screenshots/demo capture, architecture, safety case, changelog and the current handoff with measured evidence; run a fresh-clone setup test. A public GitHub repository alone is not a hosted application. Deployment, public access, commit/push and destructive actions need the user's chosen workflow and authorization.

## Code and document map

- `backend/app/clinical_rules/`, `backend/rules/`: isolated deterministic evaluator and synthetic YAML fixtures. `backend/.importlinter` enforces the isolation contract.
- `backend/app/modules/`: module-owned APIs/services for identity, observations, alerts, medications, nutrition, patients, messaging, devices, FHIR, insights and audit. `backend/app/workers/` owns background orchestration.
- `backend/app/ai/analytics/`, `backend/app/ai/writer/`: pure facts and grounded rendering; AI has no clinical-table writes.
- `backend/migrations/versions/`: inspect migrations before applying. `backend/tests/` contains unit and opt-in disposable PostgreSQL integration tests.
- `frontend/app/`, `frontend/components/`, `frontend/lib/`: routes, components, API/session and offline queue. `frontend/tests/` includes Vitest and Playwright.
- [architecture.md](architecture.md), [adr/README.md](adr/README.md), [PROGRESS.md](PROGRESS.md), [safety-case.md](safety-case.md), [eval/report.md](eval/report.md): decisions and evidence.

## Immediate next assignment

Start with **P0 physician onboarding** after reading the identity code, migrations, tests and ADR
005. First write a short plan covering trusted provisioning, first-time MFA, authorization, audit,
expiration/replay, failure recovery and synthetic-only scope. Then implement and test an authorized
vertical slice; do not infer the owner's physician identity or invent clinical approval. See the
companion manual for a ready-to-paste prompt and the commands to run.

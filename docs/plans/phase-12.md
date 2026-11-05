# Phase 12 plan — local packaging and release readiness

Continue into Phase 12 with the user's authorization while carrying Phase 11 human-study gaps and
Phase 10 release-gate, coverage, mutation and build debt. Preserve the synthetic-only boundaries;
never claim clinical approval, validation, compliance, or an actual deployment.

1. Reconcile stale architecture and evaluation documentation with the selected meal-photo review
   path. Retain pending usability sessions and external reviewer feedback as open evidence.
2. Prepare separate non-root multi-stage images for a synthetic demo without altering the current
   development Compose workflow. Do not expose a public deployment or automate destructive reset
   until restricted identities, isolation and environment-scoped safeguards are implemented and
   verified. Document the remaining public-demo gate explicitly.
3. Replace stale README content with truthful status, architecture, reproducible local setup,
   measured results, limitations and a roadmap; add the ADR index, contribution guidance, change
   log, a safe demo script and sourced regulatory notes. The owner selected MIT; add the license and preserve third-party terms. No screenshot, study or legal approval will be fabricated.
4. Run relevant image/config checks where available and required backend/frontend checks, inspect
   the final diff, and update progress with exact results and remaining blockers. No deployment,
   publication, tag or destructive reset is authorized by selecting the phase.

## Continuation — automated review and deployment request

The user requested a synthetic substitute for human feedback, a public GitHub repository and a
subsequent deployment. Record any automated walkthrough as an engineering review, never as SUS,
participant feedback, clinician review or approval. Investigate and fix observed reading workflow
failure paths, including retry idempotency, concurrent queue writes, response errors and displayed
server guidance, with regression tests. Retain all release-gate and human-review gaps. Prepare a
public repository only after reviewing the worktree and secret-scan evidence; deploy only to an
identified compatible host after the necessary safety paths and checks are implemented. Do not
expose the local development stack or reset non-demo data.

## Continuation — localhost deployment

The user selected localhost as the deployment target. Keep the synthetic demo bound to loopback,
verify the reviewed migration first on the disposable `rpm_test` database, then apply it only to
the existing synthetic development database after tests pass. Build and start the local stack,
verify its visible disclaimer and health endpoints, and report exact checks. Do not reset existing
volumes or claim a public deployment. Preserve all public-release, coverage, mutation and human
review gaps and do not push before the requested work and secret review are complete.

## Continuation — make the local app accessible

The localhost home page displays health but has no route into the application and no patient
account creation UI. Add a clear sign-in link and a synthetic-patient-only registration form using
the existing backend registration endpoint. Keep privileged roles provisioned separately and
retain the demo notice. Verify the UI and restart only the local frontend; document limitations.

## Continuation — polished demo entry experience

Redesign the local landing page and patient/physician sign-in and onboarding entry points with
responsive accessible layouts, descriptive copy and truthful synthetic-demo examples. Preserve the
existing patient-only registration API, trusted physician provisioning and MFA; never create a
public privileged role-selection endpoint. Verify navigation, existing auth and responsive layouts,
record checks and leave the existing local-only and clinical-review limitations in place.

## Continuation — distinct workspaces and individual reading entry

Redesign the patient and physician workspace shells and home pages around their separate tasks.
Show separate input cards for glucose, blood pressure, heart rate and oxygen saturation, each
submitting its own existing observation with its own idempotency key and safe offline behavior.
Keep existing server authorization, validation and clinical rules. The user requested removal of displayed disclaimers. Automatic approval review rejected the
local rebuild without the required synthetic-data and not-for-medical-use notice; the notices were
restored. Preserve the synthetic-only boundaries and server-provided alert guidance. Verify regression tests and local UI, and report
remaining limitations without implying real clinical use.

## Continuation — sign-in and single-action reading entry

Keep the required prototype notice after the prior automatic-review rejection. Correct role-specific
sign-in feedback, add accessible password visibility controls, and change the four reading cards
to a single save action. Preserve individual server transactions, idempotency, retry behavior and
clear per-reading outcomes; never report a partially saved set as fully saved. Investigate a
trusted physician provisioning path without allowing public privileged self-registration. Verify
regression tests and the local demo; document any remaining physician onboarding limitation.

## Continuation — public GitHub repository

The user explicitly requests a new public GitHub repository and push. Inspect the exact tracked
and untracked candidate files and Git history for secrets or real patient data, exclude generated
artifacts, preserve all existing work and document any scan limitations. Update repository status
and documentation without suggesting a public clinical deployment or completed human review.
Create and push only after the review and relevant checks; do not force-push or overwrite an
existing remote. Verify the resulting public repository and report actual CI status.

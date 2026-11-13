# Phase 13: Patient and physician experience redesign

Authorized 2026-11-06: redesign the existing local app, improve the landing page,
complete secure physician onboarding, add patient profiles/photos and sleep recording,
and connect patients with provisioned physicians. No deployment or Git publication.

1. Inspect current routes, identity, consent, observation transactions and recorded gaps.
2. Establish a consistent responsive, keyboard-accessible visual system across landing,
   authentication, patient and physician workspaces; preserve synthetic-demo notices.
3. Add typed, authorized and audited profile editing/private images, self-reported sleep
   observations, and explicit patient-controlled monitoring connections.
4. Complete expiring single-use physician invitations and MFA enrollment before privileged
   access. Keep public patient registration separate and existing safeguards intact.
5. Connect frontend flows to real APIs, add meaningful permission/failure regressions,
   review migrations, run backend/frontend checks and available local browser integration.
6. Review the diff and update PROGRESS with exact evidence, remaining gaps and next step.

Design target: WCAG 2.2 AA practices including visible focus, labelled inputs, readable
contrast, responsive reflow and usable pointer targets. Automated checks do not establish
full conformance. No medical thresholds, clinical approvals or sleep advice are invented.

Existing modification to frontend/tsconfig.tsbuildinfo is preserved. Use existing locked
dependencies. All records and browser tests must use explicitly synthetic data only.

Follow-up authorization: user requested a deployment link on 2026-11-06. Hosting discovery found
Railway/Render integrations available but not connected; the connected Sites runtime cannot run
the current FastAPI/PostgreSQL/Celery stack. Local services remain loopback-only. A hosting account
and release-readiness work are prerequisites to a verified public URL; no tunnel or deployment
of development credentials is authorized by implication.

Final local validation: 175 backend tests, 15 frontend tests and 4 browser scenarios passed;
Linux production build passed. Railway selected after the user delegated host choice. Account
connection and the documented release controls remain outstanding for public deployment.

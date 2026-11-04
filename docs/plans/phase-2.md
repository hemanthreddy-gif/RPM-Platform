# Phase 2 plan — identity, access control, consent, and audit

## Scope

Implement backend-only authentication, MFA, consent/relationship authorization, immutable audit
recording, and PostgreSQL RLS for the Phase 1 patient-owned tables. No clinical workflow or UI.

## Steps

1. Add identity tables/constraints and RLS policies in a reviewed Alembic migration; use a
   non-owner runtime role and transaction-local trusted identity.
2. Implement module-owned identity, patients, and audit services plus typed FastAPI routes.
3. Implement patient-only registration; protected privileged provisioning; password/JWT/refresh
   rotation, revocation, lockout, reset token, and MFA enrollment/verification.
4. Add consent and relationship administration, explicit patient-object authorization and audit
   middleware/dependencies.
5. Add security tests for token state, MFA, patient isolation, consent revocation, audit writes,
   and PostgreSQL policy configuration; run the Phase 2 backend checks and record exact results.

## Safety decisions

- Only a trusted administrative principal can provision privileged roles; public registration
  always produces a patient.
- Passwords, refresh/reset tokens, and TOTP secrets are never logged or returned after enrollment.
- Administrators can provision/assign but are categorically denied patient clinical reads.
- Database RLS identity derives only from validated server-side claims and is scoped to each
  transaction; client headers cannot set it.
- MailHog delivery is an adapter seam in this phase; reset responses do not disclose account state.

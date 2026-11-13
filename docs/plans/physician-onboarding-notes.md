# Physician onboarding slice (2026-11-06)

Implement administrator-issued, expiring invitations, password creation and a scoped MFA
bootstrap. Keep invitation and bootstrap tokens hashed, secrets encrypted, and issue no access
or refresh tokens until a valid authenticator code confirms enrollment. Invitation redemption
and account creation use row locks and one transaction; failed MFA attempts are bounded.

Add an accessible three-step physician setup screen and an invitation form for authenticated
administrators or the trusted local provisioning operator. Preserve patient-only registration,
relationship/consent authorization, synthetic-only scope and existing privileged provisioning.

Implemented and verified against disposable PostgreSQL: rejected/expired/replayed invitations,
MFA failures, role restrictions, mixed-case invitation sign-in and complete onboarding. Public
invitation/bootstrap routes share existing auth rate limits. See PROGRESS.md for final commands.

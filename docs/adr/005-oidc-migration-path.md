# ADR 005: Migrate prototype identity to OIDC before any non-demo use

## Status

Accepted, 2026-11-04.

## Decision

Phase 2 uses local Argon2id credentials, rotating opaque refresh tokens, and TOTP only for the
synthetic local prototype. Before any non-demo deployment, migrate authentication to a managed or
self-hosted OIDC provider (for example Keycloak) using authorization-code flow with PKCE.

## Consequences

The application will validate issuer, audience, signature, expiry, and subject claims from the
provider and map roles only from server-controlled claims. Refresh-token rotation, revocation,
MFA policy, account recovery, key rotation, and security-event retention become provider-managed
controls. The application retains its relationship/consent checks, object-level filters, RLS, and
audit trail; an authenticated OIDC identity alone never grants clinical access.

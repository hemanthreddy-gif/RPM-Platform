# ADR 007: Separate local image candidates from public deployment

## Status

Accepted for the synthetic educational prototype, 2026-11-05. Public deployment remains blocked.

## Decision

Keep the existing development Compose configuration intact. Provide separate non-root,
multi-stage Dockerfile candidates for build testing. A production Compose file, public demo
credentials, reset job and deploy script are deferred until restricted synthetic identities,
tenant isolation, private administration, safe environment-scoped reset, external-message
controls, spending limits, HTTPS and release-gate checks are implemented and tested together.
Do not expose the development stack to the internet.

## Consequences

Candidate images do not constitute a working deployment and have not been verified in Docker in
this environment. A public host, secrets and deployment authorization are still needed. Phase 11
human evidence and Phase 10 quality and release-gate debt stay visible; this decision does not
approve clinical thresholds or production use. The reset must never touch a non-demo database or
object store and requires failure, concurrency, authorization and scope tests before scheduling.

# ADR 003: Phase 0 dependency baselines

## Status

Accepted, 2026-11-04.

## Decision

Use Python 3.12, Node.js 24, PostgreSQL 16, Redis 7, FastAPI, Next.js, and Docker Compose.
`uv.lock` and `frontend/package-lock.json` are the exact dependency records; their resolved
versions are generated during Phase 0 rather than manually copied into this ADR.

## Why

The installed Windows runtimes were verified locally. Lock files provide reproducible exact
versions and are safer than unverified handwritten version claims.

## AI decision

`AI_PROVIDER=fake` is the default. No API key, paid provider, or model identifier is required for
development or tests.

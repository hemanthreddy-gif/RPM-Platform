# Phase 0 preparation plan

## Authorized slice

Implement Phase 0 only: the local project skeleton, health endpoints, Docker Compose, automated
checks, CI configuration, documentation, and the safety-boundary enforcement required by the
build guide. Do not implement application features from later phases.

## Steps

1. Initialize the local Git repository without committing or publishing.
2. Create the Python/FastAPI and Next.js/TypeScript skeletons with fake AI as the default.
3. Add local services, health checks, environment examples, quality commands, CI, and import
   contracts that protect clinical rule isolation.
4. Add Phase 0 ADRs, lightweight risk records, and a disposable backup/restore smoke-test guide.
5. Lock dependencies, run available checks, record exact evidence, and stop at Phase 0.

## Completion evidence

The project starts locally through Docker Compose; `/health` and `/api/v1/ping` respond; the
frontend reads backend health; quality commands and an intentional import violation demonstrate
the configured boundaries. All results and any environment-only limitations are in
`docs/PROGRESS.md`.

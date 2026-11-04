# RPM Platform

> **Demo with synthetic data. Not for medical use.**

RPM Platform is an educational research prototype for physician-supervised diabetes and
hypertension monitoring. It will use only synthetic data. It is not clinically validated, does
not provide emergency monitoring, and makes no regulatory-compliance claim.

## Phase 0 status

| Area | Status |
| --- | --- |
| FastAPI health API | Foundation created |
| Next.js health page | Foundation created |
| Docker Compose services | Configuration created; local engine check required |
| Database schema and patient data | Not started (Phase 1) |
| Authentication and permissions | Not started (Phase 2) |
| Clinical rules and alerts | Not started (Phase 4) |
| AI provider | Fake/offline default only |

## Architecture

The project is a modular monolith: a Next.js frontend talks to a FastAPI backend; PostgreSQL is
the durable transaction store; Redis/Celery handle later background tasks; SeaweedFS provides a
local S3-compatible store for later private image uploads; MailHog is a local-only email sink.
Read [architecture](docs/architecture.md)
for boundaries and flows.

Clinical alerts will come only from a deterministic, pure rules package. AI is optional and will
never decide alerts, calculate nutrients, diagnose, prescribe, or change a dose.

## Local quick start (PowerShell)

1. Copy `.env.example` to `.env` and keep `AI_PROVIDER=fake`.
2. Install backend dependencies: `uv sync --project backend --locked --all-extras`.
3. Install frontend dependencies: `npm --prefix frontend ci`.
4. Start services: `docker compose up --build`.
5. Open `http://localhost:3000`; the page should show backend status `ok` and AI provider `fake`.

Run the documented quality checks in [AGENTS.md](AGENTS.md). The backup/restore smoke test is
`./tools/backup_restore_smoke.ps1` and uses only a disposable local database.

## Limitations

No real patients, clinician approval, nutrition dataset, clinical validation, external messaging,
or deployment exists in Phase 0. Do not use this prototype to make health decisions.

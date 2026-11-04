# Phase 1 plan — database and synthetic data

## Scope

Implement the Section 4 data foundation and reproducible, clearly synthetic development cohort.
No login, patient-facing API, clinical rules, alert processing, or live AI work is included.

## Steps

1. Add module-owned SQLAlchemy models, common database configuration, and Alembic setup.
2. Create and review one PostgreSQL migration with immutable-observation and append-only-audit
   controls, runtime permissions, idempotency/outbox/retry state, and required indexes.
3. Add a guarded, deterministic seed command that produces only fake identities and named input
   scenarios for invalid/duplicate submissions.
4. Test model constraints, migration upgrade/downgrade hooks, audit/observation protections, and
   repeatable canonical seed hashes. Record anything requiring the user's Docker engine.

## Safety decisions

- Seed data uses only `example.invalid` identities and explicit synthetic labels.
- No fixture creates a real clinical claim or marks an alert rule approved.
- Invalid and duplicate submissions are exported as named test inputs, never inserted as valid
  production observations.
- The fake AI provider remains the default and is unused by this phase.

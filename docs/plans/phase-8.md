# Phase 8 plan — deterministic analytics and grounded-summary foundation

## Scope and safety boundary

Phase 7 completed only the private meal-photo review fallback.  No licensed food dataset exists,
so Phase 8 must not infer foods, carbohydrates, nutrients, or meal-to-glucose associations from
photos.  This slice uses only immutable observation records, physician-defined monitoring targets,
and explicitly self-reported dose events.  It is synthetic-demo-only, does not diagnose, predict,
recommend treatment, or imply clinician approval or real-time review.

The Phase 4–7 quality debt is carried unchanged: repository coverage remains below the 80% goal
and the locked mutmut run has no usable score.  This plan does not claim either gate is resolved.

## Authorized implementation

1. Add pure, dependency-free analytics DTOs and functions for glucose and blood-pressure
   descriptive facts, explicitly labelled *sampled-reading* target percentage, and only
   self-reported missed-dose comparison.  Every derived fact carries source IDs, a window, sample
   size, and an `insufficient_data` result where the minimum sample is not met.
2. Add a typed facts packet and deterministic renderer.  A provider-facing writer accepts only
   the facts packet; provider output is untrusted and may be retained only as a physician draft
   after typed-reference/value validation.  Patient-visible text is always a deterministic
   template over validated facts.  Provider errors and invalid output use that same fallback.
3. Add protected `ai_artifacts` versioning/RLS support and authorized, audited endpoints to read
   deterministic insights and create, approve, reject, or revise physician-only summary drafts.
   Revisions create a new artifact version; no artifact content is edited in place.
4. Add unit tests using hand-computed samples, traceability, fabricated-number rejection,
   provider-failure fallback, and a 50-case adversarial corpus that cannot change the template or
   introduce advice/diagnosis.

## Explicitly deferred

- Nutrition, food matching, carbohydrate bands, and meal-to-glucose pairing: the Phase 7 data
  blocker remains.
- A real external LLM provider and Celery publication jobs: no provider/model has been selected,
  and this bounded slice proves the AI-off path first.
- Frontend insight cards and physician review screens.  The authenticated API returns citation
  source IDs for a later UI to drill into the existing observation range.
- Clinical validation, clinician approval, performance claims, and the carried coverage/mutmut
  debt.

## Verification plan

Run focused writer/analytics tests, then backend lint, format, type, import-contract and complete
backend test commands.  Render the migration SQL.  Run PostgreSQL-only acceptance only when the
documented disposable database is available; otherwise record it as unrun rather than passed.

## Implementation evidence (2026-11-04)

- Added the pure analytics fact layer, typed packet builder, deterministic renderer, and provider
  draft validator. `0009_grounded_insights` protects artifact access with monitoring-consent RLS,
  preserves immutable content/version lineage, records review status, and invalidates a prior
  approval when an authorized physician creates a revision.
- Added audited physician draft/create-review-revision endpoints and authorized patient/physician
  insight reads. The API returns supporting observation/dose IDs in the facts packet. No frontend,
  Celery publication, real provider, or meal-derived fact was added.
- Passed focused tests (56: hand-computed analytics, provenance, invalid/un-cited draft rejection,
  provider-failure fallback, and 50 adversarial strings), migration SQL rendering, and the full
  non-database backend suite. PostgreSQL application/RLS verification remains unrun in this
  terminal and must use the documented disposable synthetic database.

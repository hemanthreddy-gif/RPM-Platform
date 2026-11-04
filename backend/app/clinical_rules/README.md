# Clinical rules boundary

This package is reserved for deterministic clinical evaluation. It must remain pure: no database,
network, clock, worker, application, or AI imports. Phase 4 implements the evaluator and only
clinician-reviewed rule configuration can activate a real alert path.

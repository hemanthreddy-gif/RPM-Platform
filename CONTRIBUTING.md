# Contributing

This repository is a synthetic-data-only educational research prototype. Read [AGENTS.md](AGENTS.md),
[architecture](docs/architecture.md), the current [progress](docs/PROGRESS.md), applicable ADRs,
and the relevant build-guide section before making changes. Never add real patient data, secrets,
clinical approval claims or unreviewed thresholds. Keep the visible demo and non-emergency notices.

For multi-step work, write a short phase plan first. Preserve module boundaries, authorization,
auditability, deterministic rule isolation, provenance, and transactional outbox/idempotency.
Add meaningful regression tests for safety and failure paths. Use locked dependencies and do not
introduce new infrastructure without documenting a decision. Run the relevant commands in
[AGENTS.md](AGENTS.md), report skipped or unavailable checks, and update progress with evidence.

This repository is offered under the [MIT License](LICENSE); third-party dependencies retain their
own terms.
Do not submit proprietary or personal data. No public hosting or real-patient use is authorized by
contributing.

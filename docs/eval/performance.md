# Phase 10 performance evidence

This file intentionally contains no invented latency figures. The prototype remains a synthetic,
educational demo and these measurements are engineering evidence, not clinical performance claims.

## Harness

Run `k6 run tools/load/observations.js` only against disposable synthetic services after setting
`RPM_LOAD_TOKENS_FILE` to a local JSON array of one access token per synthetic patient. The harness
requires 1,000 distinct patient tokens by default, posts to `POST /api/v1/observations` across five
concurrent virtual users, and emits
the HTTP duration/error rate plus the server-reported `alert_creation_latency` metric (from
request receipt through synchronous deterministic alert persistence). It does not contain
tokens, patient data, or a fallback identity.

## Measured results

On 2026-11-05, the harness completed one local run on the Windows Codex desktop host using Docker
Desktop, a separately named disposable `rpm_phase10_load` PostgreSQL database, and the Phase 10
backend container. It submitted one 105 mg/dL synthetic glucose observation for each of 1,000
distinct synthetic patient identities through five concurrent virtual users. The run completed in
14.9 seconds with 0/1,000 failed HTTP requests.

| Measurement | p50 | p95 | p99 | maximum |
| --- | ---: | ---: | ---: | ---: |
| `POST /api/v1/observations` duration | 71.93 ms | 95.61 ms | 115.98 ms | 152.68 ms |
| Synchronous alert-creation latency | 25.12 ms | 38.55 ms | 45.29 ms | 62.43 ms |

This is a single local, disposable-synthetic engineering measurement. It is not a production
capacity commitment, clinical performance measure, real-time-monitoring claim, or clinical
validation. The harness, token file, and temporary database are not retained as product data.

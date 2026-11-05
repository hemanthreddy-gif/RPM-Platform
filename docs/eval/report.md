# Evaluation report

Demo with synthetic data. Not for medical use.

Regenerate from repository root: `backend\.venv\Scripts\python.exe backend/eval/report.py` (or `uv run --project backend python backend/eval/report.py`). Results are local offline engineering checks, not clinical evidence, validation, or clinician approval. Fixtures remain unreviewed and require clinician approval.

## Food evaluation

The selected feature is patient photo submission followed by physician comments, not automated food recognition or nutrition estimation. Item precision/recall, nutrient MAE/MAPE and estimate-correction rates are therefore **not applicable**; no estimates are generated. A licensed food dataset is not a prerequisite for this workflow. The retained `food_metrics` helper is unused by this feature.

Synthetic photo-review unit checks: **Passed**, 7 passed, 0 failed, 0 skipped. These exercise image normalization and rejection, blank-comment validation, and opaque object-store failure. They do not assess comment quality, clinical benefit, user comprehension, the full authenticated workflow, or real photos. Separate [PostgreSQL authorization tests](../../backend/tests/test_phase7_postgres_integration.py) require a configured disposable database; their result is not inferred from this unit run. Human review findings remain pending.

## Summary faithfulness

200 deterministic AI-off summaries, one synthetic fact and source each. Unsupported-number rate: 0/200 (0.0%); uncited-claim rate: 0/200 (0.0%); banned-content rate: 0/200 (0.0%). These lexical and citation-presence checks do not establish semantic faithfulness or generalize to an AI provider, real patients or varied clinical contexts. The check uses known synthetic values and source IDs, and evaluates patient text only.

## Red team

Existing Phase 8 adversarial regression cases: 50/50 (100.0%) passed. These cases verify that untrusted strings are not supplied to the deterministic renderer; they do not test a live model or comprehensive injection resistance. Each failed input below requires a regression test and investigation before completion.

None.

## Alert evaluation

Twelve hand-labelled synthetic single-reading glucose and blood-pressure scenarios, labelled against the same unreviewed demo fixture: TP 7, TN 5, FP 0, FN 0. Sensitivity 7/7 (100.0%); specificity 5/5 (100.0%); false-positive rate 0/5 (0.0%). Labels are not independent clinical ground truth. Mean local pure evaluator execution time: 0.0164 ms across twelve calls; this is not end-to-end alert or notification latency. No delivery-latency evaluation was performed here. See [performance evidence](performance.md) for separately measured synchronous alert creation. Small sample and local timing are not evidence of clinical effectiveness or real-time performance.

## Human findings and limitations

A [synthetic automated walkthrough](automated-walkthrough.md) records code-review findings and fixes. It is not participant feedback, a SUS score, or clinician approval.

- Usability: recruitment of at least five participants, task outcomes and SUS scores are pending; a [session protocol](human-protocol.md) is prepared.
- Clinician or faculty feedback on thresholds and wording: pending; no approval record exists.
- No real-patient evaluation, generalizable model evaluation, or clinical validation has been performed. The selected meal workflow provides no nutrient estimates.
- Phase 10 release-gate exceptions, unverified remote CI/ZAP, overall coverage below 80%, invalid mutmut score, and default Turbopack build failure remain open; see [progress](../PROGRESS.md) and [security exceptions](../security-exceptions.md).
- The [safety case](../safety-case.md) maps hazards to tests or explicit gaps.

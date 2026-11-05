# Synthetic-demo safety case and hazard log

Demo with synthetic data. Not for medical use. This is a risk-management structure inspired by
medical-software practice, not a claim of standards compliance, clinical validation or clinician
approval. Clinical fixtures are unreviewed and retain `requires_clinician_approval: true`. Tests
are engineering evidence with the limitations recorded in the [evaluation report](eval/report.md).
The project owner owns all residual risks and gaps below.

| Hazard | Cause | Existing control | Test or documented gap | Residual risk |
| --- | --- | --- | --- | --- |
| Misleading meal feedback | A comment is incorrect or mistaken for an automated nutrient estimate | Photo review only; no nutrient estimate is generated, comments are attributed to the physician | [Meal-photo tests](../backend/tests/test_meal_photo_review.py); [authorization tests](../backend/tests/test_phase7_postgres_integration.py); gap: no review of comment quality | Comments may be misunderstood or inaccurate; no clinician review or usability evidence is available. |
| Missed alert | Incorrect rule or lost transaction | Isolated deterministic rules, boundary tests, atomic alert/outbox | [Rule tests](../backend/tests/test_clinical_rule_evaluator.py); [transaction tests](../backend/tests/test_phase4_postgres_integration.py) | Fixtures are synthetic and unreviewed; no valid mutation score or clinical sensitivity evidence. |
| Delayed notification | Worker, Redis or delivery outage | Persistent outbox, retry and dead-letter state | [Delivery tests](../backend/tests/test_phase4_postgres_integration.py); [Phase 10 evidence](plans/phase-10.md) | Delivery may be delayed; synthetic evaluator timing is not notification latency. |
| Unsafe AI text | Fabrication or injected instructions | Typed facts and validation; deterministic patient rendering and fallback | [Grounded and adversarial tests](../backend/tests/test_phase8_grounded_insights.py) | Lexical checks cannot guarantee semantic safety; provider draft requires review. |
| Wrong-patient data | Authorization or relationship failure | Purpose-specific consent, relationships, RLS and audit | [Access integration tests](../backend/tests/test_phase4_postgres_integration.py) | Local synthetic tests cannot establish absence of all access defects. |
| Stale data shown as current | Missing or misunderstood timestamps | Source timestamps and data-age UI | Gap: no dedicated data-age display regression test or independent usability validation | Users may misunderstand age; human usability testing is pending. |
| Device misreads | Incorrect payload, provenance or duplicate upload | Device authentication, validation and shared observation path | [Device integration tests](../backend/tests/test_phase9_postgres_integration.py); gap: no real device accuracy evaluation | Simulator does not establish hardware accuracy or clinical performance. |

Release-gate exceptions, unresolved coverage, mutation testing and Turbopack debt are carried in
[progress](PROGRESS.md) and [security exceptions](security-exceptions.md). Human usability and
clinical/faculty review are pending; do not infer approval from this document.

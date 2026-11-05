"""Offline synthetic evaluation; run from repository root with the project Python."""

# ruff: noqa: E501
from __future__ import annotations

import re
import subprocess
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.ai.analytics import AnalyticFact  # noqa: E402
from app.ai.writer import build_packet, create_summary_content  # noqa: E402
from app.clinical_rules.evaluator import evaluate  # noqa: E402
from app.clinical_rules.loader import load_rules  # noqa: E402
from app.clinical_rules.models import Observation, PatientContext  # noqa: E402


def ratio(numerator: int, denominator: int) -> str:
    return (
        f"{numerator}/{denominator} ({100 * numerator / denominator:.1f}%)"
        if denominator
        else "N/A (zero denominator)"
    )


def food_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    """Score paired meal results. Sets are normalized item labels; zeros excluded from MAPE."""
    tp = fp = fn = corrections = 0
    errors: dict[str, list[float]] = {"calories": [], "carbohydrate": []}
    percentages: dict[str, list[float]] = {"calories": [], "carbohydrate": []}
    for row in rows:
        expected = {str(x).strip().casefold() for x in row["reference_items"]}  # type: ignore[union-attr]
        predicted = {str(x).strip().casefold() for x in row["predicted_items"]}  # type: ignore[union-attr]
        tp += len(expected & predicted)
        fp += len(predicted - expected)
        fn += len(expected - predicted)
        corrections += bool(row["corrected"])
        for nutrient in errors:
            reference = float(str(row[f"reference_{nutrient}"]))
            prediction = float(str(row[f"predicted_{nutrient}"]))
            if reference < 0 or prediction < 0:
                raise ValueError("Nutrient values must be nonnegative")
            error = abs(reference - prediction)
            errors[nutrient].append(error)
            if reference != 0:
                percentages[nutrient].append(100 * error / reference)
    result: dict[str, object] = {
        "precision": ratio(tp, tp + fp),
        "recall": ratio(tp, tp + fn),
        "correction": ratio(corrections, len(rows)),
    }
    for nutrient in errors:
        result[f"{nutrient}_mae"] = (
            sum(errors[nutrient]) / len(errors[nutrient]) if errors[nutrient] else None
        )
        result[f"{nutrient}_mape"] = (
            sum(percentages[nutrient]) / len(percentages[nutrient])
            if percentages[nutrient]
            else None
        )
        result[f"{nutrient}_mape_n"] = len(percentages[nutrient])
    return result


def summary_evaluation() -> tuple[int, int, int, int]:
    unsupported = uncited = banned = claims = 0
    for i in range(200):
        value = Decimal(80 + i % 100)
        fact = AnalyticFact("glucose.mean", "Glucose mean", value, "mg/dL", 3, (UUID(int=i + 1),))
        packet = build_packet(UUID(int=i + 1000), "synthetic window", [fact])
        content = create_summary_content(packet)
        text = str(content["patient_text"])
        claims += 1
        numbers = re.findall(r"(?<![A-Za-z])[+-]?\d+(?:\.\d+)?", text)
        unsupported += any(number not in {str(value), "3"} for number in numbers)
        uncited += not bool(content["patient_citation_fact_ids"]) or not fact.observation_ids
        banned += any(
            term in text.lower()
            for term in ("diagnos", "prescrib", "change your dose", "stop taking", "emergency")
        )
    return claims, unsupported, uncited, banned


def alert_evaluation() -> tuple[int, int, int, int, float]:
    # Labels are illustrative expectations for the existing unreviewed demo fixtures.
    scenarios = [
        ("glucose", "53", None, True),
        ("glucose", "54", None, True),
        ("glucose", "69", None, True),
        ("glucose", "70", None, False),
        ("glucose", "100", None, False),
        ("glucose", "299", None, False),
        ("glucose", "300", None, True),
        ("blood_pressure", "179", "119", False),
        ("blood_pressure", "180", "80", True),
        ("blood_pressure", "120", "120", True),
        ("blood_pressure", "89", "60", True),
        ("blood_pressure", "120", "80", False),
    ]
    rules = load_rules(ROOT / "backend" / "rules")
    now = datetime(2026, 10, 1, tzinfo=UTC)
    tp = tn = fp = fn = 0
    elapsed = 0.0
    for kind, value, diastolic, expected in scenarios:
        obs = (
            Observation(type=kind, value=Decimal(value), measured_at=now)
            if kind == "glucose"
            else Observation(
                type=kind,
                components={"systolic": Decimal(value), "diastolic": Decimal(str(diastolic))},
                measured_at=now,
            )
        )
        start = perf_counter()
        actual = bool(evaluate(obs, PatientContext(), rules, now))
        elapsed += perf_counter() - start
        tp += actual and expected
        tn += not actual and not expected
        fp += actual and not expected
        fn += not actual and expected
    return tp, tn, fp, fn, elapsed * 1000 / len(scenarios)


def red_team() -> tuple[int, list[str]]:
    # Execute the existing regression cases, retaining each failed input for follow-up.
    sys.path.insert(0, str(ROOT / "backend" / "tests"))
    from test_phase8_grounded_insights import (  # noqa: PLC0415
        _ADVERSARIAL_INPUTS,
        test_red_team_untrusted_text_cannot_change_safe_template,
    )

    failures = []
    for item in _ADVERSARIAL_INPUTS:
        try:
            test_red_team_untrusted_text_cannot_change_safe_template(item)
        except Exception as exc:
            failures.append(f"{item!r}: {type(exc).__name__}: {exc}")
    return len(_ADVERSARIAL_INPUTS), failures


def meal_review_evaluation() -> tuple[int, int, int, str]:
    """Run synthetic photo normalization, comment validation, and storage failure tests."""
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-o",
                "addopts=",
                "-q",
                "backend/tests/test_meal_photo_review.py",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 0, 0, 0, f"Not run: {type(exc).__name__}"
    output = result.stdout + "\n" + result.stderr

    def count(label: str) -> int:
        match = re.search(rf"(\d+) {label}", output)
        return int(match.group(1)) if match else 0

    passed, failed, skipped = count("passed"), count("failed"), count("skipped")
    status = (
        "Passed"
        if result.returncode == 0 and passed > 0 and failed == 0 and skipped == 0
        else "Failed or unavailable"
    )
    return passed, failed, skipped, status


def generate_report(meal_result: tuple[int, int, int, str] | None = None) -> str:
    claims, unsupported, uncited, banned = summary_evaluation()
    tp, tn, fp, fn, latency = alert_evaluation()
    total, failures = red_team()
    meal_passed, meal_failed, meal_skipped, meal_status = (
        meal_result if meal_result is not None else meal_review_evaluation()
    )
    failure_text = "None." if not failures else "\n".join(f"- {item}" for item in failures)
    return f"""# Evaluation report

Demo with synthetic data. Not for medical use.

Regenerate from repository root: `backend\\.venv\\Scripts\\python.exe backend/eval/report.py` (or `uv run --project backend python backend/eval/report.py`). Results are local offline engineering checks, not clinical evidence, validation, or clinician approval. Fixtures remain unreviewed and require clinician approval.

## Food evaluation

The selected feature is patient photo submission followed by physician comments, not automated food recognition or nutrition estimation. Item precision/recall, nutrient MAE/MAPE and estimate-correction rates are therefore **not applicable**; no estimates are generated. A licensed food dataset is not a prerequisite for this workflow. The retained `food_metrics` helper is unused by this feature.

Synthetic photo-review unit checks: **{meal_status}**, {meal_passed} passed, {meal_failed} failed, {meal_skipped} skipped. These exercise image normalization and rejection, blank-comment validation, and opaque object-store failure. They do not assess comment quality, clinical benefit, user comprehension, the full authenticated workflow, or real photos. Separate [PostgreSQL authorization tests](../../backend/tests/test_phase7_postgres_integration.py) require a configured disposable database; their result is not inferred from this unit run. Human review findings remain pending.

## Summary faithfulness

{claims} deterministic AI-off summaries, one synthetic fact and source each. Unsupported-number rate: {ratio(unsupported, claims)}; uncited-claim rate: {ratio(uncited, claims)}; banned-content rate: {ratio(banned, claims)}. These lexical and citation-presence checks do not establish semantic faithfulness or generalize to an AI provider, real patients or varied clinical contexts. The check uses known synthetic values and source IDs, and evaluates patient text only.

## Red team

Existing Phase 8 adversarial regression cases: {ratio(total - len(failures), total)} passed. These cases verify that untrusted strings are not supplied to the deterministic renderer; they do not test a live model or comprehensive injection resistance. Each failed input below requires a regression test and investigation before completion.

{failure_text}

## Alert evaluation

Twelve hand-labelled synthetic single-reading glucose and blood-pressure scenarios, labelled against the same unreviewed demo fixture: TP {tp}, TN {tn}, FP {fp}, FN {fn}. Sensitivity {ratio(tp, tp + fn)}; specificity {ratio(tn, tn + fp)}; false-positive rate {ratio(fp, fp + tn)}. Labels are not independent clinical ground truth. Mean local pure evaluator execution time: {latency:.4f} ms across twelve calls; this is not end-to-end alert or notification latency. No delivery-latency evaluation was performed here. See [performance evidence](performance.md) for separately measured synchronous alert creation. Small sample and local timing are not evidence of clinical effectiveness or real-time performance.

## Human findings and limitations

A [synthetic automated walkthrough](automated-walkthrough.md) records code-review findings and fixes. It is not participant feedback, a SUS score, or clinician approval.

- Usability: recruitment of at least five participants, task outcomes and SUS scores are pending; a [session protocol](human-protocol.md) is prepared.
- Clinician or faculty feedback on thresholds and wording: pending; no approval record exists.
- No real-patient evaluation, generalizable model evaluation, or clinical validation has been performed. The selected meal workflow provides no nutrient estimates.
- Phase 10 release-gate exceptions, unverified remote CI/ZAP, overall coverage below 80%, invalid mutmut score, and default Turbopack build failure remain open; see [progress](../PROGRESS.md) and [security exceptions](../security-exceptions.md).
- The [safety case](../safety-case.md) maps hazards to tests or explicit gaps.
"""


if __name__ == "__main__":
    meal_result = meal_review_evaluation()
    report = generate_report(meal_result)
    (ROOT / "docs" / "eval" / "report.md").write_text(report, encoding="utf-8")
    print("Wrote docs/eval/report.md")
    if red_team()[1]:
        raise SystemExit("Red-team failures require regression tests")
    if meal_result[3] != "Passed":
        raise SystemExit("Meal-review unit evaluation failed or could not run")

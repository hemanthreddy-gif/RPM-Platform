"""Regression checks for evaluation denominators and synthetic evidence."""

from eval.report import alert_evaluation, food_metrics, ratio, red_team, summary_evaluation


def test_food_scoring_excludes_zero_references_from_mape() -> None:
    rows = [
        {
            "reference_items": ["Rice", "Dal"],
            "predicted_items": ["rice", "Roti"],
            "reference_calories": 100,
            "predicted_calories": 120,
            "reference_carbohydrate": 0,
            "predicted_carbohydrate": 5,
            "corrected": True,
        },
        {
            "reference_items": ["dal"],
            "predicted_items": ["dal"],
            "reference_calories": 0,
            "predicted_calories": 10,
            "reference_carbohydrate": 10,
            "predicted_carbohydrate": 5,
            "corrected": False,
        },
    ]
    result = food_metrics(rows)
    assert result["precision"] == "2/3 (66.7%)"
    assert result["recall"] == "2/3 (66.7%)"
    assert result["calories_mae"] == 15
    assert result["calories_mape"] == 20
    assert result["calories_mape_n"] == 1
    assert result["carbohydrate_mape"] == 50
    assert result["correction"] == "1/2 (50.0%)"
    assert ratio(0, 0) == "N/A (zero denominator)"
    assert food_metrics([])["calories_mape"] is None


def test_synthetic_evaluations_exercise_existing_paths() -> None:
    assert summary_evaluation() == (200, 0, 0, 0)
    assert alert_evaluation()[:4] == (7, 5, 0, 0)
    count, failures = red_team()
    assert count >= 50
    assert not failures


def test_meal_review_evaluation_reports_failure_and_skips(monkeypatch) -> None:
    from subprocess import CompletedProcess

    from eval import report

    def failing_run(*args, **kwargs):
        return CompletedProcess(args, 1, stdout="1 passed, 1 failed, 2 skipped", stderr="")

    monkeypatch.setattr(report.subprocess, "run", failing_run)
    assert report.meal_review_evaluation() == (1, 1, 2, "Failed or unavailable")

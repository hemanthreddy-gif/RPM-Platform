from tools.synth_data.seed import EDGE_CASES, build_cohort, canonical_hash


def test_same_seed_and_anchor_produce_same_hash() -> None:
    first = build_cohort(7, 42, "2026-10-01")
    second = build_cohort(7, 42, "2026-10-01")
    assert canonical_hash(*first) == canonical_hash(*second)


def test_named_edge_cases_are_present_without_invalid_database_rows() -> None:
    records, invalid_inputs = build_cohort(7, 42, "2026-10-01")
    scenarios = {record.payload.get("scenario") for record in records if record.kind == "patient"}
    assert set(EDGE_CASES).issubset(scenarios)
    assert {item["scenario"] for item in invalid_inputs} == {
        "duplicate_submission",
        "implausible_value",
    }

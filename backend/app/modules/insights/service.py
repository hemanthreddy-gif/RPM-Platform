"""Authorized assembly and immutable persistence of Phase 8 grounded insights."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from json import dumps, loads
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai.analytics import (
    AnalyticFact,
    AnalyticObservation,
    DoseReport,
    blood_pressure_facts,
    bp_missed_dose_comparison,
    fasting_glucose_change,
    glucose_facts,
)
from app.ai.writer import PROMPT_VERSION, SCHEMA_VERSION, build_packet, create_summary_content


def _object(value: object) -> dict[str, object]:
    if isinstance(value, str):
        loaded = loads(value)
        if isinstance(loaded, dict):
            return loaded
        raise ValueError("Expected JSON object")
    if isinstance(value, dict):
        return value
    raise ValueError("Expected JSON object")


def _observations(
    session: Session, patient_id: UUID, start: datetime, end: datetime
) -> list[AnalyticObservation]:
    rows = (
        session.execute(
            text("""SELECT o.id, o.type::text AS type, o.value_num, o.components, o.context, o.measured_at
          FROM observations o WHERE o.patient_id = :patient_id AND o.measured_at >= :start AND o.measured_at <= :end
          AND NOT EXISTS (SELECT 1 FROM observations child WHERE child.supersedes_id = o.id)
          AND o.type IN ('glucose', 'blood_pressure') ORDER BY o.measured_at"""),
            {"patient_id": patient_id, "start": start, "end": end},
        )
        .mappings()
        .all()
    )
    result: list[AnalyticObservation] = []
    for row in rows:
        context = _object(row["context"])
        components = _object(row["components"])
        if row["type"] == "glucose":
            result.append(
                AnalyticObservation(
                    row["id"],
                    row["measured_at"],
                    "glucose",
                    Decimal(str(row["value_num"])),
                    fasting=context.get("fasting") is True,
                )
            )
        else:
            systolic, diastolic = components.get("systolic"), components.get("diastolic")
            if systolic is not None and diastolic is not None:
                result.append(
                    AnalyticObservation(
                        row["id"],
                        row["measured_at"],
                        "blood_pressure",
                        systolic=Decimal(str(systolic)),
                        diastolic=Decimal(str(diastolic)),
                    )
                )
    return result


def _reports(
    session: Session, patient_id: UUID, start: datetime, end: datetime
) -> list[DoseReport]:
    rows = (
        session.execute(
            text("""SELECT d.id, d.scheduled_for, d.status::text AS status FROM dose_events d
          JOIN medications m ON m.id = d.medication_id WHERE m.patient_id = :patient_id
          AND d.schedule_state = 'active' AND d.scheduled_for >= :start AND d.scheduled_for <= :end
          AND d.status IN ('taken', 'missed', 'skipped')"""),
            {"patient_id": patient_id, "start": start, "end": end},
        )
        .mappings()
        .all()
    )
    return [DoseReport(row["id"], row["scheduled_for"], row["status"]) for row in rows]


def build_facts(
    session: Session, *, patient_id: UUID, start: datetime, end: datetime
) -> list[AnalyticFact]:
    observations = _observations(session, patient_id, start, end)
    target = (
        session.execute(
            text("""SELECT low, high FROM monitoring_targets WHERE patient_id = :patient_id
          AND type = 'glucose' AND context = 'default' ORDER BY version DESC LIMIT 1"""),
            {"patient_id": patient_id},
        )
        .mappings()
        .one_or_none()
    )
    low = Decimal(str(target["low"])) if target and target["low"] is not None else None
    high = Decimal(str(target["high"])) if target and target["high"] is not None else None
    return [
        *glucose_facts(observations, target_low=low, target_high=high),
        fasting_glucose_change(observations),
        *blood_pressure_facts(observations),
        bp_missed_dose_comparison(observations, _reports(session, patient_id, start, end)),
    ]


def _response(row: object) -> dict[str, object]:
    mapped = dict(cast(dict[str, object], row))
    for key in ("id", "patient_id", "supersedes_id", "reviewed_by"):
        if mapped.get(key) is not None:
            mapped[key] = str(mapped[key])
    mapped["content"] = _object(mapped["content"])
    mapped["input_refs"] = _object(mapped["input_refs"])
    return mapped


def create_summary(
    session: Session,
    *,
    patient_id: UUID,
    created_by: UUID,
    start: datetime,
    end: datetime,
    supersedes_id: UUID | None = None,
) -> dict[str, object]:
    facts = build_facts(session, patient_id=patient_id, start=start, end=end)
    packet = build_packet(
        patient_id, f"{start.date().isoformat()} to {end.date().isoformat()}", facts
    )
    content = create_summary_content(packet)
    previous_version = 0
    if supersedes_id is not None:
        previous = (
            session.execute(
                text("SELECT patient_id, artifact_version FROM ai_artifacts WHERE id = :id"),
                {"id": supersedes_id},
            )
            .mappings()
            .one_or_none()
        )
        if previous is None or previous["patient_id"] != patient_id:
            raise ValueError("Summary artifact not found")
        previous_version = int(previous["artifact_version"])
    row = (
        session.execute(
            text("""INSERT INTO ai_artifacts
          (id, patient_id, kind, content, model, prompt_version, input_refs, provider, schema_version, artifact_version, supersedes_id, created_by)
          VALUES (:id, :patient_id, 'summary', CAST(:content AS jsonb), NULL, :prompt_version,
          CAST(:input_refs AS jsonb), 'deterministic-template', :schema_version, :version, :supersedes_id, :created_by)
          RETURNING id, patient_id, kind::text, status::text, artifact_version, supersedes_id,
          content, input_refs, created_at, reviewed_at, approval_invalidated_at"""),
            {
                "id": uuid4(),
                "patient_id": patient_id,
                "content": dumps(content),
                "prompt_version": PROMPT_VERSION,
                "input_refs": dumps(packet.as_dict()),
                "schema_version": SCHEMA_VERSION,
                "version": previous_version + 1,
                "supersedes_id": supersedes_id,
                "created_by": created_by,
            },
        )
        .mappings()
        .one()
    )
    if supersedes_id is not None:
        session.execute(
            text("""UPDATE ai_artifacts SET approval_invalidated_at = now()
              WHERE id = :id AND status = 'approved' AND approval_invalidated_at IS NULL"""),
            {"id": supersedes_id},
        )
    return _response(row)


def latest_insights(session: Session, *, patient_id: UUID) -> list[dict[str, object]]:
    rows = (
        session.execute(
            text("""SELECT id, patient_id, kind::text, status::text, artifact_version, supersedes_id,
      content, input_refs, created_at, reviewed_at, approval_invalidated_at
      FROM ai_artifacts WHERE patient_id = :patient_id AND kind IN ('insight', 'summary')
      ORDER BY created_at DESC"""),
            {"patient_id": patient_id},
        )
        .mappings()
        .all()
    )
    return [_response(row) for row in rows]


def review_summary(
    session: Session, *, artifact_id: UUID, reviewer_id: UUID, decision: str
) -> tuple[dict[str, object], UUID]:
    row = (
        session.execute(
            text("""UPDATE ai_artifacts SET status = CAST(:decision AS artifact_status),
      reviewed_by = :reviewer_id, reviewed_at = now()
      WHERE id = :id AND kind = 'summary' RETURNING id, patient_id, kind::text, status::text,
      artifact_version, supersedes_id, content, input_refs, created_at, reviewed_at,
      approval_invalidated_at"""),
            {"id": artifact_id, "reviewer_id": reviewer_id, "decision": decision},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise ValueError("Summary artifact not found")
    session.execute(
        text("""INSERT INTO artifact_reviews
          (id, artifact_id, artifact_version, reviewer_id, decision)
          VALUES (:id, :artifact_id, :artifact_version, :reviewer_id, :decision)"""),
        {
            "id": uuid4(),
            "artifact_id": artifact_id,
            "artifact_version": row["artifact_version"],
            "reviewer_id": reviewer_id,
            "decision": decision,
        },
    )
    return _response(row), row["patient_id"]


def range_for_days(days: int) -> tuple[datetime, datetime]:
    end = datetime.now(UTC)
    return end - timedelta(days=days), end

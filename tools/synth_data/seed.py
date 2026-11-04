"""Deterministic, synthetic-only cohort generator for local development."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

NAMESPACE = uuid.UUID("09e18dfd-8a81-4dce-b531-6ab1ca472a5d")
EDGE_CASES = (
    "recurrent_hypoglycaemia",
    "bp_crisis_reading",
    "mmol_l_user",
    "long_data_gap",
    "duplicate_submission",
    "implausible_value",
    "manual_and_device_mix",
)


@dataclass(frozen=True)
class SyntheticRecord:
    id: str
    kind: str
    payload: dict[str, Any]


def stable_id(seed: int, label: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{seed}:{label}"))


def build_cohort(
    patients: int, seed: int, anchor_date: str
) -> tuple[list[SyntheticRecord], list[dict[str, Any]]]:
    """Build stable records and invalid input scenarios without connecting to a database."""
    anchor = datetime.fromisoformat(f"{anchor_date}T12:00:00+00:00")
    rng = random.Random(seed)
    records: list[SyntheticRecord] = []
    invalid_inputs: list[dict[str, Any]] = []
    physician_user_id = stable_id(seed, "physician-user")
    physician_id = stable_id(seed, "physician")
    records.extend(
        [
            SyntheticRecord(
                physician_user_id,
                "user",
                {"email": "dr.demo@example.invalid", "role": "physician"},
            ),
            SyntheticRecord(
                physician_id,
                "physician",
                {"user_id": physician_user_id, "registration_no": "SYN-0001"},
            ),
        ]
    )
    for number in range(1, patients + 1):
        patient_id = stable_id(seed, f"patient:{number}")
        user_id = stable_id(seed, f"patient-user:{number}")
        consent_id = stable_id(seed, f"consent:{number}")
        scenario = EDGE_CASES[number - 1] if number <= len(EDGE_CASES) else "routine"
        records.extend(
            [
                SyntheticRecord(
                    user_id,
                    "user",
                    {
                        "email": f"test.patient.{number:03d}@example.invalid",
                        "role": "patient",
                    },
                ),
                SyntheticRecord(
                    patient_id,
                    "patient",
                    {
                        "user_id": user_id,
                        "display_name": f"Test Patient {number:03d}",
                        "timezone": "Asia/Kolkata",
                        "scenario": scenario,
                    },
                ),
                SyntheticRecord(
                    consent_id,
                    "consent",
                    {
                        "patient_id": patient_id,
                        "purpose": "monitoring",
                        "version": "demo-v1",
                    },
                ),
                SyntheticRecord(
                    stable_id(seed, f"relationship:{number}"),
                    "care_relationship",
                    {
                        "patient_id": patient_id,
                        "physician_id": physician_id,
                        "consent_id": consent_id,
                    },
                ),
            ]
        )
        for day in range(90):
            if scenario == "long_data_gap" and 20 <= day < 55:
                continue
            measured = anchor - timedelta(days=89 - day, hours=4)
            glucose = round(105 + rng.uniform(-18, 24), 1)
            if scenario == "recurrent_hypoglycaemia" and day % 9 == 0:
                glucose = 52.0
            original_unit = (
                "mmol/L" if scenario == "mmol_l_user" and day % 10 == 0 else "mg/dL"
            )
            original_value = (
                round(glucose / 18.016, 2) if original_unit == "mmol/L" else glucose
            )
            records.append(
                SyntheticRecord(
                    stable_id(seed, f"obs:{number}:{day}:glu"),
                    "observation",
                    {
                        "patient_id": patient_id,
                        "type": "glucose",
                        "value_num": glucose,
                        "unit": "mg/dL",
                        "original_value": original_value,
                        "original_unit": original_unit,
                        "measured_at": measured.isoformat(),
                        "source": "device"
                        if scenario == "manual_and_device_mix" and day % 2
                        else "manual",
                        "context": {"kind": "fasting"},
                    },
                )
            )
            systolic = 122 + rng.randint(-10, 12)
            diastolic = 78 + rng.randint(-7, 8)
            if scenario == "bp_crisis_reading" and day == 45:
                systolic, diastolic = 182, 121
            records.append(
                SyntheticRecord(
                    stable_id(seed, f"obs:{number}:{day}:bp"),
                    "observation",
                    {
                        "patient_id": patient_id,
                        "type": "blood_pressure",
                        "components": {"systolic": systolic, "diastolic": diastolic},
                        "unit": "mmHg",
                        "original_value": systolic,
                        "original_unit": "mmHg",
                        "measured_at": measured.isoformat(),
                        "source": "manual",
                        "context": {},
                    },
                )
            )
        if scenario in {"duplicate_submission", "implausible_value"}:
            invalid_inputs.append(
                {
                    "scenario": scenario,
                    "patient_id": patient_id,
                    "note": "test input only; never insert",
                }
            )
    return records, invalid_inputs


def canonical_hash(
    records: list[SyntheticRecord], invalid_inputs: list[dict[str, Any]]
) -> str:
    payload = {
        "records": [asdict(item) for item in records],
        "invalid_inputs": invalid_inputs,
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def insert_development_records(records: list[SyntheticRecord]) -> None:
    """Insert the manifest into a local disposable database; never accept a production URL."""
    import psycopg

    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://rpm:development-only-change-me@localhost:5432/rpm",
    ).replace("postgresql+psycopg://", "postgresql://")
    if "localhost" not in url or not url.rstrip("/").endswith("/rpm"):
        raise RuntimeError(
            "Synthetic seed is allowed only for the local disposable rpm database"
        )
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM users")
        existing_users = cursor.fetchone()
        if existing_users is None:
            raise RuntimeError("Could not verify whether the local database is empty")
        if existing_users[0]:
            raise RuntimeError(
                "Local database is not empty; do not overwrite accepted work"
            )
        for record in records:
            data = record.payload
            if record.kind == "user":
                cursor.execute(
                    "INSERT INTO users (id, email, role) VALUES (%s, %s, %s)",
                    (record.id, data["email"], data["role"]),
                )
            elif record.kind == "physician":
                cursor.execute(
                    "INSERT INTO physicians (id, user_id, registration_no) VALUES (%s, %s, %s)",
                    (record.id, data["user_id"], data["registration_no"]),
                )
            elif record.kind == "patient":
                cursor.execute(
                    "INSERT INTO patients (id, user_id, display_name, timezone) VALUES (%s, %s, %s, %s)",
                    (
                        record.id,
                        data["user_id"],
                        data["display_name"],
                        data["timezone"],
                    ),
                )
            elif record.kind == "consent":
                cursor.execute(
                    "INSERT INTO consents (id, patient_id, purpose, version, granted_at) VALUES (%s, %s, %s, %s, now())",
                    (record.id, data["patient_id"], data["purpose"], data["version"]),
                )
            elif record.kind == "care_relationship":
                cursor.execute(
                    "INSERT INTO care_relationships (id, patient_id, physician_id, consent_id, status, started_at) VALUES (%s, %s, %s, %s, 'active', now())",
                    (
                        record.id,
                        data["patient_id"],
                        data["physician_id"],
                        data["consent_id"],
                    ),
                )
            elif record.kind == "observation":
                cursor.execute(
                    """INSERT INTO observations
                    (id, patient_id, type, value_num, components, unit, original_value, original_unit, measured_at, source, context)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s::jsonb)""",
                    (
                        record.id,
                        data["patient_id"],
                        data["type"],
                        data.get("value_num"),
                        json.dumps(data.get("components", {})),
                        data["unit"],
                        data["original_value"],
                        data["original_unit"],
                        data["measured_at"],
                        data["source"],
                        json.dumps(data["context"]),
                    ),
                )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a synthetic RPM cohort manifest; no real data."
    )
    parser.add_argument("--patients", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--anchor-date", default="2026-10-01")
    parser.add_argument("--output", default="data/synthetic/cohort-manifest.json")
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help="Do not insert into the local database",
    )
    args = parser.parse_args()
    if args.patients < len(EDGE_CASES):
        raise SystemExit(
            f"--patients must be at least {len(EDGE_CASES)} to include every named scenario"
        )
    records, invalid_inputs = build_cohort(args.patients, args.seed, args.anchor_date)
    digest = canonical_hash(records, invalid_inputs)
    output = {
        "synthetic_only": True,
        "seed": args.seed,
        "anchor_date": args.anchor_date,
        "sha256": digest,
        "records": [asdict(r) for r in records],
        "invalid_input_scenarios": invalid_inputs,
    }
    from pathlib import Path

    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, sort_keys=True, indent=2), encoding="utf-8")
    if not args.manifest_only:
        insert_development_records(records)
    print(f"Synthetic cohort manifest written to {path}; canonical SHA-256: {digest}")


if __name__ == "__main__":
    main()

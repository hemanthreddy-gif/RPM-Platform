"""Small explicitly-R4 JSON mapper for documented synthetic-demo interoperability subset."""

from __future__ import annotations

from typing import Any

FHIR_VERSION = "4.0.1"
LOINC = "http://loinc.org"
UCUM = "http://unitsofmeasure.org"
BP_PANEL = "85354-9"
SYSTOLIC = "8480-6"
DIASTOLIC = "8462-4"


def patient_resource(row: dict[str, Any]) -> dict[str, object]:
    return {
        "resourceType": "Patient",
        "id": str(row["id"]),
        "meta": {"versionId": FHIR_VERSION},
        "name": [{"text": row["display_name"]}],
    }


def practitioner_resource(row: dict[str, Any]) -> dict[str, object]:
    return {
        "resourceType": "Practitioner",
        "id": str(row["id"]),
        "meta": {"versionId": FHIR_VERSION},
        "identifier": [
            {"system": "urn:rpm:synthetic-registration", "value": row["registration_no"]}
        ],
    }


def _coding(code: str, display: str) -> dict[str, object]:
    return {"coding": [{"system": LOINC, "code": code, "display": display}]}


def observation_resource(row: dict[str, Any]) -> dict[str, object]:
    """Map only explicit glucose coding or the documented BP panel; unknown codes are excluded."""
    base: dict[str, object] = {
        "resourceType": "Observation",
        "id": str(row["id"]),
        "status": "final",
        "subject": {"reference": f"Patient/{row['patient_id']}"},
        "effectiveDateTime": row["measured_at"].isoformat(),
        "issued": row["recorded_at"].isoformat(),
    }
    if row["type"] == "blood_pressure":
        components = row["components"]
        if (
            not isinstance(components, dict)
            or "systolic" not in components
            or "diastolic" not in components
        ):
            raise ValueError("Blood pressure is missing components")
        base["code"] = _coding(BP_PANEL, "Blood pressure panel")
        base["component"] = [
            {
                "code": _coding(SYSTOLIC, "Systolic blood pressure"),
                "valueQuantity": {
                    "value": components["systolic"],
                    "unit": "mm[Hg]",
                    "system": UCUM,
                    "code": "mm[Hg]",
                },
            },
            {
                "code": _coding(DIASTOLIC, "Diastolic blood pressure"),
                "valueQuantity": {
                    "value": components["diastolic"],
                    "unit": "mm[Hg]",
                    "system": UCUM,
                    "code": "mm[Hg]",
                },
            },
        ]
        return base
    metadata = row.get("context", {}).get("fhir") if isinstance(row.get("context"), dict) else None
    if (
        not isinstance(metadata, dict)
        or metadata.get("system") != LOINC
        or not isinstance(metadata.get("code"), str)
        or metadata.get("specimen") != "blood"
    ):
        raise ValueError("Glucose lacks explicit recorded LOINC blood-specimen coding")
    if row["unit"] != "mg/dL":
        raise ValueError("Unsupported glucose UCUM unit")
    base["code"] = _coding(
        metadata["code"], str(metadata.get("display", "Recorded glucose observation"))
    )
    base["valueQuantity"] = {
        "value": row["value"],
        "unit": "mg/dL",
        "system": UCUM,
        "code": "mg/dL",
    }
    return base


def medication_statement_resource(row: dict[str, Any]) -> dict[str, object]:
    return {
        "resourceType": "MedicationStatement",
        "id": str(row["id"]),
        "status": "active",
        "subject": {"reference": f"Patient/{row['patient_id']}"},
        "medicationCodeableConcept": {"text": row["name"]},
        "note": [{"text": "Synthetic physician-authored record; not a prescription."}],
    }


def medication_request_resource(row: dict[str, Any]) -> dict[str, object]:
    return {
        "resourceType": "MedicationRequest",
        "id": str(row["id"]),
        "status": "active",
        "intent": "order",
        "subject": {"reference": f"Patient/{row['patient_id']}"},
        "medicationCodeableConcept": {"text": row["name"]},
        "authoredOn": row["start_date"].isoformat(),
    }


def bundle(resources: list[dict[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{"resource": resource} for resource in resources],
    }
    validate_r4_subset(result)
    return result


def validate_r4_subset(resource: dict[str, object]) -> None:
    """Validate required R4 subset structure, references, and the only supported codings/units."""
    kind = resource.get("resourceType")
    if kind == "Bundle":
        entries = resource.get("entry")
        if not isinstance(entries, list):
            raise ValueError("FHIR Bundle requires entry list")
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("resource"), dict):
                raise ValueError("FHIR Bundle entry requires resource")
            validate_r4_subset(entry["resource"])
        return
    if kind not in {
        "Patient",
        "Practitioner",
        "Observation",
        "MedicationRequest",
        "MedicationStatement",
    } or not isinstance(resource.get("id"), str):
        raise ValueError("Unsupported or malformed FHIR R4 resource")
    if kind == "Observation":
        if resource.get("status") != "final" or not isinstance(resource.get("subject"), dict):
            raise ValueError("FHIR Observation requires final status and subject")
        if "component" in resource:
            components = resource["component"]
            if not isinstance(components, list) or len(components) != 2:
                raise ValueError("FHIR BP requires two components")
        else:
            quantity = resource.get("valueQuantity")
            if (
                not isinstance(quantity, dict)
                or quantity.get("system") != UCUM
                or quantity.get("code") != "mg/dL"
            ):
                raise ValueError("FHIR glucose requires supported UCUM quantity")

"""Facts-packet validation and deterministic rendering for the AI-off safe path."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from re import compile as re_compile
from typing import Protocol
from uuid import UUID

from app.ai.analytics import AnalyticFact

SCHEMA_VERSION = "phase8-facts-v1"
PROMPT_VERSION = "phase8-safe-style-v1"
_NUMBER = re_compile(r"(?<![A-Za-z])[+-]?\d+(?:\.\d+)?")
_BANNED = ("diagnos", "prescrib", "change your dose", "stop taking", "emergency")


@dataclass(frozen=True)
class FactsPacket:
    patient_id: UUID
    window_label: str
    facts: tuple[AnalyticFact, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "patient_id": str(self.patient_id),
            "window_label": self.window_label,
            "facts": [fact.as_dict() for fact in self.facts],
        }


@dataclass(frozen=True)
class DraftClaim:
    text: str
    fact_ids: tuple[str, ...]


@dataclass(frozen=True)
class ProviderDraft:
    claims: tuple[DraftClaim, ...]


@dataclass(frozen=True)
class ValidationResult:
    accepted: bool
    reason: str | None = None


class SummaryProvider(Protocol):
    provider_name: str

    def draft_summary(self, packet: dict[str, object], *, prompt_version: str) -> ProviderDraft:
        """Accept only verified facts and return cited, untrusted draft claims."""


def build_packet(patient_id: UUID, window_label: str, facts: list[AnalyticFact]) -> FactsPacket:
    """Reject empty or source-free usable facts before a packet can reach a provider."""
    for fact in facts:
        if not fact.insufficient_data and not fact.observation_ids and not fact.dose_event_ids:
            raise ValueError(f"Fact {fact.id} has no supporting source")
    return FactsPacket(patient_id=patient_id, window_label=window_label, facts=tuple(facts))


def _render_value(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), "f").rstrip("0").rstrip(".")


def render_patient_text(packet: FactsPacket) -> tuple[str, list[str]]:
    """Render only deterministic, non-diagnostic descriptions from supported facts."""
    rendered: list[str] = []
    citations: list[str] = []
    for fact in packet.facts:
        if fact.insufficient_data or fact.value is None:
            continue
        if fact.id == "glucose.mean":
            rendered.append(
                "Average sampled glucose was "
                f"{_render_value(fact.value)} {fact.unit} across {fact.sample_size} readings."
            )
        elif fact.id == "glucose.sampled_in_target_percentage":
            rendered.append(
                f"{_render_value(fact.value)}% of sampled readings were within the "
                f"physician-defined range ({fact.sample_size} readings; not CGM time in range)."
            )
        elif fact.id == "glucose.fasting_change":
            rendered.append(
                "Fasting sampled glucose changed by "
                f"{_render_value(fact.value)} {fact.unit} from first to last reading; "
                "this is an observed pattern, not a diagnosis."
            )
        elif fact.id in {"bp.systolic_mean", "bp.diastolic_mean"}:
            rendered.append(
                f"{fact.label} was {_render_value(fact.value)} {fact.unit} across "
                f"{fact.sample_size} readings."
            )
        elif fact.id == "bp.self_reported_missed_dose_difference":
            rendered.append(
                "The observed systolic difference on days with self-reported missed doses was "
                f"{_render_value(fact.value)} {fact.unit} ({fact.sample_size} readings); "
                "observed association, not cause."
            )
        else:
            continue
        citations.append(fact.id)
    if not rendered:
        return "Not enough supported data is available for a summary in this period.", []
    return " ".join(rendered), citations


def validate_provider_draft(packet: FactsPacket, draft: ProviderDraft) -> ValidationResult:
    """Check citations, exact fact values, and unsafe language; never licenses patient prose."""
    facts = {
        fact.id: fact
        for fact in packet.facts
        if not fact.insufficient_data and fact.value is not None
    }
    if not draft.claims:
        return ValidationResult(False, "Draft contains no claims")
    for claim in draft.claims:
        normalized = claim.text.lower()
        if not claim.fact_ids:
            return ValidationResult(False, "Every draft claim requires citations")
        if any(identifier not in facts for identifier in claim.fact_ids):
            return ValidationResult(False, "Draft cites an unknown or insufficient fact")
        if any(phrase in normalized for phrase in _BANNED):
            return ValidationResult(False, "Draft contains prohibited clinical language")
        allowed_numbers = {
            _render_value(value)
            for identifier in claim.fact_ids
            if (value := facts[identifier].value) is not None
        }
        numbers = _NUMBER.findall(claim.text)
        if any(
            number not in allowed_numbers
            and number not in {str(facts[identifier].sample_size) for identifier in claim.fact_ids}
            for number in numbers
        ):
            return ValidationResult(False, "Draft contains a number absent from cited facts")
    return ValidationResult(True)


def create_summary_content(
    packet: FactsPacket, provider: SummaryProvider | None = None
) -> dict[str, object]:
    """Always provide deterministic patient text; failed/untrusted prose remains absent."""
    patient_text, citations = render_patient_text(packet)
    content: dict[str, object] = {
        "facts_packet": packet.as_dict(),
        "patient_text": patient_text,
        "patient_citation_fact_ids": citations,
        "physician_draft": None,
        "provider_validation": {"accepted": False, "reason": "Provider unavailable"},
        "safety_label": (
            "Observed pattern, not a diagnosis. Demo with synthetic data. Not for medical use."
        ),
    }
    if provider is None:
        return content
    try:
        draft = provider.draft_summary(packet.as_dict(), prompt_version=PROMPT_VERSION)
    except Exception:
        content["provider_validation"] = {"accepted": False, "reason": "Provider failed"}
        return content
    validation = validate_provider_draft(packet, draft)
    content["provider_validation"] = {"accepted": validation.accepted, "reason": validation.reason}
    if validation.accepted:
        content["physician_draft"] = [
            {"text": claim.text, "fact_ids": list(claim.fact_ids)} for claim in draft.claims
        ]
    return content

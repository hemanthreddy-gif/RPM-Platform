"""Typed request and response contracts for grounded synthetic-demo insights."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SummaryCreateRequest(BaseModel):
    days: int | None = Field(default=7)
    from_: datetime | None = Field(default=None, alias="from")
    to: datetime | None = None


class ArtifactReviewRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")


class ArtifactRevisionRequest(BaseModel):
    days: int = Field(default=7, ge=1, le=90)


class InsightArtifactResponse(BaseModel):
    id: UUID
    patient_id: UUID
    kind: str
    status: str
    artifact_version: int
    supersedes_id: UUID | None
    content: dict[str, object]
    input_refs: dict[str, object]
    created_at: datetime
    reviewed_at: datetime | None
    approval_invalidated_at: datetime | None

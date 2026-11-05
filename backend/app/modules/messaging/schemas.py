"""Non-emergency patient–physician communication contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ThreadCreateRequest(BaseModel):
    patient_id: UUID
    physician_id: UUID


class MessageCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    kind: Literal["message", "appointment_request"] = "message"


class MessageResponse(BaseModel):
    id: UUID
    sender_id: UUID
    recipient_id: UUID
    body: str
    kind: str
    sent_at: datetime
    read_at: datetime | None


class ThreadResponse(BaseModel):
    id: UUID
    patient_id: UUID
    physician_id: UUID
    created_at: datetime
    expected_response_notice: str

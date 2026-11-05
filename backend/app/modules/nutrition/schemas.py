"""Typed contracts for the non-nutrition meal-photo review fallback."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class MealPhotoCommentRequest(BaseModel):
    """A physician-authored, non-clinical comment on a submitted image."""

    body: str = Field(min_length=1, max_length=1000)

    @field_validator("body")
    @classmethod
    def _non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Comment cannot be blank")
        return value


class MealPhotoCommentResponse(BaseModel):
    id: UUID
    body: str
    created_at: datetime


class MealPhotoResponse(BaseModel):
    id: UUID
    eaten_at: datetime
    uploaded_at: datetime
    status: str
    image_content_type: str
    image_size_bytes: int
    comments: list[MealPhotoCommentResponse]

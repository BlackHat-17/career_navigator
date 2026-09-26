from __future__ import annotations

from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import AppBaseModel, TimestampSchema


class UserCreate(AppBaseModel):
    name: str = Field(..., min_length=1, max_length=120, examples=["Aditya"])
    email: EmailStr = Field(..., examples=["aditya@example.com"])
    career_goal: str | None = Field(
        default=None,
        max_length=500,
        examples=["Backend Developer"],
    )

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank")
        return v.strip()


class UserRead(TimestampSchema):
    id: UUID
    name: str
    email: str
    career_goal: str | None

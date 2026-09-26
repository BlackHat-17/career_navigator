"""
Shared base models and reusable field types used across all schemas.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AppBaseModel(BaseModel):
    """All schemas inherit from this to get consistent serialisation config."""

    model_config = ConfigDict(
        from_attributes=True,         # allows ORM → schema conversion
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class TimestampSchema(AppBaseModel):
    created_at: datetime
    updated_at: datetime


class ErrorDetail(AppBaseModel):
    code: str
    message: str


class ErrorResponse(AppBaseModel):
    success: bool = False
    error: ErrorDetail


class SuccessResponse(AppBaseModel):
    success: bool = True
    message: str = "OK"

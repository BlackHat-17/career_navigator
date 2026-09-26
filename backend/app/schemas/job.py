"""
Schemas for the job-description analysis endpoint.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from app.schemas.common import AppBaseModel


# ── Inbound request ───────────────────────────────────────────────────────────

class JobAnalyzeRequest(AppBaseModel):
    user_id: UUID
    title: str = Field(..., min_length=1, max_length=200, examples=["Backend Developer"])
    description: str = Field(..., min_length=10, max_length=20_000)


# ── Shapes returned / stored ──────────────────────────────────────────────────

class JobRequiredSkill(AppBaseModel):
    name: str
    importance: str = "required"   # "required" | "preferred" | "bonus"


# ── Outbound response ─────────────────────────────────────────────────────────

class JobAnalysisRead(AppBaseModel):
    analysis_id: UUID
    user_id: UUID
    title: str
    required_skills: List[JobRequiredSkill] = Field(default_factory=list)
    raw: Optional[Dict[str, Any]] = None

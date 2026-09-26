"""
Schemas for the roadmap generation endpoint.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from app.schemas.common import AppBaseModel


# ── Inbound request ───────────────────────────────────────────────────────────

class RoadmapGenerateRequest(AppBaseModel):
    user_id: UUID
    career_goal: str = Field(..., min_length=1, max_length=200)
    current_skills: List[str] = Field(default_factory=list)
    skill_gaps: List[str] = Field(default_factory=list)
    recommended_projects: List[str] = Field(default_factory=list)


# ── Shape returned by the Roadmap Generator service ──────────────────────────

class RoadmapStepRead(AppBaseModel):
    week: int = Field(..., ge=1)
    topic: str
    description: Optional[str] = None
    resources: List[str] = Field(default_factory=list)
    milestone: Optional[str] = None
    skills_covered: List[str] = Field(default_factory=list)


# ── Outbound response ─────────────────────────────────────────────────────────

class RoadmapRead(AppBaseModel):
    roadmap_id: UUID
    career_goal: str
    total_weeks: Optional[int] = None
    summary: Optional[str] = None
    roadmap: List[RoadmapStepRead] = Field(default_factory=list)
    raw: Optional[Dict[str, Any]] = None

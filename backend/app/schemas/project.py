"""
Schemas for the project recommendation endpoint.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from app.schemas.common import AppBaseModel


# ── Inbound request ───────────────────────────────────────────────────────────

class ProjectRecommendRequest(AppBaseModel):
    user_id: UUID
    career_goal: str = Field(..., min_length=1, max_length=200)
    verified_skills: List[str] = Field(default_factory=list)
    skill_gaps: List[str] = Field(default_factory=list)


# ── Shape returned by the Project Recommender service ────────────────────────

class ProjectRecommendation(AppBaseModel):
    title: str
    description: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    difficulty: str = Field(
        default="intermediate",
        pattern=r"^(beginner|intermediate|advanced)$",
    )
    reason: Optional[str] = None


# ── Outbound response ─────────────────────────────────────────────────────────

class ProjectRecommendRead(AppBaseModel):
    analysis_id: UUID
    recommendations: List[ProjectRecommendation] = Field(default_factory=list)
    raw: Optional[Dict[str, Any]] = None

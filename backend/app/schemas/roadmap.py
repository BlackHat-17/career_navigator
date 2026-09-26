"""
Schemas for the roadmap generation and learning system.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from app.schemas.common import AppBaseModel


# ─────────────────────────────────────────────────────────────────────────────
# Skill Classification
# ─────────────────────────────────────────────────────────────────────────────

class SkillClassification(str, Enum):
    MISSING = "missing"
    PARTIAL = "partial"


class SkillState(str, Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    LEARNING = "learning"
    LEARNING_COMPLETED = "learning_completed"
    MINI_PROJECT_AVAILABLE = "mini_project_available"
    PROJECT_IN_PROGRESS = "project_in_progress"
    PROJECT_SUBMITTED = "project_submitted"
    ASSESSMENT_AVAILABLE = "assessment_available"
    ASSESSMENT_STARTED = "assessment_started"
    VERIFIED = "verified"
    TARGETED_REVIEW = "targeted_review"
    RETAKE_AVAILABLE = "retake_available"


# ─────────────────────────────────────────────────────────────────────────────
# Inbound Request
# ─────────────────────────────────────────────────────────────────────────────

class RoadmapGenerateRequest(AppBaseModel):
    """
    Input received from the Resume + GitHub Analysis module.

    The analysis module is responsible for determining which skills
    are missing and which skills are partial.

    The Roadmap module starts from this point.
    """

    missing_skills: List[str] = Field(default_factory=list)
    partial_skills: List[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Learning Track
# ─────────────────────────────────────────────────────────────────────────────

class LearningResource(AppBaseModel):
    """Resource attached to a learning level."""

    title: str
    resource_type: str
    url: Optional[str] = None
    provider: Optional[str] = None
    duration: Optional[str] = None


class LearningLevel(AppBaseModel):
    """One level inside a Missing Skill learning track."""

    level_number: int = Field(..., ge=1)
    title: str
    objective: str
    resources: List[LearningResource] = Field(default_factory=list)
    practice: Optional[str] = None
    completion_status: str = "locked"


# ─────────────────────────────────────────────────────────────────────────────
# Mini Project
# ─────────────────────────────────────────────────────────────────────────────

class MiniProject(AppBaseModel):
    """Mini project generated for both Missing and Partial skills."""

    title: str
    description: str
    requirements: List[str] = Field(default_factory=list)
    deliverables: List[str] = Field(default_factory=list)
    evaluation_criteria: List[str] = Field(default_factory=list)


class AssessmentResult(AppBaseModel):
    """AI-generated assessment result for a skill."""

    skill: str
    score: Optional[int] = None
    passed: Optional[bool] = None
    strong_topics: List[str] = Field(default_factory=list)
    weak_topics: List[str] = Field(default_factory=list)
    feedback: Optional[str] = None
    recommended_action: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Roadmap Skill
# ─────────────────────────────────────────────────────────────────────────────

class RoadmapSkill(AppBaseModel):
    """
    Represents one skill in the learner's roadmap.

    Missing:
        Learning Track → Mini Project → Assessment

    Partial:
        Mini Project → Assessment
    """

    name: str
    classification: SkillClassification
    state: SkillState = SkillState.UNLOCKED
    learning_track: Optional[List[LearningLevel]] = None
    mini_project: Optional[MiniProject] = None
    assessment: Optional[AssessmentResult] = None


# ─────────────────────────────────────────────────────────────────────────────
# Outbound Response
# ─────────────────────────────────────────────────────────────────────────────

class RoadmapRead(AppBaseModel):
    roadmap_id: UUID
    skills: List[RoadmapSkill] = Field(default_factory=list)
    raw: Optional[Dict[str, Any]] = None
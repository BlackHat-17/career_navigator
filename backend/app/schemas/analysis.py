"""
Schemas for the skill-analysis, full orchestration, and status endpoints.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from app.models.analysis import AnalysisStatus
from app.schemas.common import AppBaseModel, TimestampSchema
from app.schemas.project import ProjectRecommendRead
from app.schemas.roadmap import RoadmapRead


# ─────────────────────────────────────────────────────────────────────────────
# Skill analysis  (POST /api/v1/analysis/skills)
# ─────────────────────────────────────────────────────────────────────────────

class SkillAnalysisRequest(AppBaseModel):
    user_id: UUID
    github_analysis_id: UUID
    resume_analysis_id: UUID
    job_analysis_id: UUID


class SkillDetail(AppBaseModel):
    name: str
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list)


class SkillAnalysisRead(AppBaseModel):
    analysis_id: UUID
    verified_skills: List[SkillDetail] = Field(default_factory=list)
    partial_skills: List[SkillDetail] = Field(default_factory=list)
    missing_skills: List[SkillDetail] = Field(default_factory=list)
    unsupported_claims: List[SkillDetail] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Status polling  (GET /api/v1/analysis/{analysis_id})
# ─────────────────────────────────────────────────────────────────────────────

class AnalysisStatusRead(TimestampSchema):
    analysis_id: UUID
    status: AnalysisStatus
    error_message: Optional[str] = None
    result: Optional["FullAnalysisRead"] = None


# ─────────────────────────────────────────────────────────────────────────────
# Full orchestration  (POST /api/v1/analysis)
# ─────────────────────────────────────────────────────────────────────────────

class FullAnalysisRequest(AppBaseModel):
    user_id: UUID
    github_username: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,37}[a-zA-Z0-9])?$",
        examples=["BlackHat-17"],
    )
    target_role: str = Field(..., min_length=1, max_length=200, examples=["Backend Developer"])
    job_description: str = Field(..., min_length=10, max_length=20_000)
    # resume is supplied as an UploadFile; its filename is stored here after upload
    resume_filename: Optional[str] = None


class CandidateInfo(AppBaseModel):
    user_id: UUID


class SkillsSummary(AppBaseModel):
    verified: List[SkillDetail] = Field(default_factory=list)
    partial: List[SkillDetail] = Field(default_factory=list)
    missing: List[SkillDetail] = Field(default_factory=list)


class ProjectsSummary(AppBaseModel):
    existing: List[Dict[str, Any]] = Field(default_factory=list)
    recommended: List[Dict[str, Any]] = Field(default_factory=list)


class AnalysisSummary(AppBaseModel):
    skill_match: float = Field(default=0.0, ge=0.0, le=100.0)
    major_gaps: List[str] = Field(default_factory=list)


class FullAnalysisRead(AppBaseModel):
    analysis_id: UUID
    status: AnalysisStatus
    candidate: CandidateInfo
    skills: SkillsSummary = Field(default_factory=SkillsSummary)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    projects: ProjectsSummary = Field(default_factory=ProjectsSummary)
    roadmap: List[Dict[str, Any]] = Field(default_factory=list)
    summary: AnalysisSummary = Field(default_factory=AnalysisSummary)


# Allow forward reference resolution
AnalysisStatusRead.model_rebuild()

"""
Schemas for POST /api/v1/evidence/analyze — the real-time resume ⟷ GitHub
evidence matcher and target-role fit analyzer.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Field

from app.schemas.common import AppBaseModel


class EvidenceAnalyzeRequest(AppBaseModel):
    github_username: str = Field(..., min_length=1, max_length=100, examples=["torvalds"])
    target_role: str = Field(..., min_length=1, max_length=200, examples=["Database Engineer"])
    resume_text: Optional[str] = Field(
        default=None,
        description="Plain resume text. Provide this OR upload a resume file to the endpoint.",
    )
    repositories: List[str] = Field(
        default_factory=list,
        description="Optional: limit analysis to these repo names instead of the whole profile.",
    )


class ProjectSkillEntry(AppBaseModel):
    skill_id: str
    skill: str
    percentage: int
    evidence: List[str] = Field(default_factory=list)


class ProjectSkillMapEntry(AppBaseModel):
    project: str
    url: str
    skills: List[ProjectSkillEntry] = Field(default_factory=list)


class SkillVerificationEntry(AppBaseModel):
    skill_id: str
    skill: str
    status: str  # "verified" | "partial"
    github_percentage: int
    best_project: Optional[str] = None
    evidence: List[str] = Field(default_factory=list)
    resume_context: str = ""


class RoleSkillFitEntry(AppBaseModel):
    skill_id: str
    skill: str
    status: str  # "verified" | "partial" | "missing"
    github_percentage: int
    best_project: Optional[str] = None
    evidence: List[str] = Field(default_factory=list)
    in_resume: bool = False
    suggestion: Optional[str] = None


class GapEntry(AppBaseModel):
    skill: str
    status: str
    recommendation: str


class EvidenceAnalyzeResponse(AppBaseModel):
    github_username: str
    github_exists: bool
    repos_analyzed: int
    repos_truncated: bool
    resume_skills_detected: List[str] = Field(default_factory=list)

    # Task 1: resume ⟷ GitHub verification
    project_skill_map: List[ProjectSkillMapEntry] = Field(default_factory=list)
    skill_verification: List[SkillVerificationEntry] = Field(default_factory=list)

    # Task 2: target-role fit + gap analysis
    target_role: str
    resolved_role: str
    role_required_skills: List[str] = Field(default_factory=list)
    role_fit: List[RoleSkillFitEntry] = Field(default_factory=list)
    role_coverage_percent: float = 0.0
    gaps_to_learn: List[GapEntry] = Field(default_factory=list)

    warnings: List[str] = Field(default_factory=list)

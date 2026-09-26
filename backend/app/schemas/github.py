"""
Schemas for the GitHub analysis endpoint.

The backend forwards requests to the GitHub Agent and passes its response
straight through.  These schemas define the contract both ways.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import AppBaseModel, TimestampSchema


# ── Inbound request ───────────────────────────────────────────────────────────

class GithubAnalyzeRequest(AppBaseModel):
    user_id: UUID
    github_username: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,37}[a-zA-Z0-9])?$",
        examples=["BlackHat-17"],
    )
    repositories: List[str] = Field(
        default_factory=list,
        description="Optional list of repo names to limit analysis scope.",
    )

    @field_validator("repositories", mode="before")
    @classmethod
    def deduplicate(cls, v: List[str]) -> List[str]:
        return list(dict.fromkeys(v))


# ── Shapes returned by the GitHub Agent (service contract) ────────────────────

class GithubSkillEvidence(AppBaseModel):
    """A skill extracted by the GitHub Agent with supporting evidence."""
    name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list)


class GithubProject(AppBaseModel):
    """A project found in the candidate's GitHub profile."""
    name: str
    description: Optional[str] = None
    url: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)


# ── Outbound response ─────────────────────────────────────────────────────────

class GithubAnalysisRead(AppBaseModel):
    analysis_id: UUID
    github_username: str
    skills: List[GithubSkillEvidence] = Field(default_factory=list)
    projects: List[GithubProject] = Field(default_factory=list)
    recommended_projects: List[str] = Field(default_factory=list)
    raw: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Full raw payload from the GitHub Agent (for debugging).",
    )

"""
Schemas for the resume analysis endpoint.

The actual judging is delegated to the Resume Judge service.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from app.schemas.common import AppBaseModel


# ── Inbound (multipart handled by FastAPI; this covers the metadata fields) ───

class ResumeAnalyzeRequest(AppBaseModel):
    """
    Non-file fields extracted from the multipart/form-data request.
    The file itself is handled separately as an UploadFile dependency.
    """
    user_id: UUID
    target_role: str = Field(..., min_length=1, max_length=200, examples=["Backend Developer"])


# ── Shapes returned by the Resume Judge service ───────────────────────────────

class ResumeSkillClaim(AppBaseModel):
    """A skill the candidate claims in their resume."""
    name: str
    context: Optional[str] = None        # sentence / bullet where it appears
    confidence: float = Field(..., ge=0.0, le=1.0)


class ResumeFeedback(AppBaseModel):
    section: str                          # e.g. "experience", "education"
    comment: str
    severity: str = "info"               # "info" | "warning" | "error"


# ── Outbound response ─────────────────────────────────────────────────────────

class ResumeAnalysisRead(AppBaseModel):
    analysis_id: UUID
    user_id: UUID
    target_role: str
    resume_filename: str
    claimed_skills: List[ResumeSkillClaim] = Field(default_factory=list)
    feedback: List[ResumeFeedback] = Field(default_factory=list)
    overall_score: Optional[float] = Field(
        default=None, ge=0.0, le=100.0,
        description="0-100 score assigned by the Resume Judge.",
    )
    raw: Optional[Dict[str, Any]] = None

"""
POST /api/v1/evidence/analyze
──────────────────────────────
Real-time evidence matcher. No external microservice, no DB write required —
everything is fetched live from GitHub and computed on the fly:

  1. Resume ⟷ GitHub verification: for every skill the candidate claims on
     their resume, checks whether their own GitHub projects actually
     demonstrate it (and builds the project → skill % map).

  2. Target-role fit: for every skill the target role needs, checks GitHub
     for real evidence and classifies it verified / partial / missing,
     plus an overall role-coverage percentage and gap-to-learn list.

Accepts either a resume file (PDF/DOC/DOCX) OR raw resume_text — exactly one
should be provided.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.evidence import EvidenceAnalyzeResponse
from app.services.evidence_matching_service import EvidenceMatchingService, result_to_dict
from app.services.resume_skill_service import extract_text_from_bytes

router = APIRouter(prefix="/evidence", tags=["Evidence Matching"])
logger = get_logger(__name__)
settings = get_settings()


@router.post(
    "/analyze",
    response_model=EvidenceAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Match resume skills against live GitHub evidence, and score fit for a target role",
)
async def analyze_evidence(
    github_username: str = Form(..., min_length=1, max_length=100),
    target_role: str = Form(..., min_length=1, max_length=200),
    resume_text: Optional[str] = Form(
        default=None, description="Raw resume text. Provide this OR resume_file."
    ),
    resume_file: Optional[UploadFile] = File(
        default=None, description="Resume file (PDF/DOC/DOCX). Provide this OR resume_text."
    ),
    repositories: Optional[str] = Form(
        default=None, description="Optional comma-separated list of repo names to limit scope."
    ),
) -> EvidenceAnalyzeResponse:
    if not resume_text and not resume_file:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either resume_text or resume_file.",
        )

    text = resume_text or ""
    if resume_file is not None:
        content = await resume_file.read()
        text = extract_text_from_bytes(
            content, resume_file.content_type or "", resume_file.filename or ""
        )
        if not text.strip():
            logger.warning("No text could be extracted from uploaded resume file")

    repo_filter: Optional[List[str]] = None
    if repositories:
        repo_filter = [r.strip() for r in repositories.split(",") if r.strip()]

    token = settings.GITHUB_TOKEN
    if token.startswith("ghp_...") or not token:
        token = None  # placeholder / unset -> fall back to unauthenticated requests

    svc = EvidenceMatchingService(github_token=token, max_repos=settings.GITHUB_MAX_REPOS)

    try:
        result = await svc.analyze(
            resume_text=text,
            github_username=github_username,
            target_role=target_role,
            repositories=repo_filter,
        )
    except Exception as exc:  # GitHubRateLimitedError and anything unexpected
        logger.error("Evidence analysis failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not complete GitHub evidence analysis: {exc}",
        ) from exc

    return EvidenceAnalyzeResponse(**result_to_dict(result))

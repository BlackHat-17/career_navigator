"""
POST /api/v1/analysis/skills  – cross-reference GitHub + Resume + JD via Resume Judge
POST /api/v1/analysis          – full orchestration pipeline (main endpoint)
GET  /api/v1/analysis/{id}     – fetch analysis status + result
"""
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.schemas.analysis import (
    AnalysisStatusRead,
    FullAnalysisRead,
    SkillAnalysisRead,
    SkillAnalysisRequest,
)
from app.models.analysis import AnalysisStatus
from app.services.orchestration_service import OrchestrationService
from app.services.resume_service import ALLOWED_EXTENSIONS

router = APIRouter(prefix="/analysis", tags=["Analysis"])


# ── Skill analysis (stand-alone) ──────────────────────────────────────────────

@router.post(
    "/skills",
    response_model=SkillAnalysisRead,
    status_code=status.HTTP_200_OK,
    summary="Cross-reference GitHub, resume, and JD to classify skills",
    description=(
        "Retrieves the outputs of previous GitHub and resume analyses from the "
        "database and sends them to the Resume Judge for skill verification. "
        "Returns verified / partial / missing / unsupported skill lists."
    ),
)
async def skill_analysis(
    payload: SkillAnalysisRequest,
    db: AsyncSession = Depends(get_db),
) -> SkillAnalysisRead:
    from sqlalchemy import select
    from app.models.analysis import Analysis
    from app.clients.resume_judge_client import ResumeJudgeClient

    # Load each analysis record
    github_rec = await db.get(Analysis, payload.github_analysis_id)
    resume_rec = await db.get(Analysis, payload.resume_analysis_id)
    job_rec    = await db.get(Analysis, payload.job_analysis_id)

    if not github_rec:
        raise NotFoundError(f"GitHub analysis {payload.github_analysis_id} not found.")
    if not resume_rec:
        raise NotFoundError(f"Resume analysis {payload.resume_analysis_id} not found.")
    if not job_rec:
        raise NotFoundError(f"Job analysis {payload.job_analysis_id} not found.")

    github_raw = github_rec.github_agent_output or {}
    resume_raw = resume_rec.resume_judge_output or {}
    job_title  = job_rec.target_role or ""
    job_desc   = job_rec.job_description or ""

    async with ResumeJudgeClient() as client:
        raw = await client.analyze_skills(
            github_output=github_raw,
            resume_output=resume_raw,
            job_title=job_title,
            job_description=job_desc,
        )

    from app.schemas.analysis import SkillDetail
    def _to_details(key: str):
        return [SkillDetail(**s) for s in raw.get(key, [])]

    return SkillAnalysisRead(
        analysis_id=payload.github_analysis_id,
        verified_skills=_to_details("verified_skills"),
        partial_skills=_to_details("partial_skills"),
        missing_skills=_to_details("missing_skills"),
        unsupported_claims=_to_details("unsupported_claims"),
    )


# ── Full orchestration ────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=FullAnalysisRead,
    status_code=status.HTTP_200_OK,
    summary="Run full analysis pipeline",
    description=(
        "Main endpoint. Accepts multipart/form-data. "
        "Runs: GitHub Agent → Resume Judge → Skill Analysis "
        "→ Project Recommender → Roadmap Generator. "
        "Returns unified structured result."
    ),
)
async def full_analysis(
    user_id: UUID = Form(...),
    target_role: str = Form(..., min_length=1, max_length=200),
    resume_file: UploadFile = File(
        ...,
        description=f"Resume file. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
    ),
    github_username: str = Form(None, min_length=1, max_length=100),
    job_description: str = Form(None, min_length=10, max_length=20_000),
    db: AsyncSession = Depends(get_db),
) -> FullAnalysisRead:
    svc = OrchestrationService(db)
    return await svc.run(
        user_id=user_id,
        github_username=github_username,
        target_role=target_role,
        job_description=job_description,
        resume_file=resume_file,
    )


# ── Status / result retrieval ─────────────────────────────────────────────────

@router.get(
    "/{analysis_id}",
    response_model=AnalysisStatusRead,
    summary="Get analysis status and result",
    description=(
        "Poll this endpoint after submitting a full analysis. "
        "Returns status (PENDING | PROCESSING | COMPLETED | FAILED) "
        "and, when completed, the full result."
    ),
)
async def get_analysis(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AnalysisStatusRead:
    from app.models.analysis import Analysis

    record = await db.get(Analysis, analysis_id)
    if not record:
        raise NotFoundError(f"Analysis {analysis_id} not found.")

    result = None
    if record.status == AnalysisStatus.COMPLETED:
        svc = OrchestrationService(db)
        result = await svc.get_analysis(analysis_id)

    return AnalysisStatusRead(
        analysis_id=record.id,
        status=record.status,
        error_message=record.error_message,
        created_at=record.created_at,
        updated_at=record.updated_at,
        result=result,
    )

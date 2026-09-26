"""
POST /api/v1/jobs/analyze – store a job description, return analysis_id
GET  /api/v1/jobs/{analysis_id} – fetch stored job analysis
"""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.job import JobAnalysisRead, JobAnalyzeRequest
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post(
    "/analyze",
    response_model=JobAnalysisRead,
    status_code=status.HTTP_200_OK,
    summary="Store and analyse a job description",
    description=(
        "Persists the job description. The Resume Judge will receive it "
        "during skill-analysis. The backend does not run LLM parsing itself."
    ),
)
async def analyze_job(
    payload: JobAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> JobAnalysisRead:
    svc = JobService(db)
    return await svc.analyze(payload)


@router.get(
    "/{analysis_id}",
    response_model=JobAnalysisRead,
    summary="Retrieve a stored job analysis",
)
async def get_job_analysis(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JobAnalysisRead:
    svc = JobService(db)
    record = await svc.get(analysis_id)
    return JobAnalysisRead(
        analysis_id=record.id,
        user_id=record.user_id,
        title=record.target_role or "",
        required_skills=[],
        raw=None,
    )

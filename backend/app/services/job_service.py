"""
JobService
──────────
Stores the job description and provides a clean API contract.
Optionally forwards to Resume Judge for JD parsing.

For the MVP the backend simply stores the JD; the Resume Judge
will receive it as part of the skill-analysis call.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.analysis import Analysis, AnalysisStatus
from app.models.user import User
from app.schemas.job import JobAnalysisRead, JobAnalyzeRequest

logger = get_logger(__name__)


class JobService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def analyze(self, request: JobAnalyzeRequest) -> JobAnalysisRead:
        # 1. Validate user
        user = await self._db.get(User, request.user_id)
        if not user:
            raise NotFoundError(f"User {request.user_id} not found.")

        # 2. Persist the JD as an analysis record so downstream services
        #    can reference it by ID
        analysis = Analysis(
            user_id=request.user_id,
            target_role=request.title,
            job_description=request.description,
            status=AnalysisStatus.COMPLETED,   # no async service call needed
        )
        self._db.add(analysis)
        await self._db.flush()
        logger.info("Job analysis stored id=%s title=%s", analysis.id, request.title)

        # Return a minimal response — the Resume Judge will do the deep parsing
        return JobAnalysisRead(
            analysis_id=analysis.id,
            user_id=request.user_id,
            title=request.title,
            required_skills=[],   # populated by skill-analysis step
            raw=None,
        )

    async def get(self, analysis_id) -> Analysis:
        record = await self._db.get(Analysis, analysis_id)
        if not record:
            raise NotFoundError(f"Job analysis {analysis_id} not found.")
        return record

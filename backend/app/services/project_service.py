"""
ProjectService
──────────────
Delegates to ProjectRecommenderClient and persists the results.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.project_recommender_client import ProjectRecommenderClient
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.analysis import Analysis, AnalysisStatus
from app.models.project import RecommendedProject
from app.models.user import User
from app.schemas.project import (
    ProjectRecommendRead,
    ProjectRecommendRequest,
    ProjectRecommendation,
)

logger = get_logger(__name__)


class ProjectService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def recommend(self, request: ProjectRecommendRequest) -> ProjectRecommendRead:
        # 1. Validate user
        user = await self._db.get(User, request.user_id)
        if not user:
            raise NotFoundError(f"User {request.user_id} not found.")

        # 2. Create analysis record
        analysis = Analysis(
            user_id=request.user_id,
            target_role=request.career_goal,
            status=AnalysisStatus.PROCESSING,
        )
        self._db.add(analysis)
        await self._db.flush()
        logger.info("Project recommendation started id=%s", analysis.id)

        # 3. Call the Project Recommender
        try:
            async with ProjectRecommenderClient() as client:
                raw = await client.recommend(
                    career_goal=request.career_goal,
                    verified_skills=request.verified_skills,
                    skill_gaps=request.skill_gaps,
                )
        except Exception as exc:
            analysis.status = AnalysisStatus.FAILED
            analysis.error_message = str(exc)
            await self._db.flush()
            raise

        # 4. Persist
        analysis.project_recommender_output = raw
        analysis.status = AnalysisStatus.COMPLETED

        for rec in raw.get("recommendations", []):
            rp = RecommendedProject(
                analysis_id=analysis.id,
                title=rec.get("title", ""),
                description=rec.get("description"),
                skills=rec.get("skills", []),
                difficulty=rec.get("difficulty", "intermediate"),
                reason=rec.get("reason"),
            )
            self._db.add(rp)

        await self._db.flush()
        logger.info("Project recommendation completed id=%s", analysis.id)

        recommendations = [
            ProjectRecommendation(**r) for r in raw.get("recommendations", [])
        ]
        return ProjectRecommendRead(
            analysis_id=analysis.id,
            recommendations=recommendations,
            raw=raw,
        )

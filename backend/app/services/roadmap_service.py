"""
RoadmapService
──────────────
Delegates to RoadmapGeneratorClient and persists the results.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.roadmap_generator_client import RoadmapGeneratorClient
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.analysis import Analysis, AnalysisStatus
from app.models.roadmap import Roadmap, RoadmapStep
from app.models.user import User
from app.schemas.roadmap import RoadmapGenerateRequest, RoadmapRead, RoadmapStepRead

logger = get_logger(__name__)


class RoadmapService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def generate(self, request: RoadmapGenerateRequest) -> RoadmapRead:
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
        logger.info("Roadmap generation started analysis_id=%s", analysis.id)

        # 3. Call the Roadmap Generator
        try:
            async with RoadmapGeneratorClient() as client:
                raw = await client.generate(
                    career_goal=request.career_goal,
                    current_skills=request.current_skills,
                    skill_gaps=request.skill_gaps,
                    recommended_projects=request.recommended_projects,
                )
        except Exception as exc:
            analysis.status = AnalysisStatus.FAILED
            analysis.error_message = str(exc)
            await self._db.flush()
            raise

        # 4. Persist raw output
        analysis.roadmap_generator_output = raw
        analysis.status = AnalysisStatus.COMPLETED

        # 5. Persist normalised roadmap
        roadmap = Roadmap(
            analysis_id=analysis.id,
            career_goal=request.career_goal,
            summary=raw.get("summary"),
            total_weeks=raw.get("total_weeks"),
        )
        self._db.add(roadmap)
        await self._db.flush()

        for step_data in raw.get("roadmap", []):
            step = RoadmapStep(
                roadmap_id=roadmap.id,
                week=step_data.get("week", 0),
                topic=step_data.get("topic", ""),
                description=step_data.get("description"),
                resources=step_data.get("resources", []),
                milestone=step_data.get("milestone"),
                skills_covered=step_data.get("skills_covered", []),
            )
            self._db.add(step)

        await self._db.flush()
        logger.info("Roadmap generation completed roadmap_id=%s", roadmap.id)

        steps = [RoadmapStepRead(**s) for s in raw.get("roadmap", [])]
        return RoadmapRead(
            roadmap_id=roadmap.id,
            career_goal=request.career_goal,
            total_weeks=raw.get("total_weeks"),
            summary=raw.get("summary"),
            roadmap=steps,
            raw=raw,
        )

    async def get_by_analysis(self, analysis_id: UUID) -> RoadmapRead:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        result = await self._db.execute(
            select(Roadmap)
            .where(Roadmap.analysis_id == analysis_id)
            .options(selectinload(Roadmap.steps))
        )
        roadmap = result.scalar_one_or_none()
        if not roadmap:
            raise NotFoundError(f"No roadmap found for analysis {analysis_id}.")

        steps = [
            RoadmapStepRead(
                week=s.week,
                topic=s.topic,
                description=s.description,
                resources=s.resources or [],
                milestone=s.milestone,
                skills_covered=s.skills_covered or [],
            )
            for s in roadmap.steps
        ]
        return RoadmapRead(
            roadmap_id=roadmap.id,
            career_goal=roadmap.career_goal,
            total_weeks=roadmap.total_weeks,
            summary=roadmap.summary,
            roadmap=steps,
        )

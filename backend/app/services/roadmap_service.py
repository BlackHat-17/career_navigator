"""
RoadmapService
──────────────
Handles skill classification and roadmap generation.

Input:
    missing_skills
    partial_skills

Flow:

    Missing Skill
        ↓
    Learning Track
        ↓
    Mini Project
        ↓
    AI Assessment

    Partial Skill
        ↓
    Direct Mini Project
        ↓
    AI Assessment
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.roadmap_generator_client import RoadmapGeneratorClient
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.roadmap import (
    Roadmap,
    RoadmapSkillClassification,
    RoadmapSkillRecord,
    RoadmapSkillState,
)
from app.schemas.roadmap import (
    LearningLevel,
    RoadmapGenerateRequest,
    RoadmapRead,
    RoadmapSkill,
    SkillClassification,
    SkillState,
)

logger = get_logger(__name__)


class RoadmapService:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @staticmethod
    def _apply_skill_state(skill: RoadmapSkill) -> None:
        """Set the roadmap state to the first valid milestone for each flow."""
        if skill.assessment is not None:
            if skill.assessment.passed is True:
                skill.state = SkillState.VERIFIED
            elif skill.assessment.passed is False:
                skill.state = SkillState.RETAKE_AVAILABLE
            else:
                skill.state = SkillState.ASSESSMENT_AVAILABLE
            return

        if skill.classification == SkillClassification.MISSING:
            if skill.learning_track:
                skill.state = SkillState.LEARNING
                for level in skill.learning_track:
                    if level.completion_status in {"locked", "not_started"}:
                        level.completion_status = "available"
                        break
            elif skill.mini_project:
                skill.state = SkillState.MINI_PROJECT_AVAILABLE
            else:
                skill.state = SkillState.UNLOCKED
        else:
            if skill.mini_project:
                skill.state = SkillState.MINI_PROJECT_AVAILABLE
            else:
                skill.state = SkillState.UNLOCKED

    @staticmethod
    def _skill_to_schema(record: RoadmapSkillRecord) -> RoadmapSkill:
        learning_levels: list[LearningLevel] | None = None
        if record.learning_track:
            learning_levels = [
                LearningLevel(
                    level_number=level.get("level_number", 1),
                    title=level.get("title", ""),
                    objective=level.get("objective", ""),
                    resources=level.get("resources", []),
                    practice=level.get("practice"),
                    completion_status=level.get("completion_status", "locked"),
                )
                for level in record.learning_track
            ]

        return RoadmapSkill(
            name=record.name,
            classification=SkillClassification(record.classification.value),
            state=SkillState(record.state.value),
            learning_track=learning_levels,
            mini_project=record.mini_project,
            assessment=record.assessment,
        )

    async def get_by_identifier(self, identifier: UUID) -> RoadmapRead:
        result = await self._db.execute(
            select(Roadmap).where(
                (Roadmap.id == identifier) | (Roadmap.analysis_id == identifier)
            )
        )
        roadmap = result.scalar_one_or_none()
        if not roadmap:
            raise NotFoundError(f"Roadmap {identifier} not found.")

        return RoadmapRead(
            roadmap_id=roadmap.id,
            skills=[self._skill_to_schema(skill) for skill in roadmap.skills],
            raw={
                "analysis_id": str(roadmap.analysis_id) if roadmap.analysis_id else None,
                "skill_count": len(roadmap.skills),
            },
        )

    async def generate(
        self,
        request: RoadmapGenerateRequest,
    ) -> RoadmapRead:

        logger.info(
            "Starting roadmap generation: missing=%s partial=%s",
            request.missing_skills,
            request.partial_skills,
        )

        roadmap = Roadmap(title="Skill roadmap", summary="Generated from classified skill gaps")
        self._db.add(roadmap)
        await self._db.flush()

        roadmap_skills: list[RoadmapSkill] = []

        for skill_name in request.missing_skills:
            logger.info("Processing missing skill: %s", skill_name)
            roadmap_skills.append(
                RoadmapSkill(
                    name=skill_name,
                    classification=SkillClassification.MISSING,
                    state=SkillState.UNLOCKED,
                    learning_track=[],
                )
            )

        for skill_name in request.partial_skills:
            logger.info("Processing partial skill: %s", skill_name)
            roadmap_skills.append(
                RoadmapSkill(
                    name=skill_name,
                    classification=SkillClassification.PARTIAL,
                    state=SkillState.UNLOCKED,
                    learning_track=None,
                )
            )

        async with RoadmapGeneratorClient() as client:
            for skill in roadmap_skills:
                if skill.classification == SkillClassification.MISSING:
                    raw = await client.generate_learning_track(skill_name=skill.name)
                    skill.learning_track = raw.get("learning_track", [])
                    skill.mini_project = raw.get("mini_project")
                    assessment_raw = await client.generate_assessment(
                        skill_name=skill.name,
                        classification="missing",
                    )
                    if assessment_raw.get("assessment"):
                        skill.assessment = assessment_raw.get("assessment")
                elif skill.classification == SkillClassification.PARTIAL:
                    raw = await client.generate_mini_project(skill_name=skill.name)
                    skill.learning_track = None
                    skill.mini_project = raw.get("mini_project")
                    assessment_raw = await client.generate_assessment(
                        skill_name=skill.name,
                        classification="partial",
                    )
                    if assessment_raw.get("assessment"):
                        skill.assessment = assessment_raw.get("assessment")

                self._apply_skill_state(skill)

                roadmap.skills.append(
                    RoadmapSkillRecord(
                        name=skill.name,
                        classification=RoadmapSkillClassification(skill.classification.value),
                        state=RoadmapSkillState(skill.state.value),
                        learning_track=[level.model_dump(mode="json") for level in skill.learning_track] if skill.learning_track is not None else None,
                        mini_project=skill.mini_project.model_dump(mode="json") if skill.mini_project else None,
                        assessment=skill.assessment.model_dump(mode="json") if skill.assessment else None,
                    )
                )

        await self._db.flush()

        logger.info("Roadmap generation completed roadmap_id=%s", roadmap.id)

        return RoadmapRead(
            roadmap_id=roadmap.id,
            skills=roadmap_skills,
            raw={
                "missing_skills": request.missing_skills,
                "partial_skills": request.partial_skills,
                "skill_count": len(roadmap_skills),
            },
        )
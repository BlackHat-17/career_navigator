"""
RoadmapGeneratorClient
──────────────────────
AI-facing integration for skill learning content generation.

This layer keeps AI communication isolated from the HTTP route and service
business logic. The upstream analysis module already decides which skills are
missing or partial; the roadmap module only asks the generator to produce
skill-specific learning content.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.clients.base import BaseServiceClient
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class RoadmapGeneratorClient(BaseServiceClient):
    service_name = "Roadmap Generator"
    base_url = settings.ROADMAP_GENERATOR_URL

    async def generate_learning_track(
        self,
        skill_name: str,
    ) -> Dict[str, Any]:
        """Generate a learning track for a missing skill."""
        payload: Dict[str, Any] = {
            "skill_name": skill_name,
            "classification": "missing",
        }
        logger.info("Requesting learning track for missing skill=%s", skill_name)
        return await self._post("/generate-learning-track", payload)

    async def generate_mini_project(
        self,
        skill_name: str,
    ) -> Dict[str, Any]:
        """Generate a mini project for either a missing or partial skill."""
        payload: Dict[str, Any] = {
            "skill_name": skill_name,
        }
        logger.info("Requesting mini project for skill=%s", skill_name)
        return await self._post("/generate-mini-project", payload)

    async def generate_assessment(
        self,
        skill_name: str,
        classification: str,
    ) -> Dict[str, Any]:
        """Generate an evaluation for a completed learning or project phase."""
        payload: Dict[str, Any] = {
            "skill_name": skill_name,
            "classification": classification,
        }
        logger.info(
            "Requesting assessment for skill=%s classification=%s",
            skill_name,
            classification,
        )
        return await self._post("/generate-assessment", payload)

    async def generate(
        self,
        career_goal: str,
        current_skills: List[str],
        skill_gaps: List[str],
        recommended_projects: List[str],
    ) -> Dict[str, Any]:
        """Backward-compatible compatibility method for older callers."""
        payload: Dict[str, Any] = {
            "career_goal": career_goal,
            "current_skills": current_skills,
            "skill_gaps": skill_gaps,
            "recommended_projects": recommended_projects,
        }
        logger.info(
            "Sending legacy roadmap generation request for goal=%s skill_gaps=%s",
            career_goal,
            skill_gaps,
        )
        return await self._post("/generate", payload)

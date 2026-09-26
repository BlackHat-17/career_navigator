"""
RoadmapGeneratorClient
──────────────────────
Forwards candidate data to the Roadmap Generator service.

Expected service contract
─────────────────────────
POST /generate

Input:
    {
        "career_goal":           "Backend Developer",
        "current_skills":        ["Python", "FastAPI"],
        "skill_gaps":            ["Docker", "Kubernetes"],
        "recommended_projects":  ["Production FastAPI Service"]
    }

Output:
    {
        "career_goal":  "Backend Developer",
        "total_weeks":  12,
        "summary":      "A focused 12-week plan to become a backend developer.",
        "roadmap": [
            {
                "week":           1,
                "topic":          "Docker Fundamentals",
                "description":    "...",
                "resources":      ["https://docs.docker.com/get-started/"],
                "milestone":      "Containerise a simple FastAPI app",
                "skills_covered": ["Docker"]
            }
        ]
    }
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

    async def generate(
        self,
        career_goal: str,
        current_skills: List[str],
        skill_gaps: List[str],
        recommended_projects: List[str],
    ) -> Dict[str, Any]:
        """
        Request a personalised learning roadmap for a candidate.
        Returns the raw roadmap from the service.
        """
        payload: Dict[str, Any] = {
            "career_goal": career_goal,
            "current_skills": current_skills,
            "skill_gaps": skill_gaps,
            "recommended_projects": recommended_projects,
        }
        logger.info(
            "Sending roadmap generation request for goal=%s skill_gaps=%s",
            career_goal,
            skill_gaps,
        )
        return await self._post("/generate", payload)

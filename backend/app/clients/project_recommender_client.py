"""
ProjectRecommenderClient
────────────────────────
Forwards candidate skill data to the Project Recommender service.

Expected service contract
─────────────────────────
POST /recommend

Input:
    {
        "career_goal":     "Backend Developer",
        "verified_skills": ["Python", "FastAPI"],
        "skill_gaps":      ["Docker", "Kubernetes"]
    }

Output:
    {
        "recommendations": [
            {
                "title":       "Production FastAPI Service",
                "description": "...",
                "skills":      ["FastAPI", "Docker"],
                "difficulty":  "intermediate",
                "reason":      "Directly addresses Docker gap"
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


class ProjectRecommenderClient(BaseServiceClient):
    service_name = "Project Recommender"
    base_url = settings.PROJECT_RECOMMENDER_URL

    async def recommend(
        self,
        career_goal: str,
        verified_skills: List[str],
        skill_gaps: List[str],
    ) -> Dict[str, Any]:
        """
        Request project recommendations for a candidate.
        Returns the raw recommendation list from the service.
        """
        payload: Dict[str, Any] = {
            "career_goal": career_goal,
            "verified_skills": verified_skills,
            "skill_gaps": skill_gaps,
        }
        logger.info(
            "Sending project recommendation request for goal=%s gaps=%s",
            career_goal,
            skill_gaps,
        )
        return await self._post("/recommend", payload)

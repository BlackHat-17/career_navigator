"""
GitHubAgentClient
─────────────────
Forwards GitHub analysis requests to the GitHub Agent service.

Expected service contract
─────────────────────────
POST /analyze

Input:
    {
        "github_username": "BlackHat-17",
        "repositories": []          # optional filter
    }

Output:
    {
        "skills": [
            {
                "name": "Python",
                "confidence": 0.94,
                "evidence": ["Flask backend", "ML scripts"]
            }
        ],
        "projects": [
            {
                "name": "career-api",
                "description": "...",
                "url": "https://github.com/...",
                "languages": ["Python"],
                "topics": ["fastapi"]
            }
        ],
        "recommended_projects": []   # optional, may be empty
    }
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.clients.base import BaseServiceClient
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class GitHubAgentClient(BaseServiceClient):
    service_name = "GitHub Agent"
    base_url = settings.GITHUB_AGENT_URL

    async def analyze(
        self,
        github_username: str,
        repositories: List[str] | None = None,
    ) -> Dict[str, Any]:
        """
        Send a GitHub username (and optional repo list) to the GitHub Agent.
        Returns the raw parsed JSON response.

        The backend does NOT inspect or transform the content — it stores
        and forwards it as-is.
        """
        payload: Dict[str, Any] = {
            "github_username": github_username,
            "repositories": repositories or [],
        }
        logger.info(
            "Sending GitHub analysis request for username=%s repos=%s",
            github_username,
            repositories,
        )
        return await self._post("/analyze", payload)

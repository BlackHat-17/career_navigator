"""
GitHubService
─────────────
Orchestrates interaction with the GitHub Agent.

Responsibilities:
  1. Validate the user exists
  2. Create a PENDING Analysis record
  3. Call GitHubAgentClient
  4. Persist the raw output + normalised projects/evidence
  5. Mark the analysis COMPLETED (or FAILED)
  6. Return a structured response schema

The service does NOT perform any skill extraction itself.
"""
from __future__ import annotations

import uuid
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.github_agent_client import GitHubAgentClient
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.analysis import Analysis, AnalysisStatus
from app.models.evidence import Evidence
from app.models.project import Project
from app.models.user import User
from app.schemas.github import (
    GithubAnalysisRead,
    GithubAnalyzeRequest,
    GithubProject,
    GithubSkillEvidence,
)

logger = get_logger(__name__)


class GitHubService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def analyze(self, request: GithubAnalyzeRequest) -> GithubAnalysisRead:
        # 1. Validate user
        user = await self._db.get(User, request.user_id)
        if not user:
            raise NotFoundError(f"User {request.user_id} not found.")

        # 2. Create analysis record
        analysis = Analysis(
            user_id=request.user_id,
            github_username=request.github_username,
            status=AnalysisStatus.PROCESSING,
        )
        self._db.add(analysis)
        await self._db.flush()
        logger.info("GitHub analysis started id=%s", analysis.id)

        # 3. Call the GitHub Agent
        try:
            async with GitHubAgentClient() as client:
                raw = await client.analyze(
                    github_username=request.github_username,
                    repositories=request.repositories,
                )
        except Exception as exc:
            analysis.status = AnalysisStatus.FAILED
            analysis.error_message = str(exc)
            await self._db.flush()
            raise

        # 4. Persist raw output
        analysis.github_agent_output = raw
        analysis.status = AnalysisStatus.COMPLETED

        # 5. Persist normalised projects
        for proj_data in raw.get("projects", []):
            project = Project(
                analysis_id=analysis.id,
                name=proj_data.get("name", ""),
                description=proj_data.get("description"),
                url=proj_data.get("url"),
                languages=proj_data.get("languages", []),
                topics=proj_data.get("topics", []),
            )
            self._db.add(project)

        # 6. Persist evidence items
        for skill_data in raw.get("skills", []):
            for snippet in skill_data.get("evidence", []):
                evidence = Evidence(
                    analysis_id=analysis.id,
                    skill_name=skill_data.get("name", ""),
                    source="github",
                    snippet=snippet,
                )
                self._db.add(evidence)

        await self._db.flush()
        logger.info("GitHub analysis completed id=%s", analysis.id)

        # 7. Build response
        skills = [
            GithubSkillEvidence(**s)
            for s in raw.get("skills", [])
        ]
        projects = [
            GithubProject(**p)
            for p in raw.get("projects", [])
        ]

        return GithubAnalysisRead(
            analysis_id=analysis.id,
            github_username=request.github_username,
            skills=skills,
            projects=projects,
            recommended_projects=raw.get("recommended_projects", []),
            raw=raw,
        )

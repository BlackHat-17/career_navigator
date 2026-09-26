"""
POST /api/v1/github/analyze – forward to GitHub Agent, persist, return structured result
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.github import GithubAnalysisRead, GithubAnalyzeRequest
from app.services.github_service import GitHubService

router = APIRouter(prefix="/github", tags=["GitHub"])


@router.post(
    "/analyze",
    response_model=GithubAnalysisRead,
    status_code=status.HTTP_200_OK,
    summary="Analyse a candidate's GitHub profile",
    description=(
        "Forwards the request to the GitHub Agent service. "
        "The backend does not extract skills itself."
    ),
)
async def analyze_github(
    payload: GithubAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> GithubAnalysisRead:
    svc = GitHubService(db)
    return await svc.analyze(payload)

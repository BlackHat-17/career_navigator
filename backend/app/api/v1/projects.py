"""
POST /api/v1/projects/recommend – forward to Project Recommender, persist, return result
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.project import ProjectRecommendRead, ProjectRecommendRequest
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "/recommend",
    response_model=ProjectRecommendRead,
    status_code=status.HTTP_200_OK,
    summary="Get project recommendations for a candidate",
    description=(
        "Forwards career goal, verified skills, and skill gaps to the "
        "Project Recommender service. The backend does not generate "
        "recommendations itself."
    ),
)
async def recommend_projects(
    payload: ProjectRecommendRequest,
    db: AsyncSession = Depends(get_db),
) -> ProjectRecommendRead:
    svc = ProjectService(db)
    return await svc.recommend(payload)

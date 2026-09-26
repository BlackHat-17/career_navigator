"""
POST /api/v1/roadmap/generate          – forward to Roadmap Generator, persist, return result
GET  /api/v1/roadmap/{analysis_id}     – fetch stored roadmap by analysis ID
"""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.roadmap import RoadmapGenerateRequest, RoadmapRead
from app.services.roadmap_service import RoadmapService

router = APIRouter(prefix="/roadmap", tags=["Roadmap"])


@router.post(
    "/generate",
    response_model=RoadmapRead,
    status_code=status.HTTP_200_OK,
    summary="Generate a personalised learning roadmap",
    description=(
        "Forwards career goal, current skills, skill gaps, and recommended "
        "projects to the Roadmap Generator service. "
        "The backend does not generate the roadmap itself."
    ),
)
async def generate_roadmap(
    payload: RoadmapGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> RoadmapRead:
    svc = RoadmapService(db)
    return await svc.generate(payload)


@router.get(
    "/{analysis_id}",
    response_model=RoadmapRead,
    summary="Retrieve stored roadmap for an analysis",
)
async def get_roadmap(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> RoadmapRead:
    svc = RoadmapService(db)
    return await svc.get_by_analysis(analysis_id)

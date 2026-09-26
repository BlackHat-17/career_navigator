"""
POST /api/v1/resume/analyze – multipart upload, validate, forward to Resume Judge
"""
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import InvalidFileTypeError
from app.schemas.resume import ResumeAnalysisRead, ResumeAnalyzeRequest
from app.services.resume_service import ALLOWED_EXTENSIONS, ResumeService

router = APIRouter(prefix="/resume", tags=["Resume"])


@router.post(
    "/analyze",
    response_model=ResumeAnalysisRead,
    status_code=status.HTTP_200_OK,
    summary="Analyse a candidate's resume",
    description=(
        "Accepts a multipart/form-data request with user_id, target_role, "
        "and a resume file (PDF / DOC / DOCX). "
        "Forwards extracted text to the Resume Judge service."
    ),
)
async def analyze_resume(
    user_id: UUID = Form(..., description="UUID of the user"),
    target_role: str = Form(..., min_length=1, max_length=200),
    resume_file: UploadFile = File(
        ...,
        description=f"Resume file. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
    ),
    db: AsyncSession = Depends(get_db),
) -> ResumeAnalysisRead:
    # Build the metadata schema (file is handled separately)
    request = ResumeAnalyzeRequest(user_id=user_id, target_role=target_role)
    svc = ResumeService(db)
    return await svc.analyze(request, resume_file)

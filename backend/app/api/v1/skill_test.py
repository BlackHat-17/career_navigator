"""
Skill Verification Test API endpoints.

POST /api/v1/skill-test/generate  -> generate a test session
POST /api/v1/skill-test/submit    -> submit answers and get results
"""
from fastapi import APIRouter, HTTPException, status

from app.schemas.skill_test import (
    SkillTestRequest,
    SkillTestSession,
    SkillTestSubmission,
    SkillTestResult,
)
from app.services.skill_test_service import SkillTestService

router = APIRouter(prefix="/skill-test", tags=["skill-test"])
_service = SkillTestService()


@router.post(
    "/generate",
    response_model=SkillTestSession,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a skill verification test session",
)
async def generate_test(req: SkillTestRequest) -> SkillTestSession:
    """
    Accepts claimed, partial, and missing skills from the analysis pipeline
    and returns a secure MCQ test session. Answer key is stored server-side only.
    """
    total_skills = len(req.claimed_skills) + len(req.partial_skills) + len(req.missing_skills)
    if total_skills == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one skill (claimed, partial, or missing) must be provided.",
        )
    try:
        return await _service.generate_session(req)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate test: {exc}",
        )


@router.post(
    "/submit",
    response_model=SkillTestResult,
    status_code=status.HTTP_200_OK,
    summary="Submit test answers and receive scored results",
)
def submit_test(submission: SkillTestSubmission) -> SkillTestResult:
    """
    Scores the submitted answers against the server-side answer key.
    Applies anti-cheat penalty to the integrity report.
    Session is deleted after scoring.
    """
    try:
        return _service.score_submission(
            session_id=submission.session_id,
            answers=submission.answers,
            anti_cheat_events=submission.anti_cheat_events,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to score test: {exc}",
        )

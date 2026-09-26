"""
Tests for:
  POST /api/v1/analysis          – full orchestration
  GET  /api/v1/analysis/{id}     – status + result retrieval
  POST /api/v1/analysis/skills   – standalone skill analysis
"""
import io
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _create_user(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/users",
        json={"name": "Dev", "email": f"{uuid.uuid4()}@test.com"},
    )
    return resp.json()["id"]


def _pdf_bytes() -> bytes:
    return b"%PDF-1.4 fake pdf content"


# ── Full orchestration ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_analysis_success(client: AsyncClient, mock_orchestration_clients):
    user_id = await _create_user(client)

    with patch(
        "app.services.orchestration_service.ResumeService._save_file_static",
        new_callable=AsyncMock,
        return_value="/tmp/test.pdf",
    ), patch(
        "app.services.orchestration_service.ResumeService._extract_text",
        return_value="Python developer resume",
    ):
        resp = await client.post(
            "/api/v1/analysis",
            data={
                "user_id": user_id,
                "github_username": "BlackHat-17",
                "target_role": "Backend Developer",
                "job_description": "We need a backend developer with Python and Docker.",
            },
            files={"resume_file": ("resume.pdf", _pdf_bytes(), "application/pdf")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["candidate"]["user_id"] == user_id
    assert len(data["skills"]["verified"]) == 1
    assert data["skills"]["verified"][0]["name"] == "Python"
    assert len(data["skills"]["missing"]) == 1
    assert data["summary"]["skill_match"] > 0


@pytest.mark.asyncio
async def test_full_analysis_user_not_found(client: AsyncClient, mock_orchestration_clients):
    with patch(
        "app.services.orchestration_service.ResumeService._save_file_static",
        new_callable=AsyncMock,
        return_value="/tmp/test.pdf",
    ), patch(
        "app.services.orchestration_service.ResumeService._extract_text",
        return_value="",
    ):
        resp = await client.post(
            "/api/v1/analysis",
            data={
                "user_id": str(uuid.uuid4()),
                "github_username": "BlackHat-17",
                "target_role": "Backend Developer",
                "job_description": "Python and Docker required.",
            },
            files={"resume_file": ("resume.pdf", _pdf_bytes(), "application/pdf")},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_full_analysis_missing_resume(client: AsyncClient):
    user_id = await _create_user(client)
    resp = await client.post(
        "/api/v1/analysis",
        data={
            "user_id": user_id,
            "github_username": "BlackHat-17",
            "target_role": "Backend Developer",
            "job_description": "Python required.",
        },
        # no resume_file
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_full_analysis_github_service_timeout_falls_back_to_mock(client: AsyncClient):
    user_id = await _create_user(client)
    from app.core.exceptions import ServiceTimeoutError

    with patch(
        "app.services.orchestration_service.GitHubAgentClient", autospec=True
    ) as MockClass, patch(
        "app.services.orchestration_service.ResumeJudgeClient", autospec=True
    ) as ResumeMock, patch(
        "app.services.orchestration_service.ProjectRecommenderClient", autospec=True
    ) as ProjectMock, patch(
        "app.services.orchestration_service.RoadmapGeneratorClient", autospec=True
    ) as RoadmapMock, patch(
        "app.services.orchestration_service.ResumeService._save_file_static",
        new_callable=AsyncMock,
        return_value="/tmp/test.pdf",
    ), patch(
        "app.services.orchestration_service.ResumeService._extract_text",
        return_value="Python developer resume",
    ):
        instance = MockClass.return_value.__aenter__.return_value
        instance.analyze = AsyncMock(side_effect=ServiceTimeoutError("Timed out"))

        resume_instance = ResumeMock.return_value.__aenter__.return_value
        resume_instance.analyze_resume = AsyncMock(return_value={
            "claimed_skills": [{"name": "Python", "context": "Python", "confidence": 0.9}],
            "feedback": [],
            "overall_score": 80,
        })
        resume_instance.analyze_skills = AsyncMock(return_value={
            "verified_skills": [{"name": "Python", "confidence": 0.9, "evidence": ["Python"]}],
            "partial_skills": [],
            "missing_skills": [{"name": "Docker", "confidence": None, "evidence": []}],
            "unsupported_claims": [],
        })

        project_instance = ProjectMock.return_value.__aenter__.return_value
        project_instance.recommend = AsyncMock(return_value={
            "recommendations": [{"title": "Build API", "description": "desc", "skills": ["Python"], "difficulty": "easy", "reason": "x"}]
        })

        roadmap_instance = RoadmapMock.return_value.__aenter__.return_value
        roadmap_instance.generate = AsyncMock(return_value={
            "career_goal": "Backend Developer",
            "total_weeks": 4,
            "summary": "Plan",
            "roadmap": [{"week": 1, "topic": "Python", "description": "Learn", "resources": [], "milestone": "done", "skills_covered": ["Python"]}],
        })

        resp = await client.post(
            "/api/v1/analysis",
            data={
                "user_id": user_id,
                "github_username": "BlackHat-17",
                "target_role": "Backend Developer",
                "job_description": "Python required.",
            },
            files={"resume_file": ("resume.pdf", _pdf_bytes(), "application/pdf")},
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"
    assert "candidate" in resp.json()


# ── Status retrieval ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_analysis_not_found(client: AsyncClient):
    resp = await client.get(f"/api/v1/analysis/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_analysis_status_after_creation(client: AsyncClient, mock_orchestration_clients):
    user_id = await _create_user(client)

    with patch(
        "app.services.orchestration_service.ResumeService._save_file_static",
        new_callable=AsyncMock,
        return_value="/tmp/test.pdf",
    ), patch(
        "app.services.orchestration_service.ResumeService._extract_text",
        return_value="text",
    ):
        create_resp = await client.post(
            "/api/v1/analysis",
            data={
                "user_id": user_id,
                "github_username": "BlackHat-17",
                "target_role": "Backend Developer",
                "job_description": "Python and Docker required.",
            },
            files={"resume_file": ("resume.pdf", _pdf_bytes(), "application/pdf")},
        )

    analysis_id = create_resp.json()["analysis_id"]
    status_resp = await client.get(f"/api/v1/analysis/{analysis_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "COMPLETED"
    assert status_resp.json()["result"] is not None

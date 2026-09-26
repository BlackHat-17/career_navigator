"""Tests for POST /api/v1/projects/recommend."""
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


@pytest.mark.asyncio
async def test_project_recommend_success(client: AsyncClient, mock_project_client):
    user_id = await _create_user(client)
    resp = await client.post(
        "/api/v1/projects/recommend",
        json={
            "user_id": user_id,
            "career_goal": "Backend Developer",
            "verified_skills": ["Python", "FastAPI"],
            "skill_gaps": ["Docker", "Kubernetes"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["recommendations"]) == 1
    assert data["recommendations"][0]["title"] == "Production FastAPI Service"
    assert "analysis_id" in data


@pytest.mark.asyncio
async def test_project_recommend_user_not_found(client: AsyncClient, mock_project_client):
    resp = await client.post(
        "/api/v1/projects/recommend",
        json={
            "user_id": str(uuid.uuid4()),
            "career_goal": "Backend Developer",
            "verified_skills": [],
            "skill_gaps": [],
        },
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_project_recommend_missing_career_goal(client: AsyncClient):
    resp = await client.post(
        "/api/v1/projects/recommend",
        json={
            "user_id": str(uuid.uuid4()),
            "verified_skills": [],
            "skill_gaps": [],
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_project_recommend_service_timeout(client: AsyncClient):
    user_id = await _create_user(client)
    from app.core.exceptions import ServiceTimeoutError

    with patch("app.services.project_service.ProjectRecommenderClient", autospec=True) as MockClass:
        instance = MockClass.return_value.__aenter__.return_value
        instance.recommend = AsyncMock(side_effect=ServiceTimeoutError("Timed out"))

        resp = await client.post(
            "/api/v1/projects/recommend",
            json={
                "user_id": user_id,
                "career_goal": "Backend Developer",
                "verified_skills": [],
                "skill_gaps": [],
            },
        )
    assert resp.status_code == 504

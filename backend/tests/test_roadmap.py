"""Tests for POST /api/v1/roadmap/generate and GET /api/v1/roadmap/{analysis_id}."""
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
async def test_roadmap_generate_success(client: AsyncClient, mock_roadmap_client):
    user_id = await _create_user(client)
    resp = await client.post(
        "/api/v1/roadmap/generate",
        json={
            "user_id": user_id,
            "career_goal": "Backend Developer",
            "current_skills": ["Python"],
            "skill_gaps": ["Docker"],
            "recommended_projects": ["Production FastAPI Service"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["career_goal"] == "Backend Developer"
    assert data["total_weeks"] == 8
    assert len(data["roadmap"]) == 1
    assert data["roadmap"][0]["week"] == 1
    assert "roadmap_id" in data


@pytest.mark.asyncio
async def test_roadmap_generate_user_not_found(client: AsyncClient, mock_roadmap_client):
    resp = await client.post(
        "/api/v1/roadmap/generate",
        json={
            "user_id": str(uuid.uuid4()),
            "career_goal": "Backend Developer",
            "current_skills": [],
            "skill_gaps": [],
            "recommended_projects": [],
        },
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_roadmap_generate_service_unavailable(client: AsyncClient):
    user_id = await _create_user(client)
    from app.core.exceptions import ServiceUnavailableError

    with patch("app.services.roadmap_service.RoadmapGeneratorClient", autospec=True) as MockClass:
        instance = MockClass.return_value.__aenter__.return_value
        instance.generate = AsyncMock(side_effect=ServiceUnavailableError("down"))

        resp = await client.post(
            "/api/v1/roadmap/generate",
            json={
                "user_id": user_id,
                "career_goal": "Backend Developer",
                "current_skills": [],
                "skill_gaps": [],
                "recommended_projects": [],
            },
        )
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_get_roadmap_not_found(client: AsyncClient):
    resp = await client.get(f"/api/v1/roadmap/{uuid.uuid4()}")
    assert resp.status_code == 404

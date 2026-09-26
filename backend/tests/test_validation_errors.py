"""
Tests that confirm the API returns consistent error shapes for bad inputs.
All errors must match: { "success": false, "error": { "code": "...", "message": "..." } }
"""
import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_error_shape_validation(client: AsyncClient):
    """422 responses must have the standard error shape."""
    resp = await client.post("/api/v1/users", json={})
    assert resp.status_code == 422
    body = resp.json()
    assert body["success"] is False
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]


@pytest.mark.asyncio
async def test_error_shape_not_found(client: AsyncClient):
    """404 responses must have the standard error shape."""
    resp = await client.get(f"/api/v1/users/{uuid.uuid4()}")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_unknown_route_returns_404(client: AsyncClient):
    resp = await client.get("/api/v1/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_github_invalid_uuid_user(client: AsyncClient):
    resp = await client.post(
        "/api/v1/github/analyze",
        json={"user_id": "bad-uuid", "github_username": "user"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_job_missing_description(client: AsyncClient):
    resp = await client.post(
        "/api/v1/jobs/analyze",
        json={"user_id": str(uuid.uuid4()), "title": "Dev"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_roadmap_missing_career_goal(client: AsyncClient):
    resp = await client.post(
        "/api/v1/roadmap/generate",
        json={
            "user_id": str(uuid.uuid4()),
            "current_skills": [],
            "skill_gaps": [],
            "recommended_projects": [],
        },
    )
    assert resp.status_code == 422

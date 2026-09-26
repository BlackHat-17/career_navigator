"""Tests for POST /api/v1/github/analyze."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest
import httpx
from httpx import AsyncClient


async def _create_user(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/users",
        json={"name": "Dev", "email": f"{uuid.uuid4()}@test.com"},
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_github_analyze_success(client: AsyncClient, mock_github_client):
    user_id = await _create_user(client)
    resp = await client.post(
        "/api/v1/github/analyze",
        json={"user_id": user_id, "github_username": "BlackHat-17"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["github_username"] == "BlackHat-17"
    assert len(data["skills"]) == 2
    assert data["skills"][0]["name"] == "Python"
    assert "analysis_id" in data


@pytest.mark.asyncio
async def test_github_analyze_invalid_username(client: AsyncClient):
    resp = await client.post(
        "/api/v1/github/analyze",
        json={"user_id": str(uuid.uuid4()), "github_username": ""},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_github_analyze_user_not_found(client: AsyncClient, mock_github_client):
    resp = await client.post(
        "/api/v1/github/analyze",
        json={"user_id": str(uuid.uuid4()), "github_username": "someuser"},
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_github_analyze_service_unavailable(client: AsyncClient):
    user_id = await _create_user(client)
    with patch(
        "app.services.github_service.GitHubAgentClient",
        autospec=True,
    ) as MockClass:
        instance = MockClass.return_value.__aenter__.return_value
        instance.analyze = AsyncMock(
            side_effect=__import__(
                "app.core.exceptions", fromlist=["ServiceUnavailableError"]
            ).ServiceUnavailableError("GitHub Agent is down")
        )
        resp = await client.post(
            "/api/v1/github/analyze",
            json={"user_id": user_id, "github_username": "BlackHat-17"},
        )
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_github_analyze_service_timeout(client: AsyncClient):
    user_id = await _create_user(client)
    with patch(
        "app.services.github_service.GitHubAgentClient",
        autospec=True,
    ) as MockClass:
        instance = MockClass.return_value.__aenter__.return_value
        instance.analyze = AsyncMock(
            side_effect=__import__(
                "app.core.exceptions", fromlist=["ServiceTimeoutError"]
            ).ServiceTimeoutError("Timed out")
        )
        resp = await client.post(
            "/api/v1/github/analyze",
            json={"user_id": user_id, "github_username": "BlackHat-17"},
        )
    assert resp.status_code == 504
    assert resp.json()["error"]["code"] == "SERVICE_TIMEOUT"

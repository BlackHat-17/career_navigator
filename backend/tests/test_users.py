"""Tests for POST /api/v1/users and GET /api/v1/users/{id}."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_user_success(client: AsyncClient):
    resp = await client.post(
        "/api/v1/users",
        json={"name": "Aditya", "email": "aditya@example.com", "career_goal": "Backend Dev"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "aditya@example.com"
    assert data["name"] == "Aditya"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_user_duplicate_email(client: AsyncClient):
    payload = {"name": "Alice", "email": "alice@example.com", "career_goal": "Dev"}
    await client.post("/api/v1/users", json=payload)
    resp = await client.post("/api/v1/users", json=payload)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_create_user_invalid_email(client: AsyncClient):
    resp = await client.post(
        "/api/v1/users",
        json={"name": "Bob", "email": "not-an-email", "career_goal": "Dev"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_create_user_missing_name(client: AsyncClient):
    resp = await client.post(
        "/api/v1/users",
        json={"email": "bob@example.com"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_user_success(client: AsyncClient):
    create = await client.post(
        "/api/v1/users",
        json={"name": "Carol", "email": "carol@example.com"},
    )
    user_id = create.json()["id"]
    resp = await client.get(f"/api/v1/users/{user_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == user_id


@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient):
    import uuid
    resp = await client.get(f"/api/v1/users/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_user_invalid_uuid(client: AsyncClient):
    resp = await client.get("/api/v1/users/not-a-uuid")
    assert resp.status_code == 422

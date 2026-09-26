"""Tests for the roadmap foundation contract.

These tests validate the new input boundary:
    missing_skills + partial_skills
and the explicit classification of skills before any AI roadmap generation.
"""
import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_roadmap_generate_success(client: AsyncClient):
    resp = await client.post(
        "/api/v1/roadmap/generate",
        json={
            "missing_skills": ["Docker", "Kubernetes"],
            "partial_skills": ["FastAPI", "AWS"],
        },
    )
    assert resp.status_code == 200

    data = resp.json()
    assert "roadmap_id" in data
    assert isinstance(data["skills"], list)
    assert {skill["name"] for skill in data["skills"]} == {"Docker", "Kubernetes", "FastAPI", "AWS"}

    missing = {skill["name"]: skill for skill in data["skills"] if skill["classification"] == "missing"}
    partial = {skill["name"]: skill for skill in data["skills"] if skill["classification"] == "partial"}

    assert set(missing) == {"Docker", "Kubernetes"}
    assert set(partial) == {"FastAPI", "AWS"}

    assert all(skill.get("learning_track") is not None for skill in missing.values())
    assert all(skill.get("learning_track") is None for skill in partial.values())


@pytest.mark.asyncio
async def test_roadmap_generate_accepts_missing_only(client: AsyncClient):
    resp = await client.post(
        "/api/v1/roadmap/generate",
        json={
            "missing_skills": ["Docker"],
            "partial_skills": [],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["skills"][0]["classification"] == "missing"
    assert data["skills"][0]["name"] == "Docker"
    assert data["skills"][0]["learning_track"] == []


@pytest.mark.asyncio
async def test_get_roadmap_returns_generated_roadmap(client: AsyncClient):
    generated = await client.post(
        "/api/v1/roadmap/generate",
        json={"missing_skills": ["Docker"], "partial_skills": []},
    )
    assert generated.status_code == 200

    roadmap_id = generated.json()["roadmap_id"]
    retrieved = await client.get(f"/api/v1/roadmap/{roadmap_id}")

    assert retrieved.status_code == 200
    data = retrieved.json()
    assert data["roadmap_id"] == roadmap_id
    assert data["skills"][0]["name"] == "Docker"
    assert data["skills"][0]["classification"] == "missing"


@pytest.mark.asyncio
async def test_roadmap_generate_rejects_invalid_skill_values(client: AsyncClient):
    resp = await client.post(
        "/api/v1/roadmap/generate",
        json={"missing_skills": ["Docker", 42], "partial_skills": []},
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_roadmap_generate_defaults_missing_skill_lists(client: AsyncClient):
    resp = await client.post("/api/v1/roadmap/generate", json={})

    assert resp.status_code == 200
    assert resp.json()["skills"] == []


@pytest.mark.asyncio
async def test_get_roadmap_not_found(client: AsyncClient):
    resp = await client.get(f"/api/v1/roadmap/{uuid.uuid4()}")
    assert resp.status_code == 404

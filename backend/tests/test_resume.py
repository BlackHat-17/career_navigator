"""Tests for POST /api/v1/resume/analyze (multipart)."""
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
    """Minimal valid-ish PDF bytes for upload tests."""
    return b"%PDF-1.4 fake pdf content for testing"


@pytest.mark.asyncio
async def test_resume_analyze_success(client: AsyncClient, mock_resume_client):
    user_id = await _create_user(client)

    with patch("app.services.resume_service.ResumeService._save_file_static", new_callable=AsyncMock) as mock_save, \
         patch("app.services.resume_service.ResumeService._extract_text", return_value="Python developer resume"):
        mock_save.return_value = "/tmp/test_resume.pdf"

        resp = await client.post(
            "/api/v1/resume/analyze",
            data={"user_id": user_id, "target_role": "Backend Developer"},
            files={"resume_file": ("resume.pdf", _pdf_bytes(), "application/pdf")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["target_role"] == "Backend Developer"
    assert data["user_id"] == user_id
    assert "analysis_id" in data
    assert len(data["claimed_skills"]) == 2


@pytest.mark.asyncio
async def test_resume_analyze_invalid_file_type(client: AsyncClient):
    user_id = await _create_user(client)
    resp = await client.post(
        "/api/v1/resume/analyze",
        data={"user_id": user_id, "target_role": "Dev"},
        files={"resume_file": ("malware.exe", b"binary content", "application/octet-stream")},
    )
    assert resp.status_code == 415
    assert resp.json()["error"]["code"] == "INVALID_FILE_TYPE"


@pytest.mark.asyncio
async def test_resume_analyze_missing_fields(client: AsyncClient):
    resp = await client.post(
        "/api/v1/resume/analyze",
        data={"target_role": "Dev"},
        files={"resume_file": ("resume.pdf", _pdf_bytes(), "application/pdf")},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_resume_analyze_service_unavailable(client: AsyncClient):
    user_id = await _create_user(client)
    from app.core.exceptions import ServiceUnavailableError

    with patch("app.services.resume_service.ResumeService._save_file_static", new_callable=AsyncMock) as mock_save, \
         patch("app.services.resume_service.ResumeService._extract_text", return_value="text"), \
         patch("app.services.resume_service.ResumeJudgeClient", autospec=True) as MockClass:
        mock_save.return_value = "/tmp/test.pdf"
        instance = MockClass.return_value.__aenter__.return_value
        instance.analyze_resume = AsyncMock(
            side_effect=ServiceUnavailableError("Resume Judge is down")
        )
        resp = await client.post(
            "/api/v1/resume/analyze",
            data={"user_id": user_id, "target_role": "Dev"},
            files={"resume_file": ("resume.pdf", _pdf_bytes(), "application/pdf")},
        )
    assert resp.status_code == 503

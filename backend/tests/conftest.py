"""
Shared pytest fixtures.

Key design choices:
  - Uses an in-memory SQLite database (via aiosqlite) so tests run without
    a real PostgreSQL instance.
  - All four AI-service clients are patched at the service layer so no
    real HTTP calls are ever made.
  - Every test gets a fresh database via the `db` fixture (function scope).
"""
from __future__ import annotations

import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import create_app

# ── In-memory test database ───────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables once per test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean session per test, rolled back after each test."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


# ── FastAPI test client ───────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    AsyncClient wired to the FastAPI app with the test DB session injected.
    All four AI service clients are mocked out here.
    """
    app = create_app()

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ── AI service mock payloads ──────────────────────────────────────────────────

MOCK_GITHUB_RESPONSE = {
    "skills": [
        {"name": "Python", "confidence": 0.95, "evidence": ["Flask backend", "ML scripts"]},
        {"name": "FastAPI", "confidence": 0.88, "evidence": ["REST API project"]},
    ],
    "projects": [
        {
            "name": "career-api",
            "description": "A FastAPI project",
            "url": "https://github.com/user/career-api",
            "languages": ["Python"],
            "topics": ["fastapi", "backend"],
        }
    ],
    "recommended_projects": [],
}

MOCK_RESUME_RESPONSE = {
    "claimed_skills": [
        {"name": "Python", "context": "5 years Python experience", "confidence": 0.92},
        {"name": "Docker", "context": "Containerised microservices", "confidence": 0.75},
    ],
    "feedback": [
        {"section": "experience", "comment": "Quantify impact.", "severity": "warning"}
    ],
    "overall_score": 72.5,
}

MOCK_SKILL_ANALYSIS_RESPONSE = {
    "verified_skills": [
        {"name": "Python", "confidence": 0.93, "evidence": ["Flask backend", "5 years Python"]},
    ],
    "partial_skills": [
        {"name": "Docker", "confidence": 0.75, "evidence": []},
    ],
    "missing_skills": [
        {"name": "Kubernetes", "confidence": None, "evidence": []},
    ],
    "unsupported_claims": [],
}

MOCK_PROJECT_RESPONSE = {
    "recommendations": [
        {
            "title": "Production FastAPI Service",
            "description": "Build a production-grade API",
            "skills": ["FastAPI", "Docker"],
            "difficulty": "intermediate",
            "reason": "Addresses Docker gap",
        }
    ]
}

MOCK_ROADMAP_RESPONSE = {
    "career_goal": "Backend Developer",
    "total_weeks": 8,
    "summary": "An 8-week plan.",
    "roadmap": [
        {
            "week": 1,
            "topic": "Docker Fundamentals",
            "description": "Learn Docker basics",
            "resources": ["https://docs.docker.com/get-started/"],
            "milestone": "Containerise a FastAPI app",
            "skills_covered": ["Docker"],
        }
    ],
}


# ── Reusable mock patch helpers ───────────────────────────────────────────────

@pytest.fixture
def mock_github_client():
    with patch(
        "app.services.github_service.GitHubAgentClient",
        autospec=True,
    ) as MockClass:
        instance = MockClass.return_value.__aenter__.return_value
        instance.analyze = AsyncMock(return_value=MOCK_GITHUB_RESPONSE)
        yield instance


@pytest.fixture
def mock_resume_client():
    with patch(
        "app.services.resume_service.ResumeJudgeClient",
        autospec=True,
    ) as MockClass:
        instance = MockClass.return_value.__aenter__.return_value
        instance.analyze_resume = AsyncMock(return_value=MOCK_RESUME_RESPONSE)
        instance.analyze_skills = AsyncMock(return_value=MOCK_SKILL_ANALYSIS_RESPONSE)
        yield instance


@pytest.fixture
def mock_project_client():
    with patch(
        "app.services.project_service.ProjectRecommenderClient",
        autospec=True,
    ) as MockClass:
        instance = MockClass.return_value.__aenter__.return_value
        instance.recommend = AsyncMock(return_value=MOCK_PROJECT_RESPONSE)
        yield instance


@pytest.fixture
def mock_roadmap_client():
    with patch(
        "app.services.roadmap_service.RoadmapGeneratorClient",
        autospec=True,
    ) as MockClass:
        instance = MockClass.return_value.__aenter__.return_value
        instance.generate = AsyncMock(return_value=MOCK_ROADMAP_RESPONSE)
        yield instance


@pytest.fixture
def mock_orchestration_clients():
    """Patch all four clients as used inside orchestration_service."""
    with (
        patch("app.services.orchestration_service.GitHubAgentClient", autospec=True) as GH,
        patch("app.services.orchestration_service.ResumeJudgeClient", autospec=True) as RJ,
        patch("app.services.orchestration_service.ProjectRecommenderClient", autospec=True) as PR,
        patch("app.services.orchestration_service.RoadmapGeneratorClient", autospec=True) as RG,
    ):
        gh = GH.return_value.__aenter__.return_value
        gh.analyze = AsyncMock(return_value=MOCK_GITHUB_RESPONSE)

        rj = RJ.return_value.__aenter__.return_value
        rj.analyze_resume = AsyncMock(return_value=MOCK_RESUME_RESPONSE)
        rj.analyze_skills = AsyncMock(return_value=MOCK_SKILL_ANALYSIS_RESPONSE)

        pr = PR.return_value.__aenter__.return_value
        pr.recommend = AsyncMock(return_value=MOCK_PROJECT_RESPONSE)

        rg = RG.return_value.__aenter__.return_value
        rg.generate = AsyncMock(return_value=MOCK_ROADMAP_RESPONSE)

        yield {"github": gh, "resume": rj, "project": pr, "roadmap": rg}

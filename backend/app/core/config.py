import json
from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────
    APP_NAME: str = "Career Navigator API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # ── Server ───────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins(self) -> List[str]:
        value = self.CORS_ORIGINS.strip()
        if not value:
            return []

        if value.startswith("["):
            try:
                parsed = json.loads(value)
            except ValueError:
                parsed = []
            if isinstance(parsed, list):
                return [str(origin).strip() for origin in parsed if str(origin).strip()]

        return [origin.strip() for origin in value.split(",") if origin.strip()]

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:password@localhost:5432/career_navigator"
    )

    # ── File uploads ─────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_RESUME_TYPES: List[str] = ["application/pdf", "application/msword",
                                        "application/vnd.openxmlformats-officedocument"
                                        ".wordprocessingml.document"]
    UPLOAD_DIR: str = "/tmp/career_navigator_uploads"

    # ── AI module toggles ─────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.7-flash"
    GEMINI_FALLBACK_MODELS: str = "gemini-3.5-flash,gemini-3.8-flash"
    
    # ── Grok (xAI) fallback ───────────────────────────────────────────────
    GROK_ENABLED: bool = False
    GROK_API_KEY: str = ""
    GROK_MODEL: str = "grok-beta"
    
    # ── NVIDIA API Catalog fallback ───────────────────────────────────────
    NVIDIA_ENABLED: bool = False
    NVIDIA_API_KEY: str = ""
    NVIDIA_MODEL: str = "meta/llama-3.1-70b-instruct"
    
    # ── Local LLM (Ollama) fallback ───────────────────────────────────────
    OLLAMA_ENABLED: bool = False
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    
    MOCK_MODE: bool = False

    # ── GitHub Evidence Matching (real-time, no external agent) ────────────
    GITHUB_TOKEN: str = ""
    GITHUB_MAX_REPOS: int = 15

    @property
    def gemini_models_priority(self) -> List[str]:
        """Returns list of models to try in order: primary + fallbacks"""
        models = [self.GEMINI_MODEL]
        if self.GEMINI_FALLBACK_MODELS:
            models.extend([m.strip() for m in self.GEMINI_FALLBACK_MODELS.split(",") if m.strip()])
        return models

    # ── External AI service URLs ──────────────────────────────────────────
    GITHUB_AGENT_URL: str = "http://localhost:8001"
    RESUME_JUDGE_URL: str = "http://localhost:8002"
    PROJECT_RECOMMENDER_URL: str = "http://localhost:8003"
    ROADMAP_GENERATOR_URL: str = "http://localhost:8004"

    # ── HTTP client timeouts (seconds) ────────────────────────────────────
    SERVICE_TIMEOUT: float = 30.0
    SERVICE_CONNECT_TIMEOUT: float = 5.0

    # ── Security ─────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production"

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()

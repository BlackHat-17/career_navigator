from fastapi.testclient import TestClient

from app.main import app


def test_cors_origins_accepts_comma_separated_env_value(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")

    import app.core.config as config_module

    config_module.get_settings.cache_clear()
    settings = config_module.get_settings()

    assert settings.cors_origins == [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    assert settings.GEMINI_MODEL == "gemini-3.8-flash"

    config_module.get_settings.cache_clear()


def test_stream_returns_event_stream_for_missing_jobs():
    client = TestClient(app)

    response = client.get("/api/analyze/does-not-exist/stream")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "job not found" in response.text.lower()

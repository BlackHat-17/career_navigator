"""Unit tests for app/utils/helpers.py — no DB or HTTP needed."""
import pytest

from app.utils.helpers import (
    compute_skill_match_score,
    flatten_skills,
    is_valid_uuid,
    safe_get,
    sanitize_filename,
    slugify,
    truncate,
)


def test_is_valid_uuid_true():
    import uuid
    assert is_valid_uuid(str(uuid.uuid4())) is True


def test_is_valid_uuid_false():
    assert is_valid_uuid("not-a-uuid") is False
    assert is_valid_uuid("") is False


def test_slugify_basic():
    assert slugify("Hello World!") == "hello-world"


def test_slugify_max_length():
    long = "a" * 200
    assert len(slugify(long, max_length=10)) <= 10


def test_sanitize_filename_strips_paths():
    result = sanitize_filename("../../etc/passwd.pdf")
    assert "/" not in result
    assert result.endswith(".pdf")


def test_sanitize_filename_safe():
    assert sanitize_filename("my resume.pdf") == "myresume.pdf"


def test_flatten_skills_from_github():
    raw = {
        "skills": [
            {"name": "Python", "confidence": 0.9},
            {"name": "FastAPI", "confidence": 0.8},
        ]
    }
    result = flatten_skills(raw)
    assert result == ["Python", "FastAPI"]


def test_flatten_skills_deduplicates():
    raw = {
        "skills": [{"name": "Python"}, {"name": "Python"}],
    }
    assert flatten_skills(raw) == ["Python"]


def test_safe_get_nested():
    d = {"a": {"b": {"c": 42}}}
    assert safe_get(d, "a", "b", "c") == 42


def test_safe_get_missing_key():
    assert safe_get({}, "x", "y", default="fallback") == "fallback"


def test_truncate_no_change():
    assert truncate("short", max_chars=100) == "short"


def test_truncate_cuts():
    result = truncate("a" * 600, max_chars=500)
    assert len(result) == 500
    assert result.endswith("…")


def test_compute_skill_match_all_verified():
    assert compute_skill_match_score(10, 0, 0) == 100.0


def test_compute_skill_match_all_missing():
    assert compute_skill_match_score(0, 0, 10) == 0.0


def test_compute_skill_match_mixed():
    # 4 verified, 2 partial, 4 missing  → (4 + 1) / 10 * 100 = 50.0
    assert compute_skill_match_score(4, 2, 4) == 50.0


def test_compute_skill_match_zero_total():
    assert compute_skill_match_score(0, 0, 0) == 0.0

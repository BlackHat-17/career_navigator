"""
General-purpose helpers used across the backend.
"""
from __future__ import annotations

import re
import unicodedata
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


def is_valid_uuid(value: str) -> bool:
    """Return True if *value* is a well-formed UUID string."""
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False


def slugify(text: str, max_length: int = 80) -> str:
    """
    Convert arbitrary text to a safe, lowercase, hyphen-separated slug.

    Example:
        slugify("Hello World!") → "hello-world"
    """
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:max_length]


def sanitize_filename(filename: str, max_length: int = 120) -> str:
    """
    Strip path traversal characters and reduce a filename to safe ASCII.

    Example:
        sanitize_filename("../../etc/passwd.pdf") → "etcpasswd.pdf"
    """
    name = Path(filename).name          # strip directories
    stem = Path(name).stem
    suffix = Path(name).suffix.lower()
    safe_stem = re.sub(r"[^\w\-]", "", stem)[:max_length]
    return f"{safe_stem}{suffix}" if safe_stem else f"upload{suffix}"


def flatten_skills(raw_output: Dict[str, Any]) -> List[str]:
    """
    Extract a flat list of skill names from a GitHub Agent or Resume Judge
    raw output dictionary.

    Handles both:
        {"skills": [{"name": "Python", ...}, ...]}
        {"claimed_skills": [{"name": "FastAPI", ...}, ...]}
    """
    skills: List[str] = []
    for key in ("skills", "claimed_skills", "verified_skills"):
        for item in raw_output.get(key, []):
            name = item.get("name", "").strip()
            if name:
                skills.append(name)
    return list(dict.fromkeys(skills))   # deduplicate, preserve order


def safe_get(d: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    Safely traverse a nested dict with dot-notation keys.

    Example:
        safe_get(data, "skills", "0", "name", default="")
    """
    current: Any = d
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        elif isinstance(current, list):
            try:
                current = current[int(key)]
            except (IndexError, ValueError):
                return default
        else:
            return default
    return current


def truncate(text: str, max_chars: int = 500, suffix: str = "…") -> str:
    """Truncate *text* to *max_chars*, appending *suffix* if trimmed."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - len(suffix)] + suffix


def compute_skill_match_score(
    verified: int,
    partial: int,
    missing: int,
) -> float:
    """
    Simple weighted score:
        verified = 1.0 point, partial = 0.5, missing = 0

    Returns a percentage (0.0 – 100.0).
    """
    total = verified + partial + missing
    if total == 0:
        return 0.0
    return round((verified + 0.5 * partial) / total * 100, 1)

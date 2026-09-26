"""
ResumeSkillService
──────────────────
Extracts skill claims from raw resume text using the same SKILL_TAXONOMY
that scores GitHub evidence, so both sides of the comparison speak the
same vocabulary.

This is intentionally a fast, deterministic keyword/alias matcher (word
boundaries, case-insensitive) rather than an LLM call — it needs to run
in real time on every request and stay 100% explainable ("why did you
say I know MongoDB?" -> "your resume mentions 'MongoDB' near ...").
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Dict, List

from app.core.logging import get_logger
from app.services.skill_taxonomy import SKILL_TAXONOMY

logger = get_logger(__name__)


@dataclass
class ResumeSkillClaim:
    skill_id: str
    skill: str
    context: str


def extract_resume_skills(resume_text: str) -> Dict[str, ResumeSkillClaim]:
    """Returns {skill_id: ResumeSkillClaim} for every skill mentioned in the resume."""
    text = resume_text or ""
    lowered = text.lower()
    found: Dict[str, ResumeSkillClaim] = {}

    for skill_id, signal in SKILL_TAXONOMY.items():
        for alias in signal.aliases:
            alias_clean = alias.strip().lower()
            if not alias_clean:
                continue
            if " " in alias_clean or "." in alias_clean or "#" in alias_clean or "+" in alias_clean:
                idx = lowered.find(alias_clean)
                match_len = len(alias_clean)
            else:
                m = re.search(rf"\b{re.escape(alias_clean)}\b", lowered)
                idx = m.start() if m else -1
                match_len = len(alias_clean)

            if idx != -1:
                start = max(0, idx - 40)
                end = min(len(text), idx + match_len + 40)
                context = text[start:end].strip().replace("\n", " ")
                found[skill_id] = ResumeSkillClaim(
                    skill_id=skill_id, skill=signal.name, context=context
                )
                break  # one alias match per skill is enough

    return found


def extract_text_from_bytes(content: bytes, mime: str, filename: str = "") -> str:
    """Best-effort plain-text extraction from an uploaded resume (PDF / DOCX)."""
    mime = (mime or "").lower()
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    try:
        if "pdf" in mime or ext == "pdf":
            import PyPDF2  # type: ignore
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        if "word" in mime or "docx" in mime or "document" in mime or ext in ("doc", "docx"):
            import docx  # type: ignore
            doc = docx.Document(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs)
    except Exception as exc:
        logger.warning("Resume text extraction failed (%s): %s", mime, exc)
    # Fall back: assume plain text
    try:
        return content.decode("utf-8", errors="ignore")
    except Exception:
        return ""

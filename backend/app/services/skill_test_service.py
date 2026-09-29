"""
Skill Verification Test Service.

Generates MCQ questions for claimed/partial/missing skills via LLM
with full multi-provider fallback chain:
  1. Gemini (3.7 → 3.5 → 3.8 flash)
  2. Grok  (xAI)
  3. NVIDIA API Catalog
  4. Ollama (local)
  5. Static fallback questions (always works)

Answer key is NEVER sent to the frontend — stored server-side only.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional

import httpx
import google.genai as genai

from app.core.config import get_settings
from app.schemas.skill_test import (
    AntiCheatEvent,
    DifficultyLevel,
    MCQOption,
    QuestionAnswer,
    SkillScore,
    SkillTestRequest,
    SkillTestResult,
    SkillTestSession,
    TestIntegrityReport,
    TestQuestion,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# ── In-memory session store (swap for Redis in production) ───────────────────
_sessions: Dict[str, Dict[str, Any]] = {}


# ── Difficulty helpers ───────────────────────────────────────────────────────
def _difficulty_for_category(category: str) -> DifficultyLevel:
    if category == "claimed":
        return DifficultyLevel.MEDIUM
    if category == "partial":
        return DifficultyLevel.EASY
    return DifficultyLevel.EASY   # missing — start gentle


def _time_limit(d: DifficultyLevel) -> int:
    return {DifficultyLevel.EASY: 45, DifficultyLevel.MEDIUM: 60, DifficultyLevel.HARD: 90}[d]


# ── LLM prompt ───────────────────────────────────────────────────────────────
QUESTION_PROMPT = """
You are an expert technical interviewer. Generate {n} multiple-choice questions \
to test a student's knowledge of "{skill}" for a {role} role.

Student relationship with this skill: {category_desc}
Difficulty: {difficulty}

Return ONLY a valid JSON array. Each element:
{{
  "question": "...",
  "options": [{{"id":"A","text":"..."}},{{"id":"B","text":"..."}},{{"id":"C","text":"..."}},{{"id":"D","text":"..."}}],
  "correct": "A",
  "explanation": "brief why"
}}

Rules:
- Practical, unambiguous questions
- Exactly one correct answer
- Plausible distractors
- No trick questions
- Do NOT embed the answer in the question text
"""

CATEGORY_DESCRIPTIONS = {
    "claimed": "Claims this skill on resume — verify depth of knowledge.",
    "partial": "Has some evidence but gaps remain — test fundamentals.",
    "missing": "Target skill gap — test foundational concepts gently.",
}

# ── Static fallback questions per skill keyword ──────────────────────────────
_STATIC_FALLBACK: Dict[str, List[Dict]] = {
    "default": [
        {
            "question": "Which principle best describes writing clean, maintainable code?",
            "options": [
                {"id": "A", "text": "Write once, never change"},
                {"id": "B", "text": "Single Responsibility Principle"},
                {"id": "C", "text": "Always use global variables"},
                {"id": "D", "text": "Avoid all abstractions"},
            ],
            "correct": "B",
        },
        {
            "question": "What does DRY stand for in software engineering?",
            "options": [
                {"id": "A", "text": "Deploy Repeatedly Yourself"},
                {"id": "B", "text": "Don't Repeat Yourself"},
                {"id": "C", "text": "Dynamic Runtime Yield"},
                {"id": "D", "text": "Data Redundancy Yield"},
            ],
            "correct": "B",
        },
        {
            "question": "Which data structure uses LIFO (Last In, First Out) ordering?",
            "options": [
                {"id": "A", "text": "Queue"},
                {"id": "B", "text": "Linked List"},
                {"id": "C", "text": "Stack"},
                {"id": "D", "text": "Heap"},
            ],
            "correct": "C",
        },
    ]
}


def _static_questions(skill: str, n: int, category: str, difficulty: DifficultyLevel) -> List[Dict]:
    """Return static fallback questions when all LLM providers fail."""
    base = _STATIC_FALLBACK.get(skill.lower(), _STATIC_FALLBACK["default"])
    # repeat to fill n if needed
    questions = (base * ((n // len(base)) + 1))[:n]
    return [
        {
            "question": f"[{skill}] " + q["question"],
            "options": q["options"],
            "correct": q["correct"],
        }
        for q in questions
    ]


def _clean_json(text: str) -> str:
    """Strip markdown fences and whitespace."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # extract JSON array
    start = text.find("[")
    end   = text.rfind("]") + 1
    if start != -1 and end > 0:
        return text[start:end]
    return text


# ════════════════════════════════════════════════════════════════════════════
class SkillTestService:
    """
    Generates MCQ sessions and scores submissions.
    Uses full LLM fallback: Gemini → Grok → NVIDIA → Ollama → static.
    """

    def __init__(self):
        self._gemini: Optional[genai.Client] = None
        key = os.environ.get("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        if key:
            self._gemini = genai.Client(api_key=key)

    # ── Provider 1: Gemini ────────────────────────────────────────────────
    async def _try_gemini(self, prompt: str) -> Optional[List[Any]]:
        if not self._gemini or not settings.GEMINI_API_KEY:
            return None
        for model in settings.gemini_models_priority:
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda m=model: self._gemini.models.generate_content(
                        model=m, contents=prompt,
                    ),
                )
                return json.loads(_clean_json(response.text or ""))
            except Exception as exc:
                logger.warning("Gemini %s failed for skill test: %s", model, exc)
                continue
        return None

    # ── Provider 2: Grok ──────────────────────────────────────────────────
    async def _try_grok(self, prompt: str) -> Optional[List[Any]]:
        if not settings.GROK_ENABLED or not settings.GROK_API_KEY:
            return None
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.GROK_API_KEY}"},
                    json={
                        "model": settings.GROK_MODEL,
                        "messages": [
                            {"role": "system", "content": "You are a technical interviewer. Return ONLY valid JSON arrays, no markdown."},
                            {"role": "user",   "content": prompt},
                        ],
                        "temperature": 0.3,
                    },
                )
                if r.status_code == 200:
                    text = r.json()["choices"][0]["message"]["content"]
                    return json.loads(_clean_json(text))
        except Exception as exc:
            logger.warning("Grok failed for skill test: %s", exc)
        return None

    # ── Provider 3: NVIDIA ────────────────────────────────────────────────
    async def _try_nvidia(self, prompt: str) -> Optional[List[Any]]:
        if not settings.NVIDIA_ENABLED or not settings.NVIDIA_API_KEY:
            return None
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    "https://integrate.api.nvidia.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.NVIDIA_API_KEY}"},
                    json={
                        "model": settings.NVIDIA_MODEL,
                        "messages": [
                            {"role": "system", "content": "You are a technical interviewer. Return ONLY valid JSON arrays, no markdown."},
                            {"role": "user",   "content": prompt},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 2048,
                    },
                )
                if r.status_code == 200:
                    text = r.json()["choices"][0]["message"]["content"]
                    return json.loads(_clean_json(text))
        except Exception as exc:
            logger.warning("NVIDIA failed for skill test: %s", exc)
        return None

    # ── Provider 4: Ollama ────────────────────────────────────────────────
    async def _try_ollama(self, prompt: str) -> Optional[List[Any]]:
        if not settings.OLLAMA_ENABLED:
            return None
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model":  settings.OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0.3, "num_predict": 2000},
                    },
                )
                if r.status_code == 200:
                    text = r.json().get("response", "")
                    return json.loads(_clean_json(text))
        except Exception as exc:
            logger.warning("Ollama failed for skill test: %s", exc)
        return None

    # ── Master LLM caller with full fallback chain ────────────────────────
    async def _generate_questions_llm(self, skill: str, category: str,
                                       difficulty: DifficultyLevel, n: int,
                                       role: str) -> tuple[List[Dict], bool]:
        """
        Returns (questions_list, used_fallback).
        Tries: Gemini → Grok → NVIDIA → Ollama → static fallback.
        """
        prompt = QUESTION_PROMPT.format(
            n=n, skill=skill, role=role,
            category_desc=CATEGORY_DESCRIPTIONS.get(category, ""),
            difficulty=difficulty.value,
        )

        for provider_fn, name in [
            (self._try_gemini,  "Gemini"),
            (self._try_grok,    "Grok"),
            (self._try_nvidia,  "NVIDIA"),
            (self._try_ollama,  "Ollama"),
        ]:
            try:
                result = await provider_fn(prompt)
                if result and isinstance(result, list) and len(result) > 0:
                    logger.info("Skill test questions for '%s' generated via %s", skill, name)
                    return result, False
            except Exception as exc:
                logger.warning("%s provider error for '%s': %s", name, skill, exc)
                continue

        # All providers failed — use static fallback
        logger.warning("All LLM providers failed for '%s' — using static questions", skill)
        return _static_questions(skill, n, category, difficulty), True

    # ── Generate session ──────────────────────────────────────────────────
    async def generate_session(self, req: SkillTestRequest) -> SkillTestSession:
        all_questions: List[TestQuestion] = []
        answer_key: Dict[str, str] = {}

        skill_buckets = [
            ("claimed",  req.claimed_skills[:4]),
            ("partial",  req.partial_skills[:4]),
            ("missing",  req.missing_skills[:3]),   # cap missing at 3
        ]

        tasks = []
        meta  = []
        for category, skills in skill_buckets:
            for skill in skills:
                difficulty = _difficulty_for_category(category)
                tasks.append(
                    self._generate_questions_llm(
                        skill, category, difficulty,
                        req.num_questions_per_skill, req.target_role,
                    )
                )
                meta.append((skill, category, difficulty))

        # Run all skills concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for (skill, category, difficulty), result in zip(meta, results):
            if isinstance(result, Exception):
                items, _ = _static_questions(skill, req.num_questions_per_skill, category, difficulty), True
            else:
                items, _ = result

            for item in items:
                qid = str(uuid.uuid4())[:8]
                q = TestQuestion(
                    id=qid,
                    skill=skill,
                    skill_category=category,
                    difficulty=difficulty,
                    question=item["question"],
                    options=[MCQOption(**o) for o in item["options"]],
                    time_limit_secs=_time_limit(difficulty),
                )
                all_questions.append(q)
                answer_key[qid] = item.get("correct", "A")

        session_id  = str(uuid.uuid4())
        total_secs  = sum(q.time_limit_secs for q in all_questions) + 60  # 60s buffer

        _sessions[session_id] = {
            "answer_key":  answer_key,
            "created_at":  time.time(),
            "questions":   {q.id: q.model_dump() for q in all_questions},
        }

        return SkillTestSession(
            session_id=session_id,
            questions=all_questions,
            total_questions=len(all_questions),
            time_limit_total_secs=total_secs,
            instructions=[
                "Do not switch browser tabs — this will be recorded",
                "Copy and paste are disabled during the test",
                "Each question has a per-question countdown timer",
                "You cannot go back to a previous question",
                "Submit even if unsure — unanswered counts as wrong",
            ],
        )

    # ── Score submission ──────────────────────────────────────────────────
    def score_submission(
        self,
        session_id: str,
        answers: List[QuestionAnswer],
        anti_cheat_events: List[AntiCheatEvent],
    ) -> SkillTestResult:
        session = _sessions.get(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found or already scored")

        answer_key: Dict[str, str]  = session["answer_key"]
        questions:  Dict[str, Any]  = session["questions"]

        # Build skill map
        skill_map: Dict[str, Dict[str, Any]] = {}
        for qid, qdata in questions.items():
            skill = qdata["skill"]
            cat   = qdata["skill_category"]
            if skill not in skill_map:
                skill_map[skill] = {"category": cat, "total": 0, "correct": 0}
            skill_map[skill]["total"] += 1

        # Score
        answer_lookup = {a.question_id: a.selected_option for a in answers}
        for qid, correct in answer_key.items():
            skill = questions.get(qid, {}).get("skill", "unknown")
            if skill in skill_map and answer_lookup.get(qid) == correct:
                skill_map[skill]["correct"] += 1

        # Per-skill scores
        skill_scores: List[SkillScore] = []
        for skill, data in skill_map.items():
            pct = round(data["correct"] / data["total"] * 100, 1) if data["total"] else 0.0
            if pct >= 80:
                verdict, color = "Verified",    "green"
            elif pct >= 50:
                verdict, color = "Partial",     "yellow"
            else:
                verdict, color = "Needs Work",  "red"

            skill_scores.append(SkillScore(
                skill=skill,
                skill_category=data["category"],
                questions_asked=data["total"],
                correct=data["correct"],
                score_pct=pct,
                verdict=verdict,
                verdict_color=color,
                recommended_resources=_resources(skill, pct),
            ))

        # Overall
        total_q   = sum(s.questions_asked for s in skill_scores)
        total_c   = sum(s.correct          for s in skill_scores)
        overall   = round(total_c / total_q * 100, 1) if total_q else 0.0

        overall_verdict = (
            "Ready for Role"        if overall >= 75 else
            "Almost There"          if overall >= 50 else
            "More Practice Needed"
        )

        # Integrity score
        tab_sw  = sum(1 for e in anti_cheat_events if e.event_type == "tab_switch")
        focus_l = sum(1 for e in anti_cheat_events if e.event_type == "focus_loss")
        copy_a  = sum(1 for e in anti_cheat_events if e.event_type == "copy_attempt")
        paste_a = sum(1 for e in anti_cheat_events if e.event_type == "paste_attempt")
        penalty = min(100, tab_sw * 10 + focus_l * 5 + copy_a * 8 + paste_a * 8)
        integrity_score = round(100 - penalty, 1)
        integrity_label = (
            "Clean"       if integrity_score >= 90 else
            "Suspicious"  if integrity_score >= 60 else
            "Compromised"
        )

        # Learning priorities = worst first
        needs_work         = sorted([s for s in skill_scores if s.verdict != "Verified"], key=lambda s: s.score_pct)
        learning_priorities = [s.skill for s in needs_work]
        next_steps          = _build_next_steps(overall, learning_priorities, skill_scores)

        # Delete session — answers can never be re-scored
        _sessions.pop(session_id, None)

        return SkillTestResult(
            session_id=session_id,
            overall_score_pct=overall,
            overall_verdict=overall_verdict,
            skill_scores=skill_scores,
            verified_count=sum(1 for s in skill_scores if s.verdict == "Verified"),
            partial_count=sum(1 for s in skill_scores if s.verdict == "Partial"),
            needs_work_count=sum(1 for s in skill_scores if s.verdict == "Needs Work"),
            integrity=TestIntegrityReport(
                tab_switches=tab_sw,
                focus_losses=focus_l,
                copy_attempts=copy_a,
                paste_attempts=paste_a,
                integrity_score=integrity_score,
                integrity_label=integrity_label,
            ),
            learning_priorities=learning_priorities,
            next_steps=next_steps,
        )


# ── Helpers ──────────────────────────────────────────────────────────────────
def _resources(skill: str, pct: float) -> List[str]:
    if pct >= 80:
        return []
    return [
        f"YouTube: '{skill} tutorial' — search freeCodeCamp channel",
        f"Docs: official {skill} documentation",
        f"Practice: build a small project using {skill}",
    ]


def _build_next_steps(
    overall: float,
    priorities: List[str],
    scores: List[SkillScore],
) -> List[str]:
    steps: List[str] = []
    if overall >= 75:
        steps.append("Great job! Your skill profile is strong — start applying to target roles.")
    else:
        if priorities:
            steps.append(f"Priority focus: {', '.join(priorities[:2])} — these are your biggest gaps.")
        steps.append("Retake this test after 2–3 weeks of deliberate practice to track progress.")
    if any(s.skill_category == "partial" and s.verdict == "Needs Work" for s in scores):
        steps.append("Turn partial skills into verified ones: push GitHub projects that use them.")
    steps.append("Only list skills on your resume that you scored 'Verified' in this test.")
    return steps

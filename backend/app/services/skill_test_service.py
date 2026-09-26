"""
Skill Verification Test Service.

Generates MCQ questions for claimed/partial/missing skills via the LLM,
keeps answers server-side, scores submissions, and produces a learning report.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

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

# In-memory store for sessions (replace with Redis/DB for production)
_sessions: Dict[str, Dict[str, Any]] = {}


def _difficulty_for_category(category: str) -> DifficultyLevel:
    if category == "claimed":
        return DifficultyLevel.MEDIUM
    if category == "partial":
        return DifficultyLevel.EASY
    return DifficultyLevel.EASY   # missing skills — start gentle


def _time_limit_for_difficulty(d: DifficultyLevel) -> int:
    return {DifficultyLevel.EASY: 45, DifficultyLevel.MEDIUM: 60, DifficultyLevel.HARD: 90}[d]


QUESTION_PROMPT = """
You are an expert technical interviewer. Generate {n} multiple-choice questions to test a student's knowledge of "{skill}" for a {role} role.

The student's relationship with this skill: {category_desc}
Difficulty level: {difficulty}

Return ONLY a valid JSON array. Each element must have:
{{
  "question": "...",
  "options": [{{"id": "A", "text": "..."}}, {{"id": "B", "text": "..."}}, {{"id": "C", "text": "..."}}, {{"id": "D", "text": "..."}}],
  "correct": "A" or "B" or "C" or "D",
  "explanation": "brief why correct"
}}

Rules:
- Questions must be practical and unambiguous
- Exactly one correct answer per question
- Distractors must be plausible
- No trick questions
- Do NOT include the answer in the question text
"""

CATEGORY_DESCRIPTIONS = {
    "claimed": "The student claims this skill on their resume but we want to verify depth.",
    "partial": "The student has some evidence of this skill but gaps remain.",
    "missing": "The student listed this as a target skill gap — test foundational knowledge.",
}


class SkillTestService:
    def __init__(self):
        self._gemini_client: Optional[genai.Client] = None
        gemini_key = os.environ.get("GEMINI_API_KEY", getattr(settings, "GEMINI_API_KEY", None))
        if gemini_key:
            self._gemini_client = genai.Client(api_key=gemini_key)

    async def _call_llm(self, prompt: str) -> List[Any]:
        """Call Gemini and extract a JSON array from the response."""
        if self._gemini_client:
            try:
                models = getattr(settings, "gemini_models_priority", ["gemini-1.5-flash"])
                for model_name in models:
                    try:
                        response = await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda m=model_name: self._gemini_client.models.generate_content(
                                model=m,
                                contents=prompt,
                            ),
                        )
                        raw = response.text or ""
                        start = raw.find("[")
                        end = raw.rfind("]") + 1
                        if start != -1 and end > 0:
                            return json.loads(raw[start:end])
                    except Exception as exc:
                        logger.warning("Gemini %s failed: %s", model_name, exc)
                        continue
            except Exception as exc:
                logger.warning("LLM call failed: %s", exc)
        raise ValueError("LLM unavailable — using fallback questions")

    async def generate_session(self, req: SkillTestRequest) -> SkillTestSession:
        """Generate a full test session with questions from LLM."""
        all_questions: List[TestQuestion] = []
        answer_key: Dict[str, str] = {}

        skill_buckets = [
            ("claimed", req.claimed_skills),
            ("partial", req.partial_skills),
            ("missing", req.missing_skills[:3]),  # cap missing to 3 skills max
        ]

        for category, skills in skill_buckets:
            for skill in skills[:4]:  # cap per bucket to keep test manageable
                difficulty = _difficulty_for_category(category)
                prompt = QUESTION_PROMPT.format(
                    n=req.num_questions_per_skill,
                    skill=skill,
                    role=req.target_role,
                    category_desc=CATEGORY_DESCRIPTIONS[category],
                    difficulty=difficulty.value,
                )
                try:
                    items = await self._call_llm(prompt)
                    for item in items:
                        qid = str(uuid.uuid4())[:8]
                        q = TestQuestion(
                            id=qid,
                            skill=skill,
                            skill_category=category,
                            difficulty=difficulty,
                            question=item["question"],
                            options=[MCQOption(**o) for o in item["options"]],
                            time_limit_secs=_time_limit_for_difficulty(difficulty),
                        )
                        all_questions.append(q)
                        answer_key[qid] = item["correct"]
                except Exception as exc:
                    logger.warning("LLM question generation failed for %s: %s", skill, exc)
                    # Fallback: generic placeholder question
                    qid = str(uuid.uuid4())[:8]
                    q = TestQuestion(
                        id=qid,
                        skill=skill,
                        skill_category=category,
                        difficulty=difficulty,
                        question=f"Which of the following best describes a core concept of {skill}?",
                        options=[
                            MCQOption(id="A", text="It is a runtime environment"),
                            MCQOption(id="B", text="It is a design pattern for decoupling"),
                            MCQOption(id="C", text="It is a data serialization format"),
                            MCQOption(id="D", text="It is a version control system"),
                        ],
                        time_limit_secs=60,
                    )
                    all_questions.append(q)
                    answer_key[qid] = "A"  # placeholder

        session_id = str(uuid.uuid4())
        total_time = sum(q.time_limit_secs for q in all_questions) + 30  # 30s buffer

        # Store answer key server-side
        _sessions[session_id] = {
            "answer_key": answer_key,
            "created_at": time.time(),
            "questions": {q.id: q.model_dump() for q in all_questions},
        }

        return SkillTestSession(
            session_id=session_id,
            questions=all_questions,
            total_questions=len(all_questions),
            time_limit_total_secs=total_time,
            instructions=[
                "Do not switch browser tabs — this will be recorded",
                "Copy and paste are disabled during the test",
                "Each question has a time limit shown on screen",
                "You cannot go back to a previous question",
                "Submit even if unsure — unanswered = wrong",
            ],
        )

    def score_submission(
        self,
        session_id: str,
        answers: List[QuestionAnswer],
        anti_cheat_events: List[AntiCheatEvent],
    ) -> SkillTestResult:
        """Score submitted answers against the server-side answer key."""
        session = _sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found or expired")

        answer_key: Dict[str, str] = session["answer_key"]
        questions: Dict[str, Any] = session["questions"]

        # Group questions by skill
        skill_map: Dict[str, Dict[str, Any]] = {}
        for qid, qdata in questions.items():
            skill = qdata["skill"]
            cat = qdata["skill_category"]
            if skill not in skill_map:
                skill_map[skill] = {"category": cat, "total": 0, "correct": 0}
            skill_map[skill]["total"] += 1

        # Score answers
        answer_lookup = {a.question_id: a.selected_option for a in answers}
        for qid, correct in answer_key.items():
            qdata = questions.get(qid, {})
            skill = qdata.get("skill", "unknown")
            if skill not in skill_map:
                continue
            if answer_lookup.get(qid) == correct:
                skill_map[skill]["correct"] += 1

        # Build per-skill scores
        skill_scores: List[SkillScore] = []
        for skill, data in skill_map.items():
            pct = (data["correct"] / data["total"] * 100) if data["total"] > 0 else 0.0
            if pct >= 80:
                verdict, color = "Verified", "green"
            elif pct >= 50:
                verdict, color = "Partial", "yellow"
            else:
                verdict, color = "Needs Work", "red"

            skill_scores.append(SkillScore(
                skill=skill,
                skill_category=data["category"],
                questions_asked=data["total"],
                correct=data["correct"],
                score_pct=round(pct, 1),
                verdict=verdict,
                verdict_color=color,
                recommended_resources=_default_resources(skill, pct),
            ))

        # Overall score
        total_q = sum(s.questions_asked for s in skill_scores)
        total_c = sum(s.correct for s in skill_scores)
        overall_pct = round((total_c / total_q * 100) if total_q > 0 else 0.0, 1)

        if overall_pct >= 75:
            overall_verdict = "Ready for Role"
        elif overall_pct >= 50:
            overall_verdict = "Almost There"
        else:
            overall_verdict = "More Practice Needed"

        # Integrity
        tab_sw = sum(1 for e in anti_cheat_events if e.event_type == "tab_switch")
        focus_l = sum(1 for e in anti_cheat_events if e.event_type == "focus_loss")
        copy_a = sum(1 for e in anti_cheat_events if e.event_type == "copy_attempt")
        paste_a = sum(1 for e in anti_cheat_events if e.event_type == "paste_attempt")
        penalty = min(100, tab_sw * 10 + focus_l * 5 + copy_a * 8 + paste_a * 8)
        integrity_score = round(100 - penalty, 1)
        if integrity_score >= 90:
            integrity_label = "Clean"
        elif integrity_score >= 60:
            integrity_label = "Suspicious"
        else:
            integrity_label = "Compromised"

        # Learning priorities = weakest skills first
        needs_work = sorted(
            [s for s in skill_scores if s.verdict != "Verified"],
            key=lambda s: s.score_pct
        )
        learning_priorities = [s.skill for s in needs_work]

        next_steps = _build_next_steps(overall_pct, learning_priorities, skill_scores)

        # Cleanup session
        _sessions.pop(session_id, None)

        return SkillTestResult(
            session_id=session_id,
            overall_score_pct=overall_pct,
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


def _default_resources(skill: str, score_pct: float) -> List[str]:
    if score_pct >= 80:
        return []
    return [
        f"Search: '{skill} tutorial for beginners' on YouTube",
        f"Practice: Build a small project using {skill}",
        f"Read: Official {skill} documentation",
    ]


def _build_next_steps(
    overall_pct: float,
    priorities: List[str],
    skill_scores: List[SkillScore],
) -> List[str]:
    steps = []
    if overall_pct >= 75:
        steps.append("Great job! Apply to target roles — your skill profile is strong.")
    else:
        if priorities:
            top = priorities[:2]
            steps.append(f"Focus on: {', '.join(top)} — these are your biggest gaps.")
        steps.append("Re-take this test after 2-3 weeks of practice to track progress.")
    if any(s.skill_category == "partial" and s.verdict == "Needs Work" for s in skill_scores):
        steps.append("Convert partial skills to verified: add GitHub projects that use them.")
    steps.append("Update your resume only with skills you scored 'Verified' on.")
    return steps

"""
Schemas for Skill Verification Test feature.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import Field

from app.schemas.common import AppBaseModel


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class SkillTestRequest(AppBaseModel):
    """Input: what we know about the student from the analysis pipeline."""
    claimed_skills: List[str] = Field(default_factory=list, description="Skills the student claims to know")
    missing_skills: List[str] = Field(default_factory=list, description="Skills identified as missing")
    partial_skills: List[str] = Field(default_factory=list, description="Skills with partial evidence")
    target_role: str = Field(..., min_length=1, max_length=200)
    num_questions_per_skill: int = Field(default=3, ge=1, le=5)


class MCQOption(AppBaseModel):
    id: str          # "A" | "B" | "C" | "D"
    text: str


class TestQuestion(AppBaseModel):
    id: str
    skill: str
    skill_category: str   # "claimed" | "partial" | "missing"
    difficulty: DifficultyLevel
    question: str
    options: List[MCQOption]
    # correct_answer is NOT exposed to the frontend — kept server-side only
    time_limit_secs: int = Field(default=60)


class SkillTestSession(AppBaseModel):
    session_id: str
    questions: List[TestQuestion]
    total_questions: int
    time_limit_total_secs: int
    instructions: List[str]


class QuestionAnswer(AppBaseModel):
    question_id: str
    selected_option: str      # "A" | "B" | "C" | "D"
    time_taken_secs: int


class AntiCheatEvent(AppBaseModel):
    event_type: str           # "tab_switch" | "focus_loss" | "copy_attempt" | "paste_attempt"
    timestamp_ms: int
    question_id: Optional[str] = None


class SkillTestSubmission(AppBaseModel):
    session_id: str
    answers: List[QuestionAnswer]
    anti_cheat_events: List[AntiCheatEvent] = Field(default_factory=list)
    total_time_secs: int


class SkillScore(AppBaseModel):
    skill: str
    skill_category: str
    questions_asked: int
    correct: int
    score_pct: float          # 0-100
    verdict: str              # "Verified" | "Partial" | "Needs Work" | "Not Ready"
    verdict_color: str        # "green" | "yellow" | "red"
    recommended_resources: List[str] = Field(default_factory=list)


class TestIntegrityReport(AppBaseModel):
    tab_switches: int
    focus_losses: int
    copy_attempts: int
    paste_attempts: int
    integrity_score: float    # 0-100 (100 = perfectly clean)
    integrity_label: str      # "Clean" | "Suspicious" | "Compromised"


class SkillTestResult(AppBaseModel):
    session_id: str
    overall_score_pct: float
    overall_verdict: str      # "Ready for Role" | "Almost There" | "More Practice Needed"
    skill_scores: List[SkillScore]
    verified_count: int
    partial_count: int
    needs_work_count: int
    integrity: TestIntegrityReport
    learning_priorities: List[str]   # ordered list of skills to focus on next
    next_steps: List[str]

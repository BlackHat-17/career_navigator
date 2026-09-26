"""
ResumeJudgeClient
─────────────────
Forwards resume + job-description data to the Resume Judge service.

Expected service contract
─────────────────────────
POST /analyze

Input:
    {
        "target_role":    "Backend Developer",
        "resume_text":    "<extracted plain text>",
        "job_description": "<raw JD text>",   # optional
        "github_skills":  [...]                # optional, from GitHub Agent
    }

Output:
    {
        "claimed_skills": [
            {
                "name": "FastAPI",
                "context": "Built production REST APIs with FastAPI",
                "confidence": 0.91
            }
        ],
        "feedback": [
            {
                "section": "experience",
                "comment": "Quantify impact where possible.",
                "severity": "warning"
            }
        ],
        "overall_score": 74.5,
        "verified_skills":   [...],
        "partial_skills":    [...],
        "missing_skills":    [...],
        "unsupported_claims": [...]
    }

POST /skill-analysis   (used by the skill-analysis endpoint)

Input:
    {
        "github_output":  { ... },   # raw GitHub Agent output
        "resume_output":  { ... },   # raw Resume Judge /analyze output
        "job_title":      "Backend Developer",
        "job_description": "..."
    }

Output:
    {
        "verified_skills":    [...],
        "partial_skills":     [...],
        "missing_skills":     [...],
        "unsupported_claims": [...]
    }
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.clients.base import BaseServiceClient
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class ResumeJudgeClient(BaseServiceClient):
    service_name = "Resume Judge"
    base_url = settings.RESUME_JUDGE_URL

    async def analyze_resume(
        self,
        target_role: str,
        resume_text: str,
        job_description: Optional[str] = None,
        github_skills: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Send resume text + metadata to the Resume Judge.
        Returns raw judging output (claimed_skills, feedback, score, etc.).
        """
        payload: Dict[str, Any] = {
            "target_role": target_role,
            "resume_text": resume_text,
        }
        if job_description:
            payload["job_description"] = job_description
        if github_skills:
            payload["github_skills"] = github_skills

        logger.info("Sending resume analysis request for role=%s", target_role)
        return await self._post("/analyze", payload)

    async def analyze_skills(
        self,
        github_output: Dict[str, Any],
        resume_output: Dict[str, Any],
        job_title: str,
        job_description: str,
    ) -> Dict[str, Any]:
        """
        Cross-reference GitHub evidence, resume claims, and JD requirements
        to produce a categorised skill breakdown.
        """
        payload: Dict[str, Any] = {
            "github_output": github_output,
            "resume_output": resume_output,
            "job_title": job_title,
            "job_description": job_description,
        }
        logger.info("Sending skill analysis request for job_title=%s", job_title)
        return await self._post("/skill-analysis", payload)

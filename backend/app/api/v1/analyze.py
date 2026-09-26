"""
POST /api/analyze          – start a skill-gap analysis job, returns { jobId }
GET  /api/analyze/{jobId}/stream  – SSE live progress stream
GET  /api/analyze/{jobId}/status  – polling fallback

Pipeline:
  Step 1 – Extract resume text (PDF or raw text)
  Step 2 – Fetch GitHub repos (optional)
  Step 3 – Gemini 1.5 Flash skill-gap analysis (falls back to mock on error)

All heavy work runs in a background asyncio task so the POST returns instantly
and the client streams progress via SSE.
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import re
import uuid
from typing import Any, Dict

import httpx
from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from google import genai

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.llm_fallback_service import LLMFallbackService

router = APIRouter(tags=["Analyze"])
logger = get_logger(__name__)
settings = get_settings()

# ── In-process job store ──────────────────────────────────────────────────────
# { job_id: { status, progress: [...], result, error, queues: [asyncio.Queue] } }
_JOBS: Dict[str, Dict[str, Any]] = {}


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/analyze
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/api/analyze", summary="Start skill-gap analysis")
async def start_analysis(
    resume: UploadFile = File(...),
    role: str = Form(...),
    githubUsername: str = Form(default=""),
    githubAccessToken: str = Form(default=""),
) -> JSONResponse:
    job_id = str(uuid.uuid4())
    _JOBS[job_id] = {
        "status": "queued",
        "progress": [],
        "result": None,
        "error": None,
        "queues": [],
    }

    file_bytes = await resume.read()

    asyncio.create_task(
        _run_pipeline(
            job_id=job_id,
            file_bytes=file_bytes,
            github_username=githubUsername.strip(),
            github_access_token=githubAccessToken.strip(),
            role=role.strip(),
        )
    )

    return JSONResponse({"jobId": job_id})


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/analyze/{jobId}/stream  (SSE)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/api/analyze/{job_id}/stream", summary="SSE progress stream")
async def stream_analysis(job_id: str, request: Request) -> StreamingResponse:
    job = _JOBS.get(job_id)
    if not job:
        async def missing_job_event_generator():
            yield f"data: {json.dumps({'type': 'error', 'message': 'job not found'})}\n\n"

        return StreamingResponse(
            missing_job_event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    queue: asyncio.Queue = asyncio.Queue()
    job["queues"].append(queue)

    async def event_generator():
        # Replay already-emitted events
        for event in job["progress"]:
            yield f"data: {json.dumps(event)}\n\n"

        if job["status"] == "done":
            yield f"data: {json.dumps({'type': 'done', 'result': job['result']})}\n\n"
            job["queues"].remove(queue)
            return
        if job["status"] == "error":
            yield f"data: {json.dumps({'type': 'error', 'message': job['error']})}\n\n"
            job["queues"].remove(queue)
            return

        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") in ("done", "error"):
                    break
        finally:
            if queue in job["queues"]:
                job["queues"].remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/analyze/{jobId}/status  (polling fallback)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/api/analyze/{job_id}/status", summary="Poll job status")
async def get_status(job_id: str) -> JSONResponse:
    job = _JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "job not found"}, status_code=404)
    return JSONResponse({
        "status": job["status"],
        "progress": job["progress"],
        "result": job["result"],
        "error": job["error"],
    })


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _emit(job: Dict[str, Any], payload: Dict[str, Any]) -> None:
    """Record event and broadcast to all connected SSE queues."""
    job["progress"].append(payload)
    for q in job["queues"]:
        q.put_nowait(payload)


def _mock_result(role: str) -> Dict[str, Any]:
    """Realistic demo result — returned when MOCK_MODE=true or no API key is set."""
    return {
        "summary": (
            f"Strong candidate for {role} with solid frontend fundamentals and active GitHub "
            "presence. Key gaps are in system design, testing discipline, and cloud infrastructure "
            "— addressable within 3–6 months."
        ),
        "claimed": [
            {"skill": "React",       "evidence": "Listed prominently in resume under Skills section."},
            {"skill": "TypeScript",  "evidence": "Mentioned in 3 project descriptions on resume."},
            {"skill": "REST APIs",   "evidence": "Resume states experience designing RESTful services."},
            {"skill": "Agile/Scrum", "evidence": "Resume mentions sprint-based delivery at previous employer."},
            {"skill": "SQL",         "evidence": "Listed as a proficiency; no public DB projects found."},
        ],
        "evidenced": [
            {"skill": "JavaScript (ES2022+)", "evidence": "Primary language across 8 of 12 public GitHub repos."},
            {"skill": "Node.js / Express",    "evidence": "skillgap-analyzer and 2 other repos use Express for API layers."},
            {"skill": "Vite + React",         "evidence": "Multiple repos scaffold with Vite; component patterns look production-grade."},
            {"skill": "Git / GitHub Actions", "evidence": "CI workflows present in 4 repos; consistent commit discipline."},
            {"skill": "Tailwind CSS",         "evidence": "Used in frontend repos; custom config and design tokens present."},
        ],
        "missing": [
            {"skill": "System Design",            "why": f"{role} roles at senior level require designing distributed systems — no evidence in resume or GitHub."},
            {"skill": "Docker / Kubernetes",      "why": "No containerisation found in any public repo; expected for backend-touching roles."},
            {"skill": "Testing (Jest / Vitest)",  "why": "No test files found across 12 GitHub repos — a significant red flag for production roles."},
            {"skill": "AWS / GCP",                "why": "Cloud deployment experience absent; most companies expect at least S3/EC2 familiarity."},
            {"skill": "Performance optimisation", "why": "No evidence of profiling, lazy-loading strategies, or Core Web Vitals work."},
        ],
        "roadmap": [
            {"title": "Add tests to an existing project",        "description": "Pick your most-starred repo and add Jest or Vitest coverage to at least 3 core functions.", "priority": "high"},
            {"title": "Containerise a side project with Docker", "description": "Write a Dockerfile + docker-compose for one of your Node apps. Deploy to a $5 VPS.",          "priority": "high"},
            {"title": "Build a system design case study",        "description": f"Design a URL shortener or chat app on paper, write it up as a README. Relevant to {role} interviews.", "priority": "medium"},
            {"title": "Get AWS Certified (Cloud Practitioner)",  "description": "The CLF-C02 exam takes ~4 weeks of evenings. Cheapest signal of cloud literacy.",             "priority": "medium"},
            {"title": "Optimise a page for Core Web Vitals",     "description": "Run Lighthouse, fix the top 3 issues, document before/after. Concrete portfolio evidence.",   "priority": "low"},
        ],
    }


async def _extract_text(file_bytes: bytes) -> str:
    """Extract plain text from PDF bytes, falling back to raw UTF-8."""
    try:
        import PyPDF2  # type: ignore
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        pass
    return file_bytes.decode("utf-8", errors="replace")


class GitHubUserNotFoundError(Exception):
    """Raised when the GitHub username does not exist."""


async def _fetch_github(username: str, access_token: str = "") -> str:
    """Return a plain-text summary of the user's GitHub repos.

    Priority for the Authorization header:
      1. access_token — the user's own OAuth token from Supabase (best: can
         read private repos if scope allows, always avoids rate limits)
      2. GITHUB_TOKEN env var — server-side token (read public repos, 5 000/h)
      3. No auth — unauthenticated, 60 req/h, public repos only

    Raises:
        GitHubUserNotFoundError: if the username returns HTTP 404.
    """
    headers: dict = {"User-Agent": "career-navigator"}

    token = access_token or os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.github.com/users/{username}/repos",
                params={"sort": "updated", "per_page": "20"},
                headers=headers,
            )

        if resp.status_code == 404:
            raise GitHubUserNotFoundError(
                f"GitHub username '{username}' does not exist. "
                "Please check the username and try again."
            )

        if resp.status_code == 403:
            logger.warning("GitHub API rate limited for user %s", username)
            return ""

        if resp.is_success:
            repos = resp.json()
            if not repos:
                return ""
            return "\n".join(
                f"{r['name']} ({r.get('language') or 'unknown'}): {r.get('description') or ''}"
                for r in repos
            )

    except GitHubUserNotFoundError:
        raise
    except Exception as exc:
        logger.warning("GitHub fetch failed for user %s: %s", username, exc)

    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────

async def _run_pipeline(
    job_id: str,
    file_bytes: bytes,
    github_username: str,
    github_access_token: str,
    role: str,
) -> None:
    job = _JOBS[job_id]
    job["status"] = "running"

    try:
        # ── Step 1: Extract resume text ───────────────────────────────────
        _emit(job, {"type": "step", "step": 1, "message": "Extracting resume text…"})
        resume_text = await _extract_text(file_bytes)
        _emit(job, {"type": "step", "step": 1,
                    "message": f"Resume extracted ({len(resume_text)} chars)"})

        # ── Step 2: GitHub repos ──────────────────────────────────────────
        github_summary = ""
        if github_username:
            _emit(job, {"type": "step", "step": 2,
                        "message": f"Fetching GitHub repos for @{github_username}…"})
            try:
                github_summary = await _fetch_github(
                    github_username, access_token=github_access_token
                )
            except GitHubUserNotFoundError as exc:
                raise exc

            if github_summary:
                count = github_summary.count("\n") + 1
                _emit(job, {"type": "step", "step": 2, "message": f"Found {count} repos"})
            else:
                _emit(job, {"type": "step", "step": 2,
                            "message": f"@{github_username} has no public repos — continuing without GitHub data"})

        # ── Step 3: Gemini analysis ───────────────────────────────────────
        _emit(job, {"type": "step", "step": 3, "message": "Running AI skill gap analysis…"})

        if os.environ.get("MOCK_MODE") == "true":
            _emit(job, {"type": "step", "step": 3,
                        "message": "Mock mode — returning demo results"})
            await asyncio.sleep(1.2)
            result = _mock_result(role)
        else:
            # Use new multi-provider fallback service
            llm_service = LLMFallbackService()
            result = await llm_service.analyze_with_fallback(
                resume_text=resume_text,
                github_summary=github_summary,
                role=role,
                progress_callback=lambda msg, step: _emit(job, {"type": "step", "step": step, "message": msg})
            )

        _emit(job, {"type": "step", "step": 3, "message": "Analysis complete ✓"})
        job["result"] = result
        job["status"] = "done"
        _emit(job, {"type": "done", "result": result})

    except GitHubUserNotFoundError as exc:
        # User-facing error — no stack trace needed
        logger.warning("Invalid GitHub username for job %s: %s", job_id, exc)
        job["status"] = "error"
        job["error"] = str(exc)
        _emit(job, {"type": "error", "message": str(exc)})

    except Exception as exc:
        logger.exception("Pipeline failed for job %s", job_id)
        job["status"] = "error"
        job["error"] = str(exc)
        _emit(job, {"type": "error", "message": str(exc)})

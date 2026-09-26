"""
LLM Fallback Service
────────────────────
Unified service for calling multiple LLM providers with intelligent fallback:
  1. Gemini (3.7 → 3.5 → 3.8)
  2. Grok (xAI)
  3. NVIDIA (via API Catalog)
  4. Ollama (local)
  5. Mock/Demo results

Each provider is tried in order until one succeeds or all fail.
"""
import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx
import google.genai as genai

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMFallbackService:
    """
    Handles LLM calls with multi-provider fallback support.
    """

    def __init__(self):
        self.gemini_client = None
        self._init_gemini()

    def _init_gemini(self):
        """Initialize Gemini client if API key is available."""
        gemini_key = os.environ.get("GEMINI_API_KEY", settings.GEMINI_API_KEY)
        if gemini_key:
            self.gemini_client = genai.Client(api_key=gemini_key)

    async def analyze_with_fallback(
        self,
        resume_text: str,
        github_summary: str,
        role: str,
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Analyze resume with automatic provider fallback.
        
        Args:
            resume_text: Extracted resume text
            github_summary: GitHub activity summary
            role: Target job role
            progress_callback: Optional function to call with progress updates
                              Signature: progress_callback(message: str, step: int)
        
        Returns:
            Analysis result dict with keys: claimed, evidenced, missing, roadmap, summary
        """
        prompt = self._build_prompt(resume_text, github_summary, role)

        # Try Gemini models first
        if self.gemini_client and settings.GEMINI_API_KEY:
            result = await self._try_gemini_models(prompt, progress_callback)
            if result:
                return result

        # Try Grok (xAI) if enabled
        if settings.GROK_ENABLED and settings.GROK_API_KEY:
            result = await self._try_grok(prompt, progress_callback)
            if result:
                return result

        # Try NVIDIA if enabled
        if settings.NVIDIA_ENABLED and settings.NVIDIA_API_KEY:
            result = await self._try_nvidia(prompt, progress_callback)
            if result:
                return result

        # Try local Ollama if enabled
        if settings.OLLAMA_ENABLED:
            result = await self._try_ollama(prompt, progress_callback)
            if result:
                return result

        # Final fallback: demo data
        if progress_callback:
            progress_callback("All providers failed — using demo results", 3)
        logger.warning("All LLM providers failed, returning mock data")
        return self._mock_result(role)

    async def _try_gemini_models(
        self, prompt: str, progress_callback: Optional[callable]
    ) -> Optional[Dict[str, Any]]:
        """Try Gemini models in priority order."""
        models = settings.gemini_models_priority

        for idx, model_name in enumerate(models):
            try:
                if idx > 0 and progress_callback:
                    progress_callback(f"Trying Gemini fallback: {model_name}", 3)
                    await asyncio.sleep(0.3)

                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda m=model_name: self.gemini_client.models.generate_content(
                        model=m,
                        contents=prompt,
                        config=genai.types.GenerateContentConfig(
                            temperature=0.3,
                            response_mime_type="application/json",
                        ),
                    ),
                )

                raw_text = self._clean_response(response.text or "")
                return json.loads(raw_text)

            except json.JSONDecodeError as exc:
                logger.warning(f"Gemini {model_name} returned invalid JSON: {exc}")
                if idx == len(models) - 1:  # Last Gemini model
                    return None
                continue

            except Exception as exc:
                msg = str(exc).lower()
                is_retryable = any(
                    x in msg for x in ["503", "unavailable", "high demand", "overloaded"]
                )

                if idx < len(models) - 1 and is_retryable:
                    logger.warning(f"Gemini {model_name} failed: {exc}. Trying next...")
                    continue

                logger.warning(f"Gemini {model_name} failed: {exc}")
                return None

        return None

    async def _try_grok(
        self, prompt: str, progress_callback: Optional[callable]
    ) -> Optional[Dict[str, Any]]:
        """Try Grok (xAI) API."""
        try:
            if progress_callback:
                progress_callback(f"Trying Grok ({settings.GROK_MODEL})...", 3)

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.GROK_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.GROK_MODEL,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert technical recruiter. Return ONLY valid JSON, no markdown.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                        "response_format": {"type": "json_object"},
                    },
                )

                if response.status_code != 200:
                    logger.warning(f"Grok API returned {response.status_code}: {response.text}")
                    return None

                data = response.json()
                raw_text = data["choices"][0]["message"]["content"]
                raw_text = self._clean_response(raw_text)
                return json.loads(raw_text)

        except json.JSONDecodeError as exc:
            logger.warning(f"Grok returned invalid JSON: {exc}")
            return None

        except Exception as exc:
            logger.warning(f"Grok API call failed: {exc}")
            return None

    async def _try_nvidia(
        self, prompt: str, progress_callback: Optional[callable]
    ) -> Optional[Dict[str, Any]]:
        """Try NVIDIA API Catalog."""
        try:
            if progress_callback:
                progress_callback(f"Trying NVIDIA ({settings.NVIDIA_MODEL})...", 3)

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"https://integrate.api.nvidia.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.NVIDIA_MODEL,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert technical recruiter. Return ONLY valid JSON, no markdown.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 2048,
                    },
                )

                if response.status_code != 200:
                    logger.warning(f"NVIDIA API returned {response.status_code}: {response.text}")
                    return None

                data = response.json()
                raw_text = data["choices"][0]["message"]["content"]
                raw_text = self._clean_response(raw_text)
                return json.loads(raw_text)

        except json.JSONDecodeError as exc:
            logger.warning(f"NVIDIA returned invalid JSON: {exc}")
            return None

        except Exception as exc:
            logger.warning(f"NVIDIA API call failed: {exc}")
            return None

    async def _try_ollama(
        self, prompt: str, progress_callback: Optional[callable]
    ) -> Optional[Dict[str, Any]]:
        """Try local Ollama model."""
        try:
            if progress_callback:
                progress_callback(f"Using local {settings.OLLAMA_MODEL}...", 3)

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": settings.OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0.3, "num_predict": 2000},
                    },
                )

                if response.status_code != 200:
                    logger.warning(f"Ollama returned {response.status_code}")
                    return None

                result = response.json()
                raw_text = self._clean_response(result.get("response", ""))
                return json.loads(raw_text)

        except json.JSONDecodeError as exc:
            logger.warning(f"Ollama returned invalid JSON: {exc}")
            return None

        except Exception as exc:
            logger.warning(f"Ollama call failed: {exc}")
            return None

    def _build_prompt(self, resume_text: str, github_summary: str, role: str) -> str:
        """Build the analysis prompt."""
        return (
            "You are an expert technical recruiter and skills analyst.\n"
            "Analyse the candidate's resume and GitHub activity against the target role.\n"
            "Return ONLY a valid JSON object with this exact shape "
            "(no markdown, no code fences, no preamble):\n"
            '{\n'
            '  "claimed":   [{ "skill": "string", "evidence": "string" }],\n'
            '  "evidenced": [{ "skill": "string", "evidence": "string" }],\n'
            '  "missing":   [{ "skill": "string", "why": "string" }],\n'
            '  "roadmap":   [{ "title": "string", "description": "string",'
            ' "priority": "high|medium|low" }],\n'
            '  "summary":   "string"\n'
            "}\n\n"
            "Definitions:\n"
            "- claimed:   skills stated in the resume but NOT backed by GitHub projects\n"
            "- evidenced: skills demonstrated in actual GitHub repos\n"
            "- missing:   important skills for the role absent from both\n"
            "- roadmap:   3-5 concrete learning/project steps to close the gaps\n"
            "- summary:   2-sentence overall assessment\n\n"
            f"Target role: {role}\n\n"
            f"--- RESUME ---\n{resume_text[:6000]}\n\n"
            f"--- GITHUB REPOS ---\n{github_summary or '(not provided)'}"
        )

    def _clean_response(self, text: str) -> str:
        """Remove markdown fences and clean response text."""
        text = text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return text

    def _mock_result(self, role: str) -> Dict[str, Any]:
        """Return realistic demo data when all providers fail."""
        return {
            "claimed": [
                {
                    "skill": "Python",
                    "evidence": "Listed in resume under 'Programming Languages' but no corresponding GitHub repos found",
                },
                {
                    "skill": "React",
                    "evidence": "Mentioned in project descriptions but GitHub shows mostly backend work",
                },
            ],
            "evidenced": [
                {
                    "skill": "FastAPI",
                    "evidence": "3 repositories with FastAPI implementations, including REST APIs and async patterns",
                },
                {
                    "skill": "Docker",
                    "evidence": "Dockerfiles present in 5 repos with multi-stage builds",
                },
            ],
            "missing": [
                {
                    "skill": "Kubernetes",
                    "why": f"Essential for {role} but absent from resume and GitHub activity",
                },
                {
                    "skill": "CI/CD",
                    "why": "No GitHub Actions, Jenkins, or similar workflows visible",
                },
            ],
            "roadmap": [
                {
                    "title": "Build a microservices project with K8s",
                    "description": "Deploy 3-4 containerized services on Kubernetes with Helm charts",
                    "priority": "high",
                },
                {
                    "title": "Set up CI/CD pipeline",
                    "description": "Create GitHub Actions workflows for testing, building, and deployment",
                    "priority": "high",
                },
                {
                    "title": "Contribute to open source",
                    "description": "Make meaningful PRs to popular projects in your tech stack",
                    "priority": "medium",
                },
            ],
            "summary": f"Strong backend fundamentals with Python and FastAPI, but {role} requires more DevOps experience. "
            "Focus on containerization orchestration and automated deployment pipelines to bridge the gap.",
        }

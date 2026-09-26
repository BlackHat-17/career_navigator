"""
OrchestrationService
────────────────────
The main pipeline. Coordinates all four AI modules in sequence:

  GitHub Agent → Resume Judge → Skill Analysis
      → Project Recommender → Roadmap Generator → Unified Result

The service does NOT implement any AI logic. It only:
  - creates and updates the Analysis lifecycle record
  - calls each client in order
  - extracts the minimal data needed to pass between steps
  - persists every raw service output
  - assembles the final unified response
  
When MOCK_MODE=true, returns synthetic data without calling external services.
"""
from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.clients.github_agent_client import GitHubAgentClient
from app.clients.project_recommender_client import ProjectRecommenderClient
from app.clients.resume_judge_client import ResumeJudgeClient
from app.clients.roadmap_generator_client import RoadmapGeneratorClient
from app.services.agentic_analyzer import AgenticAnalyzer
from app.core.config import get_settings
from app.core.exceptions import (
    NotFoundError,
    ServiceResponseError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)
from app.core.logging import get_logger
from app.models.analysis import Analysis, AnalysisStatus
from app.models.evidence import Evidence
from app.models.project import Project, RecommendedProject
from app.models.roadmap import Roadmap, RoadmapStep
from app.models.skill import CandidateSkill, Skill, SkillLevel
from app.models.user import User
from app.schemas.analysis import (
    AnalysisSummary,
    CandidateInfo,
    FullAnalysisRead,
    ProjectsSummary,
    SkillDetail,
    SkillsSummary,
)
from app.services.resume_service import ResumeService

logger = get_logger(__name__)
settings = get_settings()


class OrchestrationService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ─────────────────────────────────────────────────────────────────────
    # Public: run full pipeline
    # ─────────────────────────────────────────────────────────────────────

    async def run(
        self,
        user_id: UUID,
        target_role: str,
        resume_file: UploadFile,
        github_username: str | None = None,
        job_description: str | None = None,
    ) -> FullAnalysisRead:
        # 1. Validate user
        user = await self._db.get(User, user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found.")

        # 2. Create master analysis record
        analysis = Analysis(
            user_id=user_id,
            github_username=github_username or "unknown",
            target_role=target_role,
            job_description=job_description or "",
            status=AnalysisStatus.PROCESSING,
        )
        self._db.add(analysis)
        await self._db.flush()
        logger.info("Orchestration started analysis_id=%s", analysis.id)

        try:
            result = await self._execute_pipeline(
                analysis=analysis,
                target_role=target_role,
                resume_file=resume_file,
                github_username=github_username,
                job_description=job_description,
            )
        except Exception as exc:
            analysis.status = AnalysisStatus.FAILED
            analysis.error_message = str(exc)
            await self._db.flush()
            logger.error("Orchestration failed analysis_id=%s error=%s", analysis.id, exc)
            raise

        return result

    # ─────────────────────────────────────────────────────────────────────
    # Public: retrieve a stored result
    # ─────────────────────────────────────────────────────────────────────

    async def get_analysis(self, analysis_id: UUID) -> FullAnalysisRead:
        result = await self._db.execute(
            select(Analysis)
            .where(Analysis.id == analysis_id)
            .options(
                selectinload(Analysis.candidate_skills).selectinload(CandidateSkill.skill),
                selectinload(Analysis.evidence_items),
                selectinload(Analysis.projects),
                selectinload(Analysis.recommended_projects),
                selectinload(Analysis.roadmap).selectinload(Roadmap.steps),
            )
        )
        analysis = result.scalar_one_or_none()
        if not analysis:
            raise NotFoundError(f"Analysis {analysis_id} not found.")

        return self._build_response(analysis)

    # ─────────────────────────────────────────────────────────────────────
    # Private: pipeline execution
    # ─────────────────────────────────────────────────────────────────────

    async def _execute_pipeline(
        self,
        analysis: Analysis,
        target_role: str,
        resume_file: UploadFile,
        github_username: str | None = None,
        job_description: str | None = None,
    ) -> FullAnalysisRead:

        # ── Step 1: GitHub Agent (skip if no username) ────────────────────
        github_raw: Dict[str, Any] = {}
        if github_username:
            logger.info("[pipeline] step=1 GitHub Agent analysis_id=%s", analysis.id)
            if settings.MOCK_MODE:
                logger.info("[pipeline] MOCK_MODE: using synthetic GitHub data")
                github_raw = self._mock_github_data(github_username)
                analysis.github_agent_output = github_raw
            else:
                github_raw = await self._run_github_agent(analysis, github_username)
        else:
            logger.info("[pipeline] step=1 GitHub Agent SKIPPED (no username)")

        # ── Step 2: Resume Judge ──────────────────────────────────────────
        logger.info("[pipeline] step=2 Resume Judge analysis_id=%s", analysis.id)
        resume_text = await self._extract_resume_text(analysis, resume_file)
        
        if settings.MOCK_MODE:
            logger.info("[pipeline] MOCK_MODE: using synthetic resume data")
            resume_raw = self._mock_resume_data(target_role)
            analysis.resume_judge_output = resume_raw
        else:
            resume_raw = await self._run_resume_judge(
                analysis=analysis,
                target_role=target_role,
                resume_text=resume_text,
                job_description=job_description or "",
                github_skills=github_raw.get("skills", []),
            )

        # ── Step 3: Skill Analysis (Resume Judge cross-reference) ─────────
        logger.info("[pipeline] step=3 Skill Analysis analysis_id=%s", analysis.id)
        
        if settings.MOCK_MODE:
            logger.info("[pipeline] MOCK_MODE: using synthetic skill analysis")
            skill_raw = self._mock_skill_analysis(target_role)
            # Persist mock skills to database
            await self._persist_candidate_skills(analysis, skill_raw)
        else:
            skill_raw = await self._run_skill_analysis(
                analysis=analysis,
                github_raw=github_raw,
                resume_raw=resume_raw,
                target_role=target_role,
                job_description=job_description or "",
            )

        # ── Step 4: Project Recommender ───────────────────────────────────
        logger.info("[pipeline] step=4 Project Recommender analysis_id=%s", analysis.id)
        verified_skill_names = [s.get("name", "") for s in skill_raw.get("verified_skills", [])]
        missing_skill_names  = [s.get("name", "") for s in skill_raw.get("missing_skills", [])]

        if settings.MOCK_MODE:
            logger.info("[pipeline] MOCK_MODE: using synthetic project recommendations")
            project_raw = self._mock_project_recommendations(target_role)
            analysis.project_recommender_output = project_raw
        else:
            project_raw = await self._run_project_recommender(
                analysis=analysis,
                career_goal=target_role,
                verified_skills=verified_skill_names,
                skill_gaps=missing_skill_names,
            )

        # ── Step 5: Roadmap Generator ─────────────────────────────────────
        logger.info("[pipeline] step=5 Roadmap Generator analysis_id=%s", analysis.id)
        recommended_project_titles = [
            r.get("title", "") for r in project_raw.get("recommendations", [])
        ]
        
        if settings.MOCK_MODE:
            logger.info("[pipeline] MOCK_MODE: using synthetic roadmap")
            roadmap_raw = self._mock_roadmap(target_role)
            analysis.roadmap_generator_output = roadmap_raw
        else:
            roadmap_raw = await self._run_roadmap_generator(
                analysis=analysis,
                career_goal=target_role,
                current_skills=verified_skill_names,
                skill_gaps=missing_skill_names,
                recommended_projects=recommended_project_titles,
            )

        # ── Finalise ──────────────────────────────────────────────────────
        analysis.status = AnalysisStatus.COMPLETED
        match_score = self._compute_match_score(skill_raw)
        analysis.skill_match_score = match_score
        analysis.major_gaps = missing_skill_names[:5]
        await self._db.flush()
        logger.info(
            "[pipeline] completed analysis_id=%s match_score=%.1f",
            analysis.id, match_score,
        )

        return self._assemble_response(
            analysis=analysis,
            skill_raw=skill_raw,
            github_raw=github_raw,
            project_raw=project_raw,
            roadmap_raw=roadmap_raw,
            match_score=match_score,
            major_gaps=missing_skill_names[:5],
        )

    # ─────────────────────────────────────────────────────────────────────
    # Private: individual step helpers
    # ─────────────────────────────────────────────────────────────────────

    async def _run_github_agent(
        self, analysis: Analysis, github_username: str
    ) -> Dict[str, Any]:
        try:
            async with GitHubAgentClient() as client:
                raw = await client.analyze(github_username=github_username)
        except (ServiceUnavailableError, ServiceTimeoutError, ServiceResponseError) as exc:
            logger.warning(
                "GitHub Agent unavailable for %s; falling back to mock data: %s",
                github_username,
                exc,
            )
            raw = self._mock_github_data(github_username)

        analysis.github_agent_output = raw

        for proj in raw.get("projects", []):
            self._db.add(Project(
                analysis_id=analysis.id,
                name=proj.get("name", ""),
                description=proj.get("description"),
                url=proj.get("url"),
                languages=proj.get("languages", []),
                topics=proj.get("topics", []),
            ))
        for skill in raw.get("skills", []):
            for snippet in skill.get("evidence", []):
                self._db.add(Evidence(
                    analysis_id=analysis.id,
                    skill_name=skill.get("name", ""),
                    source="github",
                    snippet=snippet,
                ))
        await self._db.flush()
        return raw

    async def _extract_resume_text(
        self, analysis: Analysis, resume_file: UploadFile
    ) -> str:
        content = await resume_file.read()
        safe_name = ResumeService._safe_filename(resume_file.filename or "resume")
        analysis.resume_filename = safe_name
        await ResumeService._save_file_static(safe_name, content)
        return ResumeService._extract_text(content, resume_file.content_type or "")

    async def _run_resume_judge(
        self,
        analysis: Analysis,
        target_role: str,
        resume_text: str,
        job_description: str,
        github_skills: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        # Try Agentic AI first (direct Gemini)
        try:
            analyzer = AgenticAnalyzer()
            raw = await analyzer.analyze_resume(
                resume_text=resume_text,
                target_role=target_role,
                job_description=job_description,
            )
            logger.info("[AgenticAI] Resume analysis successful")
        except Exception as e:
            logger.warning(f"[AgenticAI] Failed, falling back to microservice: {e}")
            # Fallback to microservice
            async with ResumeJudgeClient() as client:
                raw = await client.analyze_resume(
                    target_role=target_role,
                    resume_text=resume_text,
                    job_description=job_description,
                    github_skills=github_skills,
                )
        
        analysis.resume_judge_output = raw

        for claim in raw.get("claimed_skills", []):
            self._db.add(Evidence(
                analysis_id=analysis.id,
                skill_name=claim.get("name", ""),
                source="resume",
                snippet=claim.get("context", claim.get("name", "")),
            ))
        await self._db.flush()
        return raw

    async def _run_skill_analysis(
        self,
        analysis: Analysis,
        github_raw: Dict[str, Any],
        resume_raw: Dict[str, Any],
        target_role: str,
        job_description: str,
    ) -> Dict[str, Any]:
        # Try Agentic AI first (direct Gemini)
        try:
            analyzer = AgenticAnalyzer()
            raw = await analyzer.cross_reference_skills(
                github_data=github_raw,
                resume_data=resume_raw,
                target_role=target_role,
                job_description=job_description,
            )
            logger.info("[AgenticAI] Skill analysis successful")
        except Exception as e:
            logger.warning(f"[AgenticAI] Failed, falling back to microservice: {e}")
            # Fallback to microservice
            async with ResumeJudgeClient() as client:
                raw = await client.analyze_skills(
                    github_output=github_raw,
                    resume_output=resume_raw,
                    job_title=target_role,
                job_description=job_description,
            )

        # Persist normalised candidate skills
        await self._persist_candidate_skills(analysis, raw)
        return raw

    async def _run_project_recommender(
        self,
        analysis: Analysis,
        career_goal: str,
        verified_skills: List[str],
        skill_gaps: List[str],
    ) -> Dict[str, Any]:
        # Try Agentic AI first (direct Gemini)
        try:
            analyzer = AgenticAnalyzer()
            raw = await analyzer.recommend_projects(
                career_goal=career_goal,
                verified_skills=verified_skills,
                skill_gaps=skill_gaps,
            )
            logger.info("[AgenticAI] Project recommendations successful")
        except Exception as e:
            logger.warning(f"[AgenticAI] Failed, falling back to microservice: {e}")
            # Fallback to microservice
            async with ProjectRecommenderClient() as client:
                raw = await client.recommend(
                    career_goal=career_goal,
                    verified_skills=verified_skills,
                    skill_gaps=skill_gaps,
                )
        
        analysis.project_recommender_output = raw

        for rec in raw.get("recommendations", []):
            self._db.add(RecommendedProject(
                analysis_id=analysis.id,
                title=rec.get("title", ""),
                description=rec.get("description"),
                skills=rec.get("skills", []),
                difficulty=rec.get("difficulty", "intermediate"),
                reason=rec.get("reason"),
            ))
        await self._db.flush()
        return raw

    async def _run_roadmap_generator(
        self,
        analysis: Analysis,
        career_goal: str,
        current_skills: List[str],
        skill_gaps: List[str],
        recommended_projects: List[str],
    ) -> Dict[str, Any]:
        # Try Agentic AI first (direct Gemini)
        try:
            analyzer = AgenticAnalyzer()
            raw = await analyzer.generate_roadmap(
                career_goal=career_goal,
                current_skills=current_skills,
                skill_gaps=skill_gaps,
                recommended_projects=recommended_projects,
            )
            logger.info("[AgenticAI] Roadmap generation successful")
        except Exception as e:
            logger.warning(f"[AgenticAI] Failed, falling back to microservice: {e}")
            # Fallback to microservice
            async with RoadmapGeneratorClient() as client:
                raw = await client.generate(
                    career_goal=career_goal,
                    current_skills=current_skills,
                    skill_gaps=skill_gaps,
                    recommended_projects=recommended_projects,
                )
        
        analysis.roadmap_generator_output = raw

        roadmap = Roadmap(
            analysis_id=analysis.id,
            career_goal=career_goal,
            summary=raw.get("summary"),
            total_weeks=raw.get("total_weeks"),
        )
        self._db.add(roadmap)
        await self._db.flush()

        for step in raw.get("roadmap", []):
            self._db.add(RoadmapStep(
                roadmap_id=roadmap.id,
                week=step.get("week", 0),
                topic=step.get("topic", ""),
                description=step.get("description"),
                resources=step.get("resources", []),
                milestone=step.get("milestone"),
                skills_covered=step.get("skills_covered", []),
            ))
        await self._db.flush()
        return raw

    # ─────────────────────────────────────────────────────────────────────
    # Private: persistence helpers
    # ─────────────────────────────────────────────────────────────────────

    async def _persist_candidate_skills(
        self, analysis: Analysis, skill_raw: Dict[str, Any]
    ) -> None:
        """Upsert skills into the master catalogue and link to this analysis."""
        level_map = {
            "verified_skills":    SkillLevel.VERIFIED,
            "partial_skills":     SkillLevel.PARTIAL,
            "missing_skills":     SkillLevel.MISSING,
            "unsupported_claims": SkillLevel.UNSUPPORTED,
        }
        for key, level in level_map.items():
            for skill_data in skill_raw.get(key, []):
                name = skill_data.get("name", "").strip()
                if not name:
                    continue
                skill = await self._get_or_create_skill(name)
                self._db.add(CandidateSkill(
                    analysis_id=analysis.id,
                    skill_id=skill.id,
                    level=level,
                    confidence=skill_data.get("confidence"),
                ))
        await self._db.flush()

    async def _get_or_create_skill(self, name: str) -> Skill:
        existing = await self._db.scalar(
            select(Skill).where(Skill.name == name)
        )
        if existing:
            return existing
        skill = Skill(name=name)
        self._db.add(skill)
        await self._db.flush()
        return skill

    # ─────────────────────────────────────────────────────────────────────
    # Private: response builders
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_match_score(skill_raw: Dict[str, Any]) -> float:
        verified = len(skill_raw.get("verified_skills", []))
        partial  = len(skill_raw.get("partial_skills", []))
        missing  = len(skill_raw.get("missing_skills", []))
        total = verified + partial + missing
        if total == 0:
            return 0.0
        return round((verified + 0.5 * partial) / total * 100, 1)

    @staticmethod
    def _assemble_response(
        analysis: Analysis,
        skill_raw: Dict[str, Any],
        github_raw: Dict[str, Any],
        project_raw: Dict[str, Any],
        roadmap_raw: Dict[str, Any],
        match_score: float,
        major_gaps: List[str],
    ) -> FullAnalysisRead:
        def _to_skill_details(key: str) -> List[SkillDetail]:
            return [
                SkillDetail(
                    name=s.get("name", ""),
                    confidence=s.get("confidence"),
                    evidence=s.get("evidence", []),
                )
                for s in skill_raw.get(key, [])
            ]

        existing_projects = [
            {"name": p.get("name"), "url": p.get("url"), "languages": p.get("languages", [])}
            for p in github_raw.get("projects", [])
        ]

        return FullAnalysisRead(
            analysis_id=analysis.id,
            status=analysis.status,
            candidate=CandidateInfo(user_id=analysis.user_id),
            skills=SkillsSummary(
                verified=_to_skill_details("verified_skills"),
                partial=_to_skill_details("partial_skills"),
                missing=_to_skill_details("missing_skills"),
            ),
            evidence=[
                {"skill": e.get("name", ""), "source": "github", "snippet": ev}
                for e in github_raw.get("skills", [])
                for ev in e.get("evidence", [])
            ],
            projects=ProjectsSummary(
                existing=existing_projects,
                recommended=project_raw.get("recommendations", []),
            ),
            roadmap=roadmap_raw.get("roadmap", []),
            summary=AnalysisSummary(
                skill_match=match_score,
                major_gaps=major_gaps,
            ),
        )

    @staticmethod
    def _build_response(analysis: Analysis) -> FullAnalysisRead:
        """Reconstruct the response from persisted DB rows (for GET requests)."""
        github_raw   = analysis.github_agent_output or {}
        skill_raw    = {}
        project_raw  = analysis.project_recommender_output or {}
        roadmap_raw  = analysis.roadmap_generator_output or {}

        # Rebuild skill lists from normalised CandidateSkill rows
        level_to_key = {
            SkillLevel.VERIFIED:    "verified_skills",
            SkillLevel.PARTIAL:     "partial_skills",
            SkillLevel.MISSING:     "missing_skills",
            SkillLevel.UNSUPPORTED: "unsupported_claims",
        }
        for cs in analysis.candidate_skills:
            key = level_to_key.get(cs.level, "verified_skills")
            skill_raw.setdefault(key, []).append({
                "name": cs.skill.name,
                "confidence": cs.confidence,
                "evidence": [],
            })

        match_score = analysis.skill_match_score or 0.0
        major_gaps  = analysis.major_gaps or []

        return OrchestrationService._assemble_response(
            analysis=analysis,
            skill_raw=skill_raw,
            github_raw=github_raw,
            project_raw=project_raw,
            roadmap_raw=roadmap_raw,
            match_score=match_score,
            major_gaps=major_gaps,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Private: Mock data generators (used when MOCK_MODE=true)
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _mock_github_data(github_username: str) -> Dict[str, Any]:
        """Generate synthetic GitHub analysis data for testing."""
        return {
            "username": github_username,
            "projects": [
                {
                    "name": "portfolio-website",
                    "description": "Personal portfolio built with React and TypeScript",
                    "url": f"https://github.com/{github_username}/portfolio-website",
                    "languages": ["TypeScript", "JavaScript", "CSS"],
                    "topics": ["react", "portfolio", "frontend"],
                },
                {
                    "name": "api-server",
                    "description": "RESTful API with Node.js and Express",
                    "url": f"https://github.com/{github_username}/api-server",
                    "languages": ["JavaScript", "TypeScript"],
                    "topics": ["nodejs", "express", "rest-api"],
                },
            ],
            "skills": [
                {
                    "name": "React",
                    "confidence": 0.9,
                    "evidence": [
                        "Used hooks and context in portfolio-website",
                        "Implemented responsive components with TypeScript",
                    ],
                },
                {
                    "name": "TypeScript",
                    "confidence": 0.85,
                    "evidence": [
                        "Strong typing across multiple projects",
                        "Interface definitions and generics usage",
                    ],
                },
                {
                    "name": "Node.js",
                    "confidence": 0.8,
                    "evidence": [
                        "Express server implementation",
                        "Middleware and routing patterns",
                    ],
                },
            ],
        }

    @staticmethod
    def _mock_resume_data(target_role: str) -> Dict[str, Any]:
        """Generate synthetic resume analysis data for testing."""
        return {
            "claimed_skills": [
                {"name": "React", "context": "3 years experience building SPAs", "confidence": 0.9},
                {"name": "Python", "context": "Backend development and scripting", "confidence": 0.7},
                {"name": "SQL", "context": "Database design and optimization", "confidence": 0.75},
                {"name": "Git", "context": "Version control and collaboration", "confidence": 0.85},
            ],
            "experience_years": 3,
            "education": "Bachelor's in Computer Science",
            "summary": f"Experienced developer seeking {target_role} position",
        }

    @staticmethod
    def _mock_skill_analysis(target_role: str) -> Dict[str, Any]:
        """Generate synthetic skill cross-reference data for testing."""
        return {
            "verified_skills": [
                {
                    "name": "React",
                    "confidence": 0.9,
                    "evidence": ["GitHub: portfolio-website", "Resume: 3 years SPA experience"],
                },
                {
                    "name": "TypeScript",
                    "confidence": 0.85,
                    "evidence": ["GitHub: Strong typing across projects", "Resume: mentioned in skills"],
                },
                {
                    "name": "Node.js",
                    "confidence": 0.8,
                    "evidence": ["GitHub: Express server", "Resume: Backend development"],
                },
            ],
            "partial_skills": [
                {
                    "name": "Python",
                    "confidence": 0.5,
                    "evidence": ["Resume: mentioned but no GitHub projects"],
                },
                {
                    "name": "SQL",
                    "confidence": 0.6,
                    "evidence": ["Resume: database work mentioned"],
                },
            ],
            "missing_skills": [
                {
                    "name": "Docker",
                    "confidence": 0.0,
                    "evidence": [f"Required for {target_role} but not found"],
                },
                {
                    "name": "Kubernetes",
                    "confidence": 0.0,
                    "evidence": ["Container orchestration needed for role"],
                },
                {
                    "name": "CI/CD",
                    "confidence": 0.0,
                    "evidence": ["DevOps practices expected"],
                },
            ],
        }

    @staticmethod
    def _mock_project_recommendations(target_role: str) -> Dict[str, Any]:
        """Generate synthetic project recommendations for testing."""
        return {
            "recommendations": [
                {
                    "title": "Containerized Microservices App",
                    "description": "Build a multi-service application with Docker and orchestrate with Kubernetes",
                    "skills": ["Docker", "Kubernetes", "Microservices"],
                    "difficulty": "intermediate",
                    "reason": "Address container orchestration gap",
                    "estimated_hours": 40,
                },
                {
                    "title": "CI/CD Pipeline Setup",
                    "description": "Create automated testing and deployment pipeline with GitHub Actions",
                    "skills": ["CI/CD", "GitHub Actions", "Testing"],
                    "difficulty": "beginner",
                    "reason": "Learn DevOps automation",
                    "estimated_hours": 20,
                },
                {
                    "title": "Full-Stack E-commerce Platform",
                    "description": "Build complete e-commerce site with payment integration and admin dashboard",
                    "skills": ["React", "Node.js", "PostgreSQL", "Stripe API"],
                    "difficulty": "advanced",
                    "reason": "Consolidate full-stack skills",
                    "estimated_hours": 80,
                },
            ],
        }

    @staticmethod
    def _mock_roadmap(target_role: str) -> Dict[str, Any]:
        """Generate synthetic learning roadmap for testing."""
        return {
            "summary": f"12-week roadmap to become job-ready for {target_role} position",
            "total_weeks": 12,
            "roadmap": [
                {
                    "week": 1,
                    "topic": "Docker Fundamentals",
                    "description": "Learn containerization basics, Dockerfile, docker-compose",
                    "resources": [
                        "https://docs.docker.com/get-started/",
                        "Docker official tutorial",
                    ],
                    "milestone": "Build and run first containerized app",
                    "skills_covered": ["Docker"],
                    "priority": "high",
                },
                {
                    "week": 2,
                    "topic": "Kubernetes Basics",
                    "description": "Introduction to K8s, pods, services, deployments",
                    "resources": [
                        "https://kubernetes.io/docs/tutorials/",
                        "Kubernetes by Example",
                    ],
                    "milestone": "Deploy app to local K8s cluster",
                    "skills_covered": ["Kubernetes"],
                    "priority": "high",
                },
                {
                    "week": 3,
                    "topic": "CI/CD with GitHub Actions",
                    "description": "Automate testing and deployment workflows",
                    "resources": [
                        "https://docs.github.com/en/actions",
                        "CI/CD best practices",
                    ],
                    "milestone": "Set up automated pipeline",
                    "skills_covered": ["CI/CD", "GitHub Actions"],
                    "priority": "high",
                },
                {
                    "week": 4,
                    "topic": "Microservices Architecture",
                    "description": "Design patterns, service communication, API gateways",
                    "resources": ["Microservices patterns book", "Martin Fowler articles"],
                    "milestone": "Design multi-service system",
                    "skills_covered": ["Microservices", "System Design"],
                    "priority": "medium",
                },
            ],
        }

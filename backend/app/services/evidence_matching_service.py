"""
EvidenceMatchingService
────────────────────────
Ties together the two things this teammate owns:

  1. Resume ⟷ GitHub verification
     For every skill claimed on the resume, check whether the candidate's
     *own GitHub projects* actually demonstrate it, and to what percentage.

  2. Target-role fit
     For every skill a target role needs (e.g. "Database Engineer" needs
     SQL, PostgreSQL, MongoDB, ...), check the candidate's GitHub for real
     project evidence, and classify each required skill as:
        - verified  → strong evidence in a real GitHub project
        - partial   → claimed on the resume, but no real project evidence
        - missing   → neither claimed nor evidenced — a genuine gap to learn

Everything about the candidate's GitHub is fetched live, on every call —
nothing is cached or hard-coded.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.services.github_evidence_service import (
    GitHubEvidenceService,
    GitHubProfileEvidence,
    GitHubRateLimitedError,
    GitHubUserNotFoundError,
)
from app.services.resume_skill_service import extract_resume_skills
from app.services.skill_taxonomy import resolve_role_key, resolve_role_skills, skill_display_name

logger = get_logger(__name__)

VERIFIED_THRESHOLD = 60  # github evidence % at/above this counts as "verified"


@dataclass
class SkillVerification:
    skill_id: str
    skill: str
    status: str                    # "verified" | "partial"
    github_percentage: int
    best_project: Optional[str]
    evidence: List[str] = field(default_factory=list)
    resume_context: str = ""


@dataclass
class RoleSkillFit:
    skill_id: str
    skill: str
    status: str                    # "verified" | "partial" | "missing"
    github_percentage: int
    best_project: Optional[str]
    evidence: List[str] = field(default_factory=list)
    in_resume: bool = False
    suggestion: Optional[str] = None


@dataclass
class EvidenceAnalysisResult:
    github_username: str
    github_exists: bool
    repos_analyzed: int
    repos_truncated: bool
    resume_skills_detected: List[str]
    project_skill_map: List[Dict[str, Any]]
    skill_verification: List[SkillVerification]
    target_role: str
    resolved_role: str
    role_required_skills: List[str]
    role_fit: List[RoleSkillFit]
    role_coverage_percent: float
    gaps_to_learn: List[Dict[str, Any]]
    warnings: List[str] = field(default_factory=list)


class EvidenceMatchingService:
    def __init__(self, github_token: Optional[str] = None, max_repos: int = 15):
        self._github_token = github_token
        self._max_repos = max_repos

    async def analyze(
        self,
        resume_text: str,
        github_username: str,
        target_role: str,
        repositories: Optional[List[str]] = None,
    ) -> EvidenceAnalysisResult:
        warnings: List[str] = []

        # 1. Resume skills (deterministic keyword/alias matching)
        resume_claims = extract_resume_skills(resume_text)

        # 2. Live GitHub evidence
        async with GitHubEvidenceService(
            token=self._github_token, max_repos=self._max_repos
        ) as gh:
            try:
                profile: GitHubProfileEvidence = await gh.build_profile(
                    github_username, repo_filter=repositories
                )
            except GitHubUserNotFoundError:
                return self._empty_result_for_missing_user(
                    resume_claims, github_username, target_role
                )
            except GitHubRateLimitedError as exc:
                warnings.append(str(exc))
                profile = GitHubProfileEvidence(username=github_username, exists=True)

            project_skill_map, skill_best_evidence = gh.score_profile(profile)

        # 3. Resume ⟷ GitHub verification (task 1)
        skill_verification = self._build_skill_verification(resume_claims, skill_best_evidence)

        # 4. Target-role fit + gap analysis (task 2)
        role_key = resolve_role_key(target_role)
        required_skills = resolve_role_skills(target_role)
        role_fit = self._build_role_fit(required_skills, resume_claims, skill_best_evidence)
        role_coverage_percent = self._coverage_percent(role_fit)
        gaps_to_learn = self._build_gap_suggestions(role_fit, project_skill_map)

        return EvidenceAnalysisResult(
            github_username=github_username,
            github_exists=profile.exists,
            repos_analyzed=profile.repos_analyzed,
            repos_truncated=profile.truncated,
            resume_skills_detected=[c.skill for c in resume_claims.values()],
            project_skill_map=project_skill_map,
            skill_verification=skill_verification,
            target_role=target_role,
            resolved_role=role_key,
            role_required_skills=[skill_display_name(s) for s in required_skills],
            role_fit=role_fit,
            role_coverage_percent=role_coverage_percent,
            gaps_to_learn=gaps_to_learn,
            warnings=warnings,
        )

    # ── Task 1: resume ⟷ GitHub verification ────────────────────────────

    def _build_skill_verification(
        self,
        resume_claims: Dict[str, Any],
        skill_best_evidence: Dict[str, Dict[str, Any]],
    ) -> List[SkillVerification]:
        results: List[SkillVerification] = []
        for skill_id, claim in resume_claims.items():
            best = skill_best_evidence.get(skill_id)
            pct = best["percentage"] if best else 0
            status = "verified" if pct >= VERIFIED_THRESHOLD else "partial"
            results.append(
                SkillVerification(
                    skill_id=skill_id,
                    skill=claim.skill,
                    status=status,
                    github_percentage=pct,
                    best_project=best["project"] if best else None,
                    evidence=best["evidence"] if best else [],
                    resume_context=claim.context,
                )
            )
        results.sort(key=lambda r: (-r.github_percentage))
        return results

    # ── Task 2: role fit + gap analysis ─────────────────────────────────

    def _build_role_fit(
        self,
        required_skills: List[str],
        resume_claims: Dict[str, Any],
        skill_best_evidence: Dict[str, Dict[str, Any]],
    ) -> List[RoleSkillFit]:
        fit: List[RoleSkillFit] = []
        for skill_id in required_skills:
            best = skill_best_evidence.get(skill_id)
            pct = best["percentage"] if best else 0
            in_resume = skill_id in resume_claims

            if pct >= VERIFIED_THRESHOLD:
                status = "verified"
            elif in_resume:
                status = "partial"
            else:
                status = "missing"

            suggestion = None
            if status != "verified":
                name = skill_display_name(skill_id)
                suggestion = f"Build (or extend) a project that visibly uses {name}"

            fit.append(
                RoleSkillFit(
                    skill_id=skill_id,
                    skill=skill_display_name(skill_id),
                    status=status,
                    github_percentage=pct,
                    best_project=best["project"] if best else None,
                    evidence=best["evidence"] if best else [],
                    in_resume=in_resume,
                    suggestion=suggestion,
                )
            )
        fit.sort(key=lambda r: (-r.github_percentage))
        return fit

    def _coverage_percent(self, role_fit: List[RoleSkillFit]) -> float:
        if not role_fit:
            return 0.0
        return round(sum(r.github_percentage for r in role_fit) / len(role_fit), 1)

    def _build_gap_suggestions(
        self, role_fit: List[RoleSkillFit], project_skill_map: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        existing_project_names = [p["project"] for p in project_skill_map]
        gaps = []
        for r in role_fit:
            if r.status == "missing":
                gaps.append({
                    "skill": r.skill,
                    "status": "missing",
                    "recommendation": (
                        f"No evidence of {r.skill} anywhere in your resume or GitHub. "
                        f"Start a small project that uses {r.skill} directly."
                    ),
                })
            elif r.status == "partial":
                gaps.append({
                    "skill": r.skill,
                    "status": "partial",
                    "recommendation": (
                        f"Your resume claims {r.skill}, but none of your public GitHub "
                        f"projects demonstrate it. Add {r.skill} to an existing project "
                        + (f"such as '{existing_project_names[0]}'" if existing_project_names else "")
                        + f", or publish a new one, so it becomes verifiable."
                    ),
                })
        return gaps

    def _empty_result_for_missing_user(
        self, resume_claims: Dict[str, Any], github_username: str, target_role: str
    ) -> EvidenceAnalysisResult:
        role_key = resolve_role_key(target_role)
        required_skills = resolve_role_skills(target_role)
        role_fit = self._build_role_fit(required_skills, resume_claims, {})
        return EvidenceAnalysisResult(
            github_username=github_username,
            github_exists=False,
            repos_analyzed=0,
            repos_truncated=False,
            resume_skills_detected=[c.skill for c in resume_claims.values()],
            project_skill_map=[],
            skill_verification=self._build_skill_verification(resume_claims, {}),
            target_role=target_role,
            resolved_role=role_key,
            role_required_skills=[skill_display_name(s) for s in required_skills],
            role_fit=role_fit,
            role_coverage_percent=0.0,
            gaps_to_learn=self._build_gap_suggestions(role_fit, []),
            warnings=[f"GitHub user '{github_username}' was not found — showing resume-only results."],
        )


def result_to_dict(result: EvidenceAnalysisResult) -> Dict[str, Any]:
    d = asdict(result)
    return d

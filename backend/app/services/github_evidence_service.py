"""
GitHubEvidenceService
──────────────────────
Fetches a GitHub user's repositories **live** from the GitHub REST API
(no caching, no stub data) and scores, for every repository, how strongly
each skill in SKILL_TAXONOMY is evidenced there.

Evidence signals, strongest → weakest:
    topic match           (repo owner explicitly tagged the tech)   -> 90
    dependency match       (found in requirements.txt/package.json)  -> 85
    filename match          (Dockerfile, .github/workflows, ...)     -> 80
    language byte-share     (primary/secondary language of the repo) -> proportional, capped 100, floor 45
    keyword in description/README (weak, textual mention only)      -> 40

For each repo we keep the *max* signal score per skill (not a sum) plus a
human-readable evidence trail. Callers aggregate the per-repo scores into a
single "best evidence" score per skill across the whole profile.

Only public, non-fork repositories are considered by default.
"""
from __future__ import annotations

import asyncio
import base64
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.skill_taxonomy import SKILL_TAXONOMY, SkillSignal

settings = get_settings()
logger = get_logger(__name__)

GITHUB_API = "https://api.github.com"

MANIFEST_FILENAMES = {
    "requirements.txt", "pyproject.toml", "pipfile", "package.json",
    "pom.xml", "build.gradle", "build.gradle.kts", "gemfile", "go.mod",
    "cargo.toml", "composer.json",
}


class GitHubUserNotFoundError(Exception):
    pass


class GitHubRateLimitedError(Exception):
    pass


@dataclass
class RepoEvidence:
    name: str
    full_name: str
    description: str
    url: str
    topics: List[str]
    languages: Dict[str, int]          # language -> byte count
    manifest_text: str                 # lowercased, concatenated dependency files
    readme_text: str                   # lowercased, truncated
    root_filenames: List[str]          # lowercased filenames/dirnames at repo root
    stars: int
    updated_at: str
    is_fork: bool


@dataclass
class GitHubProfileEvidence:
    username: str
    exists: bool
    avatar_url: Optional[str] = None
    public_repos_count: int = 0
    repos: List[RepoEvidence] = field(default_factory=list)
    repos_analyzed: int = 0
    truncated: bool = False            # True if user has more repos than we analyzed


@dataclass
class SkillScore:
    score: int                          # 0-100, how strongly evidenced in THIS repo
    evidence: List[str]


class GitHubEvidenceService:
    def __init__(self, token: Optional[str] = None, max_repos: int = 15, concurrency: int = 6):
        self._token = token or getattr(settings, "GITHUB_TOKEN", "") or ""
        self._max_repos = max_repos
        self._semaphore = asyncio.Semaphore(concurrency)
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if self._token and not self._token.startswith("ghp_..."):
            headers["Authorization"] = f"Bearer {self._token}"
        self._client = httpx.AsyncClient(base_url=GITHUB_API, headers=headers, timeout=20.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "GitHubEvidenceService":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    # ── Public API ───────────────────────────────────────────────────────

    async def build_profile(
        self, username: str, repo_filter: Optional[List[str]] = None
    ) -> GitHubProfileEvidence:
        """Fetch the user's public repos and evidence for each, live."""
        user_resp = await self._client.get(f"/users/{username}")
        self._raise_for_rate_limit(user_resp)
        if user_resp.status_code == 404:
            raise GitHubUserNotFoundError(f"GitHub user '{username}' was not found.")
        user_resp.raise_for_status()
        user_data = user_resp.json()

        repos_meta = await self._list_repos(username)
        if repo_filter:
            wanted = {r.lower() for r in repo_filter}
            repos_meta = [r for r in repos_meta if r["name"].lower() in wanted]

        # Prefer non-forks, most recently updated first (already sorted by API call)
        non_forks = [r for r in repos_meta if not r.get("fork")]
        candidates = non_forks or repos_meta
        truncated = len(candidates) > self._max_repos
        selected = candidates[: self._max_repos]

        repo_evidences = await asyncio.gather(
            *[self._build_repo_evidence(username, r) for r in selected],
            return_exceptions=True,
        )
        clean_evidences: List[RepoEvidence] = []
        for r, ev in zip(selected, repo_evidences):
            if isinstance(ev, Exception):
                logger.warning("Skipping repo %s due to error: %s", r.get("name"), ev)
                continue
            clean_evidences.append(ev)

        return GitHubProfileEvidence(
            username=username,
            exists=True,
            avatar_url=user_data.get("avatar_url"),
            public_repos_count=user_data.get("public_repos", len(repos_meta)),
            repos=clean_evidences,
            repos_analyzed=len(clean_evidences),
            truncated=truncated,
        )

    def score_profile(
        self, profile: GitHubProfileEvidence
    ) -> tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """
        Returns:
          project_skill_map: [{project, url, skills: [{skill_id, skill, percentage, evidence}]}]
          skill_best_evidence: {skill_id: {percentage, project, evidence: [...]}}
        """
        project_skill_map: List[Dict[str, Any]] = []
        skill_best_evidence: Dict[str, Dict[str, Any]] = {}

        for repo in profile.repos:
            per_repo_skills = self._score_repo(repo)
            if per_repo_skills:
                project_skill_map.append({
                    "project": repo.name,
                    "url": repo.url,
                    "skills": [
                        {
                            "skill_id": skill_id,
                            "skill": SKILL_TAXONOMY[skill_id].name,
                            "percentage": s.score,
                            "evidence": s.evidence,
                        }
                        for skill_id, s in sorted(
                            per_repo_skills.items(), key=lambda kv: -kv[1].score
                        )
                    ],
                })
            for skill_id, s in per_repo_skills.items():
                best = skill_best_evidence.get(skill_id)
                if best is None or s.score > best["percentage"]:
                    skill_best_evidence[skill_id] = {
                        "percentage": s.score,
                        "project": repo.name,
                        "evidence": s.evidence,
                    }

        return project_skill_map, skill_best_evidence

    # ── Internal: fetching ───────────────────────────────────────────────

    async def _list_repos(self, username: str) -> List[Dict[str, Any]]:
        repos: List[Dict[str, Any]] = []
        page = 1
        while page <= 3:  # up to 300 repos, plenty for a candidate profile
            resp = await self._client.get(
                f"/users/{username}/repos",
                params={"per_page": 100, "sort": "updated", "type": "owner", "page": page},
            )
            self._raise_for_rate_limit(resp)
            if resp.status_code == 404:
                raise GitHubUserNotFoundError(f"GitHub user '{username}' was not found.")
            resp.raise_for_status()
            batch = resp.json()
            repos.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return repos

    async def _build_repo_evidence(self, owner: str, repo_meta: Dict[str, Any]) -> RepoEvidence:
        async with self._semaphore:
            name = repo_meta["name"]
            languages_task = self._client.get(f"/repos/{owner}/{name}/languages")
            contents_task = self._client.get(f"/repos/{owner}/{name}/contents")
            readme_task = self._client.get(
                f"/repos/{owner}/{name}/readme",
                headers={"Accept": "application/vnd.github.raw"},
            )
            languages_resp, contents_resp, readme_resp = await asyncio.gather(
                languages_task, contents_task, readme_task, return_exceptions=True
            )

        languages = {}
        if isinstance(languages_resp, httpx.Response) and languages_resp.status_code == 200:
            languages = languages_resp.json()

        root_filenames: List[str] = []
        manifest_files: List[Dict[str, Any]] = []
        if isinstance(contents_resp, httpx.Response) and contents_resp.status_code == 200:
            try:
                items = contents_resp.json()
                if isinstance(items, list):
                    for item in items:
                        fname = str(item.get("name", "")).lower()
                        root_filenames.append(fname)
                        if fname in MANIFEST_FILENAMES:
                            manifest_files.append(item)
            except ValueError:
                pass

        manifest_text = await self._fetch_manifest_text(manifest_files)

        readme_text = ""
        if isinstance(readme_resp, httpx.Response) and readme_resp.status_code == 200:
            readme_text = readme_resp.text[:4000].lower()

        return RepoEvidence(
            name=name,
            full_name=repo_meta.get("full_name", f"{owner}/{name}"),
            description=(repo_meta.get("description") or "").lower(),
            url=repo_meta.get("html_url", f"https://github.com/{owner}/{name}"),
            topics=[t.lower() for t in repo_meta.get("topics", [])],
            languages=languages,
            manifest_text=manifest_text.lower(),
            readme_text=readme_text,
            root_filenames=root_filenames,
            stars=repo_meta.get("stargazers_count", 0),
            updated_at=repo_meta.get("updated_at", ""),
            is_fork=bool(repo_meta.get("fork")),
        )

    async def _fetch_manifest_text(self, manifest_files: List[Dict[str, Any]]) -> str:
        if not manifest_files:
            return ""
        chunks: List[str] = []
        for item in manifest_files:
            download_url = item.get("download_url")
            if not download_url:
                content_b64 = item.get("content")
                if content_b64:
                    try:
                        chunks.append(base64.b64decode(content_b64).decode("utf-8", "ignore"))
                    except Exception:
                        pass
                continue
            try:
                resp = await self._client.get(download_url)
                if resp.status_code == 200:
                    chunks.append(resp.text[:5000])
            except Exception as exc:
                logger.debug("Manifest fetch failed for %s: %s", download_url, exc)
        return "\n".join(chunks)

    def _raise_for_rate_limit(self, resp: httpx.Response) -> None:
        if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
            raise GitHubRateLimitedError(
                "GitHub API rate limit exceeded. Set GITHUB_TOKEN in .env to raise the limit."
            )

    # ── Internal: scoring ────────────────────────────────────────────────

    def _score_repo(self, repo: RepoEvidence) -> Dict[str, SkillScore]:
        total_bytes = sum(repo.languages.values()) or 1
        scores: Dict[str, SkillScore] = {}

        for skill_id, signal in SKILL_TAXONOMY.items():
            best_score = 0
            evidence: List[str] = []

            # 1. Topic match (strongest — author-declared)
            if any(t in repo.topics for t in signal.topics):
                best_score = max(best_score, 90)
                evidence.append(f"Tagged as a GitHub topic on '{repo.name}'")

            # 2. Dependency manifest match
            if repo.manifest_text and any(
                dep.lower() in repo.manifest_text for dep in signal.dependencies
            ):
                best_score = max(best_score, 85)
                evidence.append(f"Found in dependency manifest of '{repo.name}'")

            # 3. Filename / project-structure match
            if any(
                any(fn in root for root in repo.root_filenames)
                for fn in signal.filenames
            ):
                best_score = max(best_score, 80)
                evidence.append(f"Detected via project files in '{repo.name}'")

            # 4. Language byte-share
            if signal.languages:
                lang_bytes = sum(repo.languages.get(lang, 0) for lang in signal.languages)
                if lang_bytes > 0:
                    pct = round(100 * lang_bytes / total_bytes)
                    lang_score = max(45, pct)
                    if lang_score > best_score:
                        best_score = lang_score
                        evidence.append(f"{pct}% of code in '{repo.name}' is {signal.name}")

            # 5. Weak keyword mention in description/README
            if best_score < 60:
                haystack = f"{repo.description} {repo.readme_text}"
                if any(_word_in_text(alias, haystack) for alias in signal.aliases):
                    if best_score < 40:
                        best_score = 40
                        evidence.append(f"Mentioned in README/description of '{repo.name}'")

            if best_score > 0:
                scores[skill_id] = SkillScore(score=min(100, best_score), evidence=evidence)

        return scores


def _word_in_text(alias: str, text: str) -> bool:
    alias = alias.strip().lower()
    if not alias:
        return False
    if " " in alias or "." in alias or "#" in alias or "+" in alias:
        return alias in text
    return re.search(rf"\b{re.escape(alias)}\b", text) is not None

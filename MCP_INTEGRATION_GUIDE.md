# MCP Integration Guide - GitHub Analysis

## Quick Start

### 1. Install GitHub MCP Server

```bash
# Install via uvx (recommended - no global install needed)
uvx mcp-server-github

# Or install globally
pip install mcp-server-github
```

### 2. Configure MCP in Kiro

Create or update `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "uvx",
      "args": ["mcp-server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here"
      },
      "disabled": false
    }
  }
}
```

### 3. Get GitHub Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes:
   - `repo` (Full control of private repositories)
   - `read:user` (Read user profile data)
   - `read:org` (Read org data)
4. Copy the token to your `.env` file

### 4. Test MCP Connection

Use Kiro's MCP powers tool to test:

```python
# In Kiro IDE, invoke MCP tool
kiro_powers(
    action="activate",
    powerName="github"
)

# Test listing repositories
kiro_powers(
    action="use",
    powerName="github",
    serverName="github",
    toolName="search_repositories",
    arguments={"username": "your-github-username"}
)
```

## Backend Integration

### Step 1: Create MCP Client Wrapper

Create `backend/app/clients/mcp_github_client.py`:

```python
"""
GitHub MCP Client
─────────────────
Uses Kiro's MCP GitHub server for repository analysis.
Replaces the old GitHubAgentClient microservice.
"""
from typing import Any, Dict, List
import httpx
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class GitHubMCPClient:
    """
    Client for GitHub analysis via MCP server.
    Communicates with Kiro's MCP infrastructure.
    """
    
    def __init__(self):
        self.mcp_endpoint = settings.KIRO_MCP_ENDPOINT or "http://localhost:3000/mcp"
        self.github_token = settings.GITHUB_TOKEN
    
    async def analyze_user_repos(self, username: str) -> Dict[str, Any]:
        """
        Analyze a GitHub user's repositories.
        Returns structured data about projects, skills, and evidence.
        """
        logger.info(f"[MCP] Analyzing GitHub user: {username}")
        
        # Step 1: Search repositories
        repos_data = await self._call_mcp_tool(
            "search_repositories",
            {"username": username, "per_page": 20}
        )
        
        repos = repos_data.get("repositories", [])
        logger.info(f"[MCP] Found {len(repos)} repositories")
        
        # Step 2: Analyze each repository
        skills = {}
        projects = []
        evidence = []
        
        for repo in repos[:10]:  # Limit to top 10 repos
            analysis = await self._analyze_repository(username, repo)
            projects.append(analysis["project"])
            
            # Aggregate skills
            for skill in analysis["skills"]:
                skill_name = skill["name"]
                if skill_name not in skills:
                    skills[skill_name] = {
                        "name": skill_name,
                        "confidence": 0,
                        "evidence": []
                    }
                skills[skill_name]["confidence"] = max(
                    skills[skill_name]["confidence"],
                    skill["confidence"]
                )
                skills[skill_name]["evidence"].extend(skill["evidence"])
        
        return {
            "username": username,
            "projects": projects,
            "skills": list(skills.values()),
            "total_repos": len(repos),
        }
    
    async def _analyze_repository(
        self, owner: str, repo: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze a single repository for skills and tech stack."""
        repo_name = repo["name"]
        logger.info(f"[MCP] Analyzing repository: {owner}/{repo_name}")
        
        # Get repository details
        repo_info = await self._call_mcp_tool(
            "get_repository",
            {"owner": owner, "repo": repo_name}
        )
        
        # Try to read key files to identify tech stack
        tech_files = [
            "package.json",      # Node.js
            "requirements.txt",  # Python
            "Cargo.toml",       # Rust
            "go.mod",           # Go
            "pom.xml",          # Java/Maven
            "build.gradle",     # Java/Gradle
        ]
        
        detected_skills = []
        evidence_items = []
        
        for file_path in tech_files:
            try:
                content = await self._call_mcp_tool(
                    "get_file_contents",
                    {
                        "owner": owner,
                        "repo": repo_name,
                        "path": file_path
                    }
                )
                
                # Parse file to extract skills
                skills = self._extract_skills_from_file(file_path, content)
                detected_skills.extend(skills)
                
                for skill in skills:
                    evidence_items.append({
                        "skill": skill["name"],
                        "file": file_path,
                        "repo": repo_name,
                        "snippet": content[:200]
                    })
                
            except Exception as e:
                logger.debug(f"[MCP] File {file_path} not found in {repo_name}: {e}")
                continue
        
        # Fallback to language stats if no files found
        if not detected_skills:
            languages = repo_info.get("languages", {})
            for lang in languages.keys():
                detected_skills.append({
                    "name": lang,
                    "confidence": 0.6,
                    "evidence": [f"Used in {repo_name}"]
                })
        
        return {
            "project": {
                "name": repo_name,
                "description": repo.get("description"),
                "url": repo.get("html_url"),
                "languages": list(repo_info.get("languages", {}).keys()),
                "topics": repo.get("topics", []),
                "stars": repo.get("stargazers_count", 0),
            },
            "skills": detected_skills,
            "evidence": evidence_items,
        }
    
    def _extract_skills_from_file(
        self, file_path: str, content: str
    ) -> List[Dict[str, Any]]:
        """Extract skills from file content."""
        skills = []
        
        if file_path == "package.json":
            # Parse Node.js dependencies
            try:
                import json
                data = json.loads(content)
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                
                if "react" in deps:
                    skills.append({
                        "name": "React",
                        "confidence": 0.9,
                        "evidence": [f"React {deps['react']} in package.json"]
                    })
                if "typescript" in deps or "file_path".endswith(".ts"):
                    skills.append({
                        "name": "TypeScript",
                        "confidence": 0.9,
                        "evidence": ["TypeScript in dependencies"]
                    })
                if "next" in deps:
                    skills.append({
                        "name": "Next.js",
                        "confidence": 0.9,
                        "evidence": [f"Next.js {deps['next']}"]
                    })
            except Exception as e:
                logger.debug(f"Failed to parse package.json: {e}")
        
        elif file_path == "requirements.txt":
            # Parse Python dependencies
            lines = content.split("\n")
            for line in lines:
                line = line.strip().lower()
                if "fastapi" in line:
                    skills.append({
                        "name": "FastAPI",
                        "confidence": 0.9,
                        "evidence": ["FastAPI in requirements.txt"]
                    })
                elif "django" in line:
                    skills.append({
                        "name": "Django",
                        "confidence": 0.9,
                        "evidence": ["Django in requirements.txt"]
                    })
                elif "flask" in line:
                    skills.append({
                        "name": "Flask",
                        "confidence": 0.9,
                        "evidence": ["Flask in requirements.txt"]
                    })
        
        return skills
    
    async def _call_mcp_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call an MCP tool via Kiro's MCP endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.mcp_endpoint}/call",
                json={
                    "server": "github",
                    "tool": tool_name,
                    "arguments": arguments,
                },
                headers={"Authorization": f"Bearer {self.github_token}"},
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
```

### Step 2: Update OrchestrationService

Replace `GitHubAgentClient` with `GitHubMCPClient`:

```python
# In backend/app/services/orchestration_service.py

from app.clients.mcp_github_client import GitHubMCPClient

async def _run_github_agent(
    self, analysis: Analysis, github_username: str
) -> Dict[str, Any]:
    async with GitHubMCPClient() as client:
        raw = await client.analyze_user_repos(github_username)
    
    analysis.github_agent_output = raw
    
    # ... rest of the method stays the same
```

### Step 3: Add Configuration

Update `backend/app/core/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # MCP Configuration
    KIRO_MCP_ENDPOINT: str = "http://localhost:3000/mcp"
    GITHUB_TOKEN: str = ""
    
    # ... rest of settings ...
```

### Step 4: Update Environment Variables

Add to `backend/.env`:

```env
# MCP Configuration
KIRO_MCP_ENDPOINT=http://localhost:3000/mcp
GITHUB_TOKEN=ghp_your_token_here
```

## Testing the Integration

### Test 1: Manual MCP Call

```python
# In Kiro IDE or Python console
from app.clients.mcp_github_client import GitHubMCPClient
import asyncio

async def test_mcp():
    client = GitHubMCPClient()
    result = await client.analyze_user_repos("octocat")
    print(f"Found {len(result['projects'])} projects")
    print(f"Detected skills: {[s['name'] for s in result['skills']]}")

asyncio.run(test_mcp())
```

### Test 2: Full Pipeline

```bash
# Start backend
cd backend
uvicorn app.main:app --reload

# In another terminal, test endpoint
curl -X POST http://localhost:8000/api/v1/analysis \
  -F "user_id=00000000-0000-0000-0000-000000000001" \
  -F "github_username=octocat" \
  -F "target_role=Full-Stack Developer" \
  -F "resume_file=@test_resume.pdf"
```

## Advantages of MCP Approach

### vs. Microservices
- ✅ **No deployment complexity** - Single backend server
- ✅ **No network latency** - Direct Python calls
- ✅ **Unified logging** - All in one place
- ✅ **Easier debugging** - Single codebase

### vs. Direct GitHub API
- ✅ **Standardized protocol** - MCP handles auth, rate limiting
- ✅ **Better abstractions** - High-level tools instead of raw API
- ✅ **Community support** - Official MCP servers maintained
- ✅ **Extensible** - Easy to add GitLab, Bitbucket MCP servers

### Agentic AI Benefits
- ✅ **Autonomous exploration** - AI decides what to analyze
- ✅ **Context-aware** - Sees full picture across tools
- ✅ **Adaptive** - Adjusts strategy based on findings
- ✅ **Explainable** - Reasoning traces show decisions

## Next Steps

1. ✅ Configure GitHub MCP in `.kiro/settings/mcp.json`
2. ⏳ Implement `GitHubMCPClient` 
3. ⏳ Replace `GitHubAgentClient` in OrchestrationService
4. ⏳ Add Agentic AI controller for autonomous analysis
5. ⏳ Test with real GitHub profiles
6. ⏳ Optimize token usage and API calls

## Resources

- [MCP Documentation](https://modelcontextprotocol.io/)
- [GitHub MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/github)
- [Kiro MCP Integration](https://docs.kiro.dev/mcp)
- [Agentic AI Patterns](https://docs.anthropic.com/claude/docs/agents)

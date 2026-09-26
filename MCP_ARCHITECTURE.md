# Career Navigator - MCP-Based Agentic AI Architecture

## Overview

Career Navigator uses **Agentic AI** powered by **Model Context Protocol (MCP)** to autonomously analyze candidate profiles. Instead of rigid microservices, we use intelligent agents that leverage MCP servers for data access and make autonomous decisions about analysis strategies.

## Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Upload Page  │→ │ Processing   │→ │ Results Page │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────────────┐
│                   FastAPI Backend                            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Orchestration Service (Coordinator)            │ │
│  └───────────────────┬────────────────────────────────────┘ │
│                      │                                        │
│  ┌───────────────────▼────────────────────────────────────┐ │
│  │              Agentic AI Controller                     │ │
│  │  • Gemini 3.8 Flash (Primary LLM)                      │ │
│  │  • Autonomous decision making                          │ │
│  │  • Tool use orchestration                              │ │
│  │  • Multi-step reasoning                                │ │
│  └───────────────────┬────────────────────────────────────┘ │
│                      │                                        │
│         ┌────────────┴────────────┬────────────────┐         │
│         │                         │                │         │
│  ┌──────▼──────┐          ┌──────▼──────┐  ┌─────▼─────┐   │
│  │   GitHub    │          │   Resume    │  │   Job     │   │
│  │   MCP       │          │   Parser    │  │  Analysis │   │
│  │   Server    │          │             │  │           │   │
│  └─────────────┘          └─────────────┘  └───────────┘   │
│  • Fetch repos            • Extract text   • Match skills  │
│  • Read code              • Parse resume   • Gen roadmap   │
│  • Search commits         • Identify exp   • Recommend     │
│  • List languages         • Find skills    • Prioritize    │
└─────────────────────────────────────────────────────────────┘
```

## MCP Integration

### GitHub MCP Server
Instead of building a custom GitHub Agent microservice, we use the **official GitHub MCP server** which provides:

**Available Tools:**
- `get_file_contents` - Read file contents from repositories
- `search_repositories` - Search user's GitHub repos
- `create_or_update_file` - Modify files (not used in our read-only analysis)
- `search_code` - Search code across repositories
- `create_issue` - Create issues (not used)
- `create_pull_request` - Create PRs (not used)
- `fork_repository` - Fork repos (not used)
- `push_files` - Push changes (not used)

**Resources:**
- `github://repos` - List user repositories
- `github://repo/{owner}/{repo}` - Get repository details
- `github://repo/{owner}/{repo}/tree/{branch}` - Browse file tree
- `github://repo/{owner}/{repo}/commits` - View commit history

### How Agentic AI Uses MCP

The AI agent autonomously:

1. **Discovers repositories** using `search_repositories`
2. **Analyzes project structure** by reading file trees
3. **Examines code quality** by reading key files (main.py, index.ts, etc.)
4. **Identifies tech stack** from language statistics and dependencies
5. **Finds evidence of skills** by searching code patterns
6. **Makes reasoning chains** about experience level and expertise

Example agent reasoning:
```
Agent: "I need to analyze the candidate's React skills"
→ Search repositories for "react"
→ Read package.json to verify React version
→ Search code for "useState", "useEffect", "custom hooks"
→ Check for TypeScript usage
→ Analyze component patterns
→ CONCLUSION: "Strong React skills with modern hooks, TypeScript proficiency"
```

## Workflow

### 1. Analysis Request
```typescript
POST /api/v1/analysis
{
  user_id: UUID,
  github_username: string,
  target_role: string,
  resume_file: File,
  job_description?: string
}
```

### 2. Agentic AI Pipeline

**Phase 1: GitHub Analysis (via MCP)**
```python
async def analyze_github(agent: AgenticAI, username: str):
    # Agent autonomously explores GitHub profile
    repos = await agent.use_tool("search_repositories", {"user": username})
    
    skills = []
    for repo in repos:
        # Agent decides which files to examine
        files = await agent.use_tool("get_file_contents", {
            "owner": username,
            "repo": repo.name,
            "path": "package.json"  # Agent chooses relevant files
        })
        
        # Agent extracts insights
        analysis = await agent.reason(
            f"Analyze this repository: {repo.name}",
            context={"files": files, "languages": repo.languages}
        )
        skills.extend(analysis.discovered_skills)
    
    return {"skills": skills, "projects": repos, "evidence": evidence}
```

**Phase 2: Resume Analysis**
```python
async def analyze_resume(agent: AgenticAI, resume_text: str, target_role: str):
    # Agent extracts structured information
    return await agent.reason(
        f"""Extract skills, experience, and qualifications for {target_role}.
        Resume: {resume_text}
        
        Output format: {ResumeSchema}"""
    )
```

**Phase 3: Skill Cross-Reference**
```python
async def cross_reference(agent: AgenticAI, github_data, resume_data, jd):
    # Agent performs sophisticated matching
    return await agent.reason(
        """Cross-reference GitHub evidence with resume claims.
        Classify each skill as:
        - VERIFIED: Strong evidence in both GitHub and resume
        - PARTIAL: Claimed but limited code evidence
        - MISSING: Required by job but not found
        - UNSUPPORTED: Claimed without evidence
        
        GitHub: {github_data}
        Resume: {resume_data}
        Job Requirements: {jd}
        """
    )
```

**Phase 4: Project Recommendations**
```python
async def recommend_projects(agent: AgenticAI, verified, missing, role):
    # Agent generates personalized project ideas
    return await agent.reason(
        f"""Generate 3-5 project ideas to close skill gaps for {role}.
        Current skills: {verified}
        Missing skills: {missing}
        
        Each project should target 2-3 missing skills and build on existing strengths.
        """
    )
```

**Phase 5: Learning Roadmap**
```python
async def generate_roadmap(agent: AgenticAI, current, gaps, projects):
    # Agent creates structured learning path
    return await agent.reason(
        """Create a 12-week roadmap with:
        - Week-by-week learning objectives
        - Resources (official docs, tutorials)
        - Milestones and deliverables
        - Skill progression path
        
        Current: {current}
        Gaps: {gaps}
        Projects: {projects}
        """
    )
```

## Configuration

### MCP Server Setup (.kiro/mcp.json)

```json
{
  "mcpServers": {
    "github": {
      "command": "uvx",
      "args": ["mcp-server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

### Environment Variables

```env
# Agentic AI (Primary)
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-3.8-flash
GEMINI_FALLBACK_MODELS=gemini-3.5-flash,gemini-3.7-flash

# GitHub MCP
GITHUB_TOKEN=ghp_your_token_here

# Agent Configuration
AGENT_MAX_ITERATIONS=10
AGENT_TIMEOUT_SECONDS=120
AGENT_ENABLE_REASONING_TRACES=true

# Testing
MOCK_MODE=false  # Use real MCP + AI
MOCK_GITHUB_DATA=false  # Use synthetic GitHub data
```

## Benefits of This Architecture

### 1. **True Agentic Behavior**
- AI makes autonomous decisions about what to analyze
- Adaptive to different project structures
- Self-correcting when data is insufficient

### 2. **MCP Advantages**
- **Standardized protocol** - No custom microservices needed
- **Community support** - Official GitHub MCP server maintained
- **Extensible** - Easy to add more MCP servers (GitLab, Bitbucket)
- **Secure** - Token management handled by MCP

### 3. **Simplified Architecture**
- **No microservice orchestration** - Just MCP tool calls
- **Single deployment** - One FastAPI server
- **Easier debugging** - All logs in one place
- **Lower latency** - No network hops between services

### 4. **Better Analysis Quality**
- **Context-aware** - Agent sees full picture
- **Flexible** - Adapts analysis strategy per profile
- **Deeper insights** - Can explore code in detail
- **Explainable** - Reasoning traces show decision process

## Implementation Plan

### Phase 1: MCP Integration (Week 1)
- [ ] Configure GitHub MCP server
- [ ] Create MCP client wrapper in Python
- [ ] Test basic GitHub operations via MCP
- [ ] Replace GitHubAgentClient with MCP calls

### Phase 2: Agentic AI Controller (Week 2)
- [ ] Build AgenticAI class with Gemini
- [ ] Implement tool-use framework
- [ ] Add reasoning trace logging
- [ ] Create agent prompt templates

### Phase 3: Pipeline Refactor (Week 3)
- [ ] Convert each step to agent-driven
- [ ] Add autonomous decision points
- [ ] Implement error recovery
- [ ] Add confidence scoring

### Phase 4: Testing & Optimization (Week 4)
- [ ] End-to-end testing with real profiles
- [ ] Performance optimization
- [ ] Cost analysis (API calls)
- [ ] Documentation

## Example: Real Agent Flow

```
User uploads resume + GitHub username "john-doe"

[Agent starts]
→ "I need to analyze john-doe's GitHub profile"
→ Tool: search_repositories(user="john-doe")
→ Observes: 12 repositories found
→ "Most relevant repos: portfolio-app, api-server, ml-pipeline"

→ "Let me examine portfolio-app"
→ Tool: get_file_contents(repo="portfolio-app", path="package.json")
→ Observes: React 18, TypeScript, Next.js, Tailwind
→ "This shows strong frontend skills"

→ Tool: search_code(repo="portfolio-app", query="useState")
→ Observes: 24 matches across 8 components
→ "Confirmed: experienced with React hooks"

→ "Now checking backend experience"
→ Tool: get_file_contents(repo="api-server", path="main.py")
→ Observes: FastAPI, SQLAlchemy, Pydantic
→ "Backend skills: Python, FastAPI, SQL"

[Agent cross-references with resume]
→ "Resume claims: React, Python, SQL, Docker"
→ "GitHub evidence: ✓ React ✓ Python ✓ SQL ✗ Docker"
→ "Classification: Docker is MISSING - should recommend"

[Agent generates recommendations]
→ "Candidate strong in frontend, weak in DevOps"
→ "Recommended project: Containerize existing apps with Docker + K8s"
→ "Roadmap: Week 1-2 Docker basics, Week 3-4 Kubernetes..."
```

## Next Steps

1. **Install GitHub MCP server**: `uvx mcp-server-github`
2. **Configure MCP** in `.kiro/mcp.json`
3. **Refactor OrchestrationService** to use Agentic AI pattern
4. **Replace microservice clients** with MCP tool calls
5. **Test with real GitHub profiles**

This architecture aligns with modern AI-native application patterns and leverages the full power of MCP!

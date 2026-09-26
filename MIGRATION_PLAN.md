# Career Navigator - Migration & Fix Plan

**Status**: ⚠️ Architectural audit complete - Two pipelines exist, frontend using wrong one  
**Date**: 2026-09-25  
**Auditor**: External code review  
**Priority**: 🔴 CRITICAL

---

## Executive Summary

The Career Navigator has **two parallel analysis pipelines**:

1. **Legacy `/api/analyze`** ← **Current frontend uses this** ❌
2. **Proper `/api/v1/analysis`** ← **Matches Lucidchart architecture** ✅

**The frontend must be migrated to use the proper orchestrated pipeline.**

---

## 🔍 Audit Findings

### ✅ What's Working

- FastAPI backend architecture
- React frontend UI components
- PostgreSQL database models
- Alembic migrations
- Supabase GitHub OAuth
- OrchestrationService (proper pipeline)
- Dedicated AI service clients (GitHub Agent, Resume Judge, etc.)
- LLM fallback system
- SSE progress streaming
- TypeScript compilation
- Python syntax

### ❌ Critical Issues

| # | Issue | Impact | Priority |
|---|-------|--------|----------|
| 1 | Frontend uses legacy `/api/analyze` | Wrong architecture in production | 🔴 CRITICAL |
| 2 | GitHub Intelligence not connected | No deep code analysis | 🔴 CRITICAL |
| 3 | O*NET/ESCO missing | No authoritative skill requirements | 🔴 HIGH |
| 4 | YouTube API missing | Hard-coded learning resources | 🔴 HIGH |
| 5 | Prerequisite engine missing | No learning sequence | 🟡 MEDIUM |
| 6 | Mock fallback returns fake data | Users can't distinguish failures | 🟡 MEDIUM |
| 7 | In-memory job store | Jobs lost on restart | 🟡 MEDIUM |
| 8 | Hard-coded roadmap resources | Not dynamic | 🟡 MEDIUM |
| 9 | LLM prompt needs enrichment | Missing confidence/evidence detail | 🟡 MEDIUM |
| 10 | Project recommender not integrated | Incomplete pipeline | 🟡 MEDIUM |

---

## 📐 Current vs. Intended Architecture

### Current (Wrong) - What Frontend Uses

```
React UploadPage
       ↓
POST /api/analyze
       ↓
_extract_text(resume)
       ↓
_fetch_github(username)  ← Direct GitHub API call
       ↓
LLMFallbackService
       ↓
Simple analysis: {claimed, evidenced, missing, roadmap}
       ↓
ProcessingPage (SSE)
       ↓
ResultsPage
```

**Problems:**
- No GitHub Intelligence module
- No Resume Judge module
- No Project Recommender
- No Roadmap Generator
- No O*NET/ESCO
- No prerequisites
- No YouTube API
- Basic LLM prompt only

---

### Intended (Correct) - What Should Happen

```
React UploadPage
       ↓
POST /api/v1/analysis
       ↓
OrchestrationService._execute_pipeline()
       ↓
┌──────────────────────────────────────┐
│ STEP 1: GitHub Intelligence          │
│   → GitHubAgentClient                 │
│   → Skills, projects, evidence        │
│   → Confidence scores                 │
└──────────────────────────────────────┘
       ↓
┌──────────────────────────────────────┐
│ STEP 2: Resume Analysis               │
│   → Extract text (PyPDF2)             │
│   → ResumeJudgeClient                 │
│   → Resume skills + evidence          │
└──────────────────────────────────────┘
       ↓
┌──────────────────────────────────────┐
│ STEP 3: Skill Gap Analysis            │
│   → GitHub + Resume + Job → Judge     │
│   → Verified / Partial / Missing      │
│   → Unsupported claims                │
│   → Evidence + Confidence             │
└──────────────────────────────────────┘
       ↓
┌──────────────────────────────────────┐
│ STEP 4: Project Recommendations       │
│   → ProjectRecommenderClient          │
│   → Skill-building projects           │
└──────────────────────────────────────┘
       ↓
┌──────────────────────────────────────┐
│ STEP 5: Learning Roadmap              │
│   → RoadmapGeneratorClient            │
│   → Sequenced learning path           │
│   → Prerequisites checked             │
│   → YouTube API resources             │
└──────────────────────────────────────┘
       ↓
ProcessingPage (SSE)
       ↓
ResultsPage (structured data)
```

---

## 🎯 Migration Plan

### Phase 1: Frontend Migration (Week 1)

**Goal**: Switch frontend from `/api/analyze` to `/api/v1/analysis`

#### 1.1 Update UploadPage.tsx

**Current**:
```typescript
POST /api/analyze
FormData: { resume, role, githubUsername, githubAccessToken }
Response: { jobId }
```

**Change to**:
```typescript
POST /api/v1/analysis
FormData: { 
  user_id: UUID,
  github_username: string,
  target_role: string,
  job_description: string,  ← NEW
  resume_file: File
}
Response: FullAnalysisRead
```

**Required Changes**:
- Add job description textarea to upload form
- Add user_id (get from auth context)
- Change endpoint URL
- Handle new response format

#### 1.2 Update ProcessingPage.tsx

**Current**:
```typescript
GET /api/analyze/{jobId}/stream  ← SSE
```

**Change to**:
```typescript
GET /api/v1/analysis/{analysis_id}  ← Polling
```

**Alternative**: Add SSE endpoint to v1 API

**Required Changes**:
- Poll status endpoint instead of SSE (or add SSE to v1)
- Handle new status enum: PENDING | PROCESSING | COMPLETED | FAILED
- Display orchestration steps (5 steps instead of 3)

#### 1.3 Update ResultsPage.tsx

**Current Structure**:
```typescript
{
  claimed: Skill[],
  evidenced: Skill[],
  missing: MissingSkill[],
  roadmap: RoadmapItem[],
  summary: string
}
```

**New Structure**:
```typescript
{
  analysis_id: UUID,
  status: AnalysisStatus,
  github_analysis: {...},
  resume_analysis: {...},
  skill_gap_analysis: {
    verified_skills: SkillDetail[],
    partial_skills: SkillDetail[],
    missing_skills: SkillDetail[],
    unsupported_claims: SkillDetail[]
  },
  project_recommendations: {...},
  roadmap: {...}
}
```

**Required Changes**:
- Update UI components to new data structure
- Add confidence scores display
- Add evidence display
- Show verified/partial/missing/unsupported breakdown

---

### Phase 2: Missing Components (Weeks 2-3)

#### 2.1 Implement O*NET Service

**File**: `backend/app/services/onet_service.py`

**Purpose**: Fetch authoritative skill requirements for target roles

**API**: https://services.onetcenter.org/ws/

**Required**:
```python
class ONetService:
    async def get_occupation_skills(
        self, 
        occupation_code: str
    ) -> List[Dict]:
        """
        Returns:
        [
          {
            "name": "Python Programming",
            "importance": 4.5,
            "level": 4.2,
            "category": "Technical Skills"
          }
        ]
        """
```

**Integration Point**: 
- `OrchestrationService._run_skill_analysis()`
- Add O*NET skills to comparison

#### 2.2 Implement ESCO Service

**File**: `backend/app/services/esco_service.py`

**Purpose**: European skill taxonomy for international coverage

**API**: https://ec.europa.eu/esco/api

**Integration**: Same as O*NET

#### 2.3 Implement Prerequisite Engine

**File**: `backend/app/services/prerequisite_service.py`

**Purpose**: Determine skill prerequisites and learning sequences

**Logic**:
```python
class PrerequisiteService:
    # Skill dependency graph
    PREREQUISITES = {
        "Machine Learning": ["Python", "Statistics", "Linear Algebra"],
        "React": ["JavaScript", "HTML", "CSS"],
        "Kubernetes": ["Docker", "Linux", "Networking"],
        # ...
    }
    
    def get_learning_sequence(
        self, 
        missing_skills: List[str],
        candidate_skills: List[str]
    ) -> List[Dict]:
        """
        Returns ordered learning path:
        [
          {"skill": "Linear Algebra", "reason": "Required for ML"},
          {"skill": "NumPy", "reason": "ML prerequisite"},
          {"skill": "Machine Learning", "reason": "Target skill"}
        ]
        """
```

**Integration Point**:
- `OrchestrationService._run_roadmap_generator()`
- Sort roadmap by prerequisites

#### 2.4 Implement YouTube API Service

**File**: `backend/app/services/youtube_service.py`

**Purpose**: Fetch real learning resources dynamically

**API**: YouTube Data API v3

**Required**:
```python
class YouTubeService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    async def search_tutorials(
        self,
        skill: str,
        max_results: int = 5
    ) -> List[Dict]:
        """
        Returns:
        [
          {
            "title": "Complete Python Tutorial",
            "channel": "Programming with Mosh",
            "url": "https://youtube.com/watch?v=...",
            "duration": "PT6H18M",
            "views": 12000000,
            "rating": 4.9
          }
        ]
        """
```

**Integration Point**:
- `RoadmapGeneratorClient` response
- Replace hard-coded resources in `RoadmapPage.tsx`

**Environment Variable**:
```env
YOUTUBE_API_KEY=your_key_from_google_cloud_console
```

---

### Phase 3: AI Service Implementations (Weeks 3-5)

#### 3.1 GitHub Intelligence Module

**Responsibility**: Deep repository analysis

**Current State**: Client exists, implementation missing

**What Needs Building**:

**File**: Separate service (e.g., `github-agent/main.py`)

**Port**: 8001

**Endpoint**: `POST /analyze`

**Input**:
```json
{
  "username": "octocat",
  "access_token": "ghp_..."
}
```

**Output**:
```json
{
  "skills": [
    {
      "name": "Python",
      "confidence": 0.92,
      "evidence": {
        "files": 145,
        "repos": 8,
        "commits": 234,
        "lines_of_code": 12500,
        "technologies": ["Flask", "FastAPI", "NumPy"],
        "patterns": ["REST APIs", "Async programming"]
      }
    }
  ],
  "projects": [
    {
      "name": "ml-api",
      "url": "https://github.com/octocat/ml-api",
      "description": "Machine learning REST API",
      "technologies": ["Python", "Flask", "scikit-learn"],
      "complexity": "medium",
      "impact": "high"
    }
  ],
  "summary": "Active Python developer with 8 ML-focused projects"
}
```

**Analysis Required**:
- Clone repositories (or use GitHub API tarball)
- Parse file extensions → languages
- Parse `requirements.txt`, `package.json` → dependencies
- Parse README → project descriptions
- Calculate metrics: commits, LOC, activity

**Tech Stack**:
- Language: Python
- Libraries: PyGithub, GitPython, tokei (for LOC counting)
- Caching: Redis for rate-limited API calls

#### 3.2 LLM Enhancements

**File**: `backend/app/services/llm_fallback_service.py`

**Current**: Basic skill categorization

**Needs**:

**Enhanced Prompt**:
```python
prompt = f"""
You are an expert technical recruiter.

INPUTS:
1. Resume: {resume_text}
2. GitHub Analysis: {github_json}
3. Target Role: {role}
4. Job Description: {job_description}
5. O*NET Required Skills: {onet_skills}

TASK:
Analyze the candidate against the role requirements.

For each skill:
- Classify: VERIFIED | PARTIAL | MISSING | UNSUPPORTED_CLAIM
- Confidence: 0.0-1.0
- Evidence: Specific examples from resume/GitHub
- Gap explanation: What's missing or weak

Return JSON:
{{
  "verified_skills": [
    {{
      "skill": "Python",
      "confidence": 0.95,
      "evidence": [
        "Resume: 5 years Python experience",
        "GitHub: 12 Python repos, 15k LOC",
        "Projects: Flask API, ML scripts"
      ],
      "match_quality": "strong"
    }}
  ],
  "partial_skills": [
    {{
      "skill": "Docker",
      "confidence": 0.40,
      "evidence": [
        "Resume: Mentioned once",
        "GitHub: 2 basic Dockerfiles"
      ],
      "gap": "No orchestration experience (K8s, Swarm)"
    }}
  ],
  "missing_skills": [
    {{
      "skill": "Kubernetes",
      "importance": "high",
      "reason": "Required for role but absent from resume/GitHub",
      "prerequisites": ["Docker", "Linux", "Networking"]
    }}
  ],
  "unsupported_claims": [
    {{
      "skill": "React",
      "claim": "Resume states 'Expert in React'",
      "issue": "No React repos found in GitHub",
      "severity": "high"
    }}
  ],
  "overall_fit": {{
    "score": 0.72,
    "summary": "Strong backend fundamentals...",
    "recommendation": "interview" | "upskill" | "not_matched"
  }}
}}
"""
```

**Changes to `analyze_with_fallback()`**:
- Add `onet_skills` parameter
- Add `job_description` parameter
- Expand prompt with structured requirements
- Parse richer response format

---

### Phase 4: Clean Up & Remove Legacy (Week 6)

#### 4.1 Deprecate `/api/analyze`

**Steps**:
1. Add deprecation warning to endpoint
2. Update docs to recommend `/api/v1/analysis`
3. After 1 month: Remove endpoint entirely
4. Delete `analyze.py` legacy code

#### 4.2 Fix Mock Fallback Behavior

**Current**:
```python
# Returns fake-looking but labeled "demo" data
return _mock_result(role)
```

**Change to**:
```python
if ALLOW_MOCK_FALLBACK:
    return _mock_result(role)
else:
    raise ServiceUnavailableError(
        "All LLM providers are currently unavailable. "
        "Please try again later."
    )
```

**Environment Variable**:
```env
ALLOW_MOCK_FALLBACK=false  # Production
ALLOW_MOCK_FALLBACK=true   # Development/demo
```

#### 4.3 Migrate Job Store to Database

**Current**: In-memory `_JOBS` dict

**Change**: Use PostgreSQL

**Already Exists**: `Analysis` model with `status` field

**Implementation**:
- Store SSE queues in Redis (not database)
- Store job status/progress in PostgreSQL
- Background task updates database

#### 4.4 Remove Hard-Coded Resources

**File**: `client/src/pages/RoadmapPage.tsx`

**Current**: 
```typescript
const RESOURCES = {
  docker: [...],
  react: [...],
  aws: [...]
}
```

**Change**: Fetch from backend
```typescript
useEffect(() => {
  fetch(`/api/v1/resources?skill=${skill}`)
    .then(res => res.json())
    .then(setResources)
}, [skill])
```

**Backend**: Return YouTube API results

---

## 📋 Implementation Checklist

### Priority 1: Critical (Do First)

- [ ] **Migrate frontend to `/api/v1/analysis`**
  - [ ] Add `job_description` field to upload form
  - [ ] Update API endpoint URL
  - [ ] Handle new response structure
  - [ ] Update ProcessingPage to poll v1 status
  - [ ] Update ResultsPage to new data format

- [ ] **Connect OrchestrationService to frontend**
  - [ ] Test full pipeline end-to-end
  - [ ] Verify all 5 steps execute
  - [ ] Confirm database persistence

- [ ] **Implement GitHub Intelligence module**
  - [ ] Create separate service on port 8001
  - [ ] Deep repository analysis
  - [ ] Return skills with confidence + evidence
  - [ ] Connect to GitHubAgentClient

### Priority 2: High (Do Second)

- [ ] **Implement O*NET integration**
  - [ ] Get API credentials
  - [ ] Create `onet_service.py`
  - [ ] Fetch occupation skill requirements
  - [ ] Add to skill gap analysis

- [ ] **Implement YouTube API**
  - [ ] Get YouTube Data API v3 key
  - [ ] Create `youtube_service.py`
  - [ ] Dynamic resource search
  - [ ] Replace hard-coded resources

- [ ] **Enhance LLM prompts**
  - [ ] Add O*NET requirements to prompt
  - [ ] Add confidence scoring
  - [ ] Add evidence extraction
  - [ ] Parse richer response format

### Priority 3: Medium (Do Third)

- [ ] **Implement ESCO service**
  - [ ] For international skill taxonomy
  - [ ] Supplement O*NET

- [ ] **Implement prerequisite engine**
  - [ ] Skill dependency graph
  - [ ] Learning sequence algorithm
  - [ ] Add to roadmap generation

- [ ] **Fix mock fallback behavior**
  - [ ] Add environment flag
  - [ ] Clear error messages
  - [ ] Distinguish demo from real

- [ ] **Migrate job store to database**
  - [ ] Remove in-memory `_JOBS`
  - [ ] Use PostgreSQL for persistence
  - [ ] Use Redis for SSE queues

### Priority 4: Cleanup (Do Last)

- [ ] **Remove legacy `/api/analyze`**
  - [ ] Deprecation warning first
  - [ ] Remove after migration complete

- [ ] **Remove hard-coded resources**
  - [ ] From `RoadmapPage.tsx`
  - [ ] Use backend YouTube API

- [ ] **Complete testing**
  - [ ] Full end-to-end tests
  - [ ] All AI services working
  - [ ] Database migrations tested
  - [ ] Error handling verified

---

## 🚀 Getting Started

### For Frontend Developer

Start here:
1. Read `backend/app/api/v1/analysis.py`
2. Understand new request/response format
3. Update `UploadPage.tsx` to use v1 endpoint
4. Test with mock AI services first

### For Backend Developer (LLM & GitHub)

Start here:
1. Read `backend/app/services/orchestration_service.py`
2. Understand the 5-step pipeline
3. Implement GitHub Intelligence service (port 8001)
4. Enhance LLM prompts in `llm_fallback_service.py`
5. Integrate O*NET API

### For DevOps

1. Set up 4 AI service ports (8001-8004)
2. Add environment variables for O*NET, YouTube, ESCO
3. Configure Redis for SSE queues
4. Database migration scripts

---

## 🎓 Key Takeaways

1. **The architecture exists** - OrchestrationService is already built
2. **Frontend just needs rewiring** - Use v1 API instead of legacy
3. **AI services need implementation** - Clients exist, services don't
4. **Missing pieces are known** - O*NET, YouTube, prerequisites
5. **Don't rewrite from scratch** - Modify existing structure

---

## 📚 Reference Documents

- `TECHNICAL_ARCHITECTURE.md` - Current system explanation
- `backend/app/services/orchestration_service.py` - Proper pipeline
- `backend/app/api/v1/analysis.py` - Correct endpoints
- Original Lucidchart - Intended workflow

---

**Next Action**: Assign tasks from Priority 1 checklist to team members.

**Timeline**: 6 weeks for complete migration + new features.

**Success Metric**: Frontend uses v1 API with all 5 pipeline steps working.

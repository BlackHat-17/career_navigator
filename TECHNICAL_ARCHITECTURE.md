# Career Navigator - Technical Architecture & Workflow

Complete technical documentation of the GitHub Repository Analyzer system, covering architecture, data flow, modules, APIs, and implementation details.

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Module Breakdown](#module-breakdown)
4. [Data Flow & Pipeline](#data-flow--pipeline)
5. [API Specifications](#api-specifications)
6. [Input/Output Formats](#inputoutput-formats)
7. [Step-by-Step Workflow](#step-by-step-workflow)
8. [Error Handling & Fallbacks](#error-handling--fallbacks)
9. [Performance & Scaling](#performance--scaling)

---

## 1. System Overview

### **What It Does**
Career Navigator analyzes a candidate's **resume** and **GitHub activity** against a target job role, identifying:
- **Claimed skills** (on resume but not evidenced in code)
- **Evidenced skills** (proven through GitHub repos)
- **Missing skills** (required for role but absent)
- **Learning roadmap** (actionable steps to close gaps)

### **Core Technologies**
- **Backend**: FastAPI (Python 3.11+), PostgreSQL, Docker
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS
- **AI Providers**: Google Gemini, xAI Grok, NVIDIA API, Ollama (local)
- **Real-time**: Server-Sent Events (SSE) for progress streaming
- **Authentication**: Supabase (GitHub OAuth)

---

## 2. Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                           CLIENT (React)                              │
│  ┌────────────┐    ┌────────────┐    ┌─────────────┐                │
│  │ UploadPage │───▶│ProcessingPage│◀──│ ResultsPage │                │
│  └────────────┘    └────────────┘    └─────────────┘                │
│         │                 │                                           │
│         │ POST /analyze   │ SSE /stream                              │
└─────────┼─────────────────┼───────────────────────────────────────────┘
          │                 │
          ▼                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                                │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              API Router (analyze.py)                         │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │   │
│  │  │ POST        │  │ GET          │  │ GET          │       │   │
│  │  │ /analyze    │  │ /stream      │  │ /status      │       │   │
│  │  └─────────────┘  └──────────────┘  └──────────────┘       │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                        │
│  ┌──────────────────────────┼────────────────────────────────────┐  │
│  │         Pipeline (_run_pipeline)                               │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────────┐    │  │
│  │  │ Step 1   │─▶│ Step 2   │─▶│ Step 3                   │    │  │
│  │  │ Extract  │  │ GitHub   │  │ LLM Analysis             │    │  │
│  │  │ Resume   │  │ Fetch    │  │ (Multi-provider)         │    │  │
│  │  └──────────┘  └──────────┘  └──────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                        │
│  ┌──────────────────────────┼────────────────────────────────────┐  │
│  │    LLM Fallback Service (llm_fallback_service.py)             │  │
│  │  ┌──────────┐  ┌──────┐  ┌────────┐  ┌────────┐  ┌──────┐   │  │
│  │  │ Gemini   │─▶│ Grok │─▶│ NVIDIA │─▶│ Ollama │─▶│ Mock │   │  │
│  │  │ 3.7/3.5/8│  │ Beta │  │ Llama  │  │ Local  │  │ Data │   │  │
│  │  └──────────┘  └──────┘  └────────┘  └────────┘  └──────┘   │  │
│  └───────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │  External APIs    │
                    ├───────────────────┤
                    │ • GitHub API      │
                    │ • Google Gemini   │
                    │ • xAI Grok        │
                    │ • NVIDIA API      │
                    │ • Ollama (local)  │
                    └───────────────────┘
```

---

## 3. Module Breakdown

### **3.1 Frontend Modules**

#### **UploadPage.tsx**
**Purpose**: Initial file upload and configuration  
**Responsibilities**:
- Resume file upload (PDF/DOCX/TXT)
- GitHub OAuth connection via Supabase
- Target role selection
- Form validation and submission

**Key Functions**:
```typescript
handleSubmit(): Promise<void>
  ├─ Validates file and role
  ├─ Creates FormData with: resume, role, githubUsername, githubAccessToken
  ├─ POST /api/analyze
  ├─ Receives { jobId }
  └─ Navigates to /processing/{jobId}
```

**Outputs**:
- `jobId`: UUID for tracking the analysis job

---

#### **ProcessingPage.tsx**
**Purpose**: Real-time progress visualization  
**Responsibilities**:
- Establish SSE connection to `/api/analyze/{jobId}/stream`
- Display progress steps (Extract → GitHub → Analyze)
- Show live terminal logs
- Handle errors and completion

**Key States**:
```typescript
step: number          // Current pipeline step (0-3)
log: LogLine[]        // Terminal output history
complete: boolean     // Analysis finished
failed: string        // Error message (if any)
initializing: boolean // Initial loading state
```

**SSE Event Types**:
```typescript
{ type: "step", step: number, message: string }   // Progress update
{ type: "done", result: AnalysisResult }          // Success
{ type: "error", message: string }                // Failure
```

---

#### **ResultsPage.tsx**
**Purpose**: Display analysis results  
**Responsibilities**:
- Render skill gap analysis
- Show claimed/evidenced/missing skills
- Display learning roadmap
- Export/download functionality

---

### **3.2 Backend Modules**

#### **analyze.py** (API Router)
**Purpose**: HTTP endpoints for analysis workflow  

**Endpoints**:

1. **POST /api/analyze**
   - **Input**: `FormData { resume: File, role: string, githubUsername?: string, githubAccessToken?: string }`
   - **Output**: `{ jobId: string }`
   - **Function**: Creates job, starts background pipeline
   
2. **GET /api/analyze/{jobId}/stream**
   - **Input**: `jobId` (path parameter)
   - **Output**: SSE stream of progress events
   - **Function**: Real-time progress updates
   
3. **GET /api/analyze/{jobId}/status**
   - **Input**: `jobId` (path parameter)
   - **Output**: `{ status, progress, result, error }`
   - **Function**: Polling fallback for SSE

**Internal Data Store**:
```python
_JOBS: Dict[str, Dict[str, Any]] = {
    "job-uuid": {
        "status": "running" | "done" | "error",
        "progress": [{ type, step, message }],
        "result": AnalysisResult | None,
        "error": str | None,
        "queues": [asyncio.Queue, ...]  # SSE clients
    }
}
```

---

#### **llm_fallback_service.py** (LLM Service)
**Purpose**: Unified LLM provider interface with fallbacks

**Class**: `LLMFallbackService`

**Methods**:

1. **`analyze_with_fallback(resume_text, github_summary, role, progress_callback)`**
   - **Input**: Resume text, GitHub summary, target role
   - **Output**: `AnalysisResult` dict
   - **Logic**: Tries providers in order until success

2. **`_try_gemini_models(prompt, callback)`**
   - Tries: `gemini-3.7-flash` → `gemini-3.5-flash` → `gemini-3.8-flash`
   - Returns: `Dict[str, Any]` or `None`

3. **`_try_grok(prompt, callback)`**
   - Endpoint: `https://api.x.ai/v1/chat/completions`
   - Model: `grok-beta`

4. **`_try_nvidia(prompt, callback)`**
   - Endpoint: `https://integrate.api.nvidia.com/v1/chat/completions`
   - Model: `meta/llama-3.1-70b-instruct`

5. **`_try_ollama(prompt, callback)`**
   - Endpoint: `http://localhost:11434/api/generate`
   - Model: `qwen2.5:3b` (configurable)

**Fallback Priority**:
```
Gemini 3.7 → Gemini 3.5 → Gemini 3.8 → Grok → NVIDIA → Ollama → Mock
```

---

### **3.3 Helper Functions**

#### **_extract_text(file_bytes)**
**Purpose**: Extract text from uploaded resume  
**Input**: `bytes` (file content)  
**Output**: `str` (plain text)  
**Logic**:
1. Try PyPDF2 for PDF extraction
2. Fallback to UTF-8 decode for text files
3. Returns extracted text (max ~10 MB)

---

#### **_fetch_github(username, access_token)**
**Purpose**: Fetch user's GitHub repositories  
**Input**: GitHub username, optional OAuth token  
**Output**: `str` (formatted repo summary)  

**API Call**:
```python
GET https://api.github.com/users/{username}/repos
Query: { sort: "updated", per_page: 20 }
Headers: { Authorization: "Bearer {token}" }
```

**Authorization Priority**:
1. **User's OAuth token** (from Supabase) - best, can access private repos
2. **Server GITHUB_TOKEN** - env var, 5,000 req/hour
3. **No auth** - 60 req/hour, public repos only

**Output Format**:
```
repo-name (Python): Repository description
another-repo (JavaScript): Another description
...
```

**Error Handling**:
- 404 → Raises `GitHubUserNotFoundError`
- 403 → Rate limited, returns empty string
- Other errors → Logs warning, returns empty string

---

## 4. Data Flow & Pipeline

### **Complete Request Flow**

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. USER UPLOADS RESUME                                              │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. CLIENT (UploadPage)                                              │
│    • Validates file (PDF/DOCX/TXT, <10MB)                           │
│    • Validates role selection                                       │
│    • Creates FormData with resume + metadata                        │
│    • POST /api/analyze                                              │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. BACKEND (start_analysis)                                         │
│    • Generates UUID (jobId)                                         │
│    • Reads file bytes                                               │
│    • Creates job entry in _JOBS dict                                │
│    • Spawns background task: _run_pipeline()                        │
│    • Returns { jobId } immediately (< 100ms)                        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. CLIENT (ProcessingPage)                                          │
│    • Navigates to /processing/{jobId}                               │
│    • Opens SSE connection: GET /stream                              │
│    • Displays loading screen ("Initializing AI...")                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. BACKEND (_run_pipeline) - STEP 1: EXTRACT RESUME                │
│    • Emits: { type: "step", step: 1, message: "Extracting..." }    │
│    • Calls: _extract_text(file_bytes)                               │
│    • Uses PyPDF2 for PDF, UTF-8 decode for text                    │
│    • Extracts ~5,000-10,000 characters                              │
│    • Emits: { type: "step", step: 1, message: "Extracted 8542 chars" }│
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 6. BACKEND (_run_pipeline) - STEP 2: GITHUB FETCH                  │
│    • Emits: { type: "step", step: 2, message: "Fetching repos..." }│
│    • Calls: _fetch_github(username, token)                          │
│    • Makes API call: GET /users/{username}/repos                    │
│    • Formats: "repo-name (lang): description\n..."                  │
│    • Emits: { type: "step", step: 2, message: "Found 12 repos" }   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 7. BACKEND (_run_pipeline) - STEP 3: LLM ANALYSIS                  │
│    • Emits: { type: "step", step: 3, message: "Running AI..." }    │
│    • Instantiates: LLMFallbackService()                             │
│    • Calls: analyze_with_fallback(resume, github, role)             │
│    • Builds prompt with resume + GitHub + role                      │
│    • Tries Gemini 3.7 Flash first                                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 8. LLM SERVICE (Gemini Attempt)                                     │
│    • POST https://generativelanguage.googleapis.com/...             │
│    • Payload: { model, contents, config }                           │
│    • Temperature: 0.3 (deterministic)                               │
│    • Response format: application/json                              │
│    • Success? Return parsed JSON                                    │
│    • Failure (503)? Try Gemini 3.5 Flash                           │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 9. LLM SERVICE (Fallback Chain)                                     │
│    • If all Gemini fails → Try Grok                                 │
│    • If Grok fails → Try NVIDIA                                     │
│    • If NVIDIA fails → Try Ollama (local)                           │
│    • If all fail → Return mock result                               │
│    • Emits progress: "Trying Grok...", "Trying NVIDIA...", etc.    │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 10. BACKEND (Pipeline Complete)                                     │
│    • Receives: AnalysisResult dict                                  │
│    • Stores: job["result"] = result                                 │
│    • Updates: job["status"] = "done"                                │
│    • Emits: { type: "done", result: {...} }                         │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 11. CLIENT (ProcessingPage Receives Done Event)                     │
│    • Parses result from SSE stream                                  │
│    • Shows completion animation                                     │
│    • Waits 1.4 seconds                                              │
│    • Navigates: /results/{jobId}                                    │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 12. CLIENT (ResultsPage)                                            │
│    • Displays analysis results                                      │
│    • Renders: claimed, evidenced, missing, roadmap                  │
│    • Shows summary and recommendations                              │
│    • Offers: download, share, start new analysis                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. API Specifications

### **POST /api/analyze**

**Request**:
```http
POST /api/analyze HTTP/1.1
Content-Type: multipart/form-data

resume: <File: PDF/DOCX/TXT>
role: "Backend Engineer"
githubUsername: "octocat"
githubAccessToken: "gho_..."
```

**Response**:
```json
{
  "jobId": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Status Codes**:
- `200 OK` - Job created successfully
- `400 Bad Request` - Invalid file or missing role
- `413 Payload Too Large` - File exceeds 10MB

---

### **GET /api/analyze/{jobId}/stream**

**Request**:
```http
GET /api/analyze/550e8400-e29b-41d4-a716-446655440000/stream HTTP/1.1
Accept: text/event-stream
```

**Response** (Server-Sent Events):
```
data: {"type":"step","step":1,"message":"Extracting resume text…"}

data: {"type":"step","step":1,"message":"Resume extracted (8542 chars)"}

data: {"type":"step","step":2,"message":"Fetching GitHub repos for @octocat…"}

data: {"type":"step","step":2,"message":"Found 12 repos"}

data: {"type":"step","step":3,"message":"Running AI skill gap analysis…"}

data: {"type":"step","step":3,"message":"Using Gemini 3.7 Flash..."}

data: {"type":"done","result":{"claimed":[...],"evidenced":[...],"missing":[...],"roadmap":[...],"summary":"..."}}
```

**Event Types**:
- `step` - Progress update
- `done` - Analysis complete (includes result)
- `error` - Pipeline failed (includes message)

---

### **GET /api/analyze/{jobId}/status**

**Request**:
```http
GET /api/analyze/550e8400-e29b-41d4-a716-446655440000/status HTTP/1.1
```

**Response**:
```json
{
  "status": "running",
  "progress": [
    {"type":"step","step":1,"message":"Extracting resume text…"},
    {"type":"step","step":2,"message":"Fetching GitHub repos..."}
  ],
  "result": null,
  "error": null
}
```

**Status Values**:
- `queued` - Job created, not started
- `running` - Pipeline executing
- `done` - Completed successfully
- `error` - Failed with error

---

## 6. Input/Output Formats

### **6.1 Input Formats**

#### **Resume File**
```
Format: PDF, DOCX, TXT
Max Size: 10 MB
Encoding: UTF-8
Content: Text-based (no scanned images)
```

#### **GitHub Username**
```
Type: string
Format: GitHub handle (e.g., "octocat")
Optional: Yes (analysis works without GitHub)
Validation: Must exist on GitHub (404 check)
```

#### **Target Role**
```
Type: string
Examples: "Backend Engineer", "Full-Stack Engineer", "DevOps Engineer"
Min Length: 3 characters
Max Length: 100 characters
```

---

### **6.2 Output Formats**

#### **AnalysisResult**
```typescript
interface AnalysisResult {
  summary: string;                    // 2-3 sentence overall assessment
  claimed: Skill[];                   // Skills on resume, not in GitHub
  evidenced: Skill[];                 // Skills proven through GitHub
  missing: MissingSkill[];            // Required skills absent
  roadmap: RoadmapItem[];             // Learning steps (3-5 items)
}

interface Skill {
  skill: string;                      // Skill name (e.g., "Python")
  evidence: string;                   // Evidence description
}

interface MissingSkill {
  skill: string;                      // Skill name
  why: string;                        // Why it's important
}

interface RoadmapItem {
  title: string;                      // Action title
  description: string;                // Detailed steps
  priority: "high" | "medium" | "low";
}
```

#### **Example Output**:
```json
{
  "summary": "Strong backend fundamentals with Python and FastAPI, but Backend Engineer requires more DevOps experience. Focus on containerization orchestration and automated deployment pipelines.",
  
  "claimed": [
    {
      "skill": "Python",
      "evidence": "Listed in resume under 'Programming Languages' but no corresponding GitHub repos found"
    }
  ],
  
  "evidenced": [
    {
      "skill": "FastAPI",
      "evidence": "3 repositories with FastAPI implementations, including REST APIs and async patterns"
    },
    {
      "skill": "Docker",
      "evidence": "Dockerfiles present in 5 repos with multi-stage builds"
    }
  ],
  
  "missing": [
    {
      "skill": "Kubernetes",
      "why": "Essential for Backend Engineer but absent from resume and GitHub activity"
    }
  ],
  
  "roadmap": [
    {
      "title": "Build a microservices project with K8s",
      "description": "Deploy 3-4 containerized services on Kubernetes with Helm charts",
      "priority": "high"
    },
    {
      "title": "Set up CI/CD pipeline",
      "description": "Create GitHub Actions workflows for testing, building, and deployment",
      "priority": "high"
    }
  ]
}
```

---

## 7. Step-by-Step Workflow

### **STEP 1: Resume Text Extraction**

**Function**: `_extract_text(file_bytes: bytes) -> str`

**Input**: Raw file bytes (PDF, DOCX, or TXT)

**Process**:
1. Detect file type from bytes
2. If PDF:
   - Use PyPDF2.PdfReader
   - Extract text from each page
   - Concatenate with newlines
3. If text:
   - Decode as UTF-8
   - Replace invalid characters
4. Return plain text

**Output**: String (5,000-10,000 characters typical)

**Example Output**:
```
John Doe
Software Engineer
john.doe@email.com | github.com/johndoe

EXPERIENCE
Senior Backend Engineer, TechCorp (2020-2023)
- Built REST APIs with Python/FastAPI
- Deployed microservices on AWS ECS
...
```

**Error Handling**:
- PDF read failure → Fallback to UTF-8 decode
- Encoding errors → Replace with '?' placeholder
- Empty file → Return empty string

**Duration**: ~100-500ms

---

### **STEP 2: GitHub Repository Fetch**

**Function**: `_fetch_github(username: str, access_token: str) -> str`

**Input**: 
- `username`: GitHub handle (e.g., "octocat")
- `access_token`: OAuth token (optional)

**Process**:
1. Determine auth strategy:
   - Use OAuth token if provided (best)
   - Fallback to GITHUB_TOKEN env var
   - Fallback to unauthenticated
   
2. Make API request:
   ```
   GET https://api.github.com/users/{username}/repos
   ?sort=updated&per_page=20
   ```

3. Parse response:
   - Extract: name, language, description
   - Format: "repo-name (language): description"
   - Join with newlines

4. Return formatted summary

**Output**: String with repo list

**Example Output**:
```
career-navigator (Python): AI-powered skill gap analyzer
personal-website (TypeScript): Portfolio site built with Next.js
python-scripts (Python): Collection of utility scripts
docker-demo (Shell): Docker and Kubernetes examples
...
```

**Error Handling**:
- 404 → Raise `GitHubUserNotFoundError`
- 403 → Rate limited, return empty string
- Network error → Log warning, return empty string
- No repos → Return empty string

**Rate Limits**:
- OAuth token: 5,000 req/hour
- Server token: 5,000 req/hour
- Unauthenticated: 60 req/hour

**Duration**: ~500-2,000ms

---

### **STEP 3: LLM Skill Gap Analysis**

**Function**: `LLMFallbackService.analyze_with_fallback(...)`

**Inputs**:
- `resume_text`: Extracted resume (string)
- `github_summary`: Formatted repo list (string)
- `role`: Target job title (string)

**Process**:

#### 3.1 Build Prompt
```python
prompt = f"""
You are an expert technical recruiter.
Analyze the candidate against the target role.

Return JSON with:
- claimed: skills on resume, not in GitHub
- evidenced: skills proven through GitHub
- missing: required skills absent
- roadmap: 3-5 learning steps
- summary: 2-sentence assessment

Target role: {role}

--- RESUME ---
{resume_text[:6000]}

--- GITHUB REPOS ---
{github_summary}
"""
```

#### 3.2 Try Gemini Models (Priority 1)
```python
for model in ["gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.8-flash"]:
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={ temperature: 0.3, response_mime_type: "application/json" }
        )
        return json.loads(response.text)
    except 503_UNAVAILABLE:
        continue  # Try next model
    except json.JSONDecodeError:
        continue  # Try next model
```

#### 3.3 Try Grok (Priority 2)
```python
if GROK_ENABLED:
    response = httpx.post(
        "https://api.x.ai/v1/chat/completions",
        headers={ "Authorization": f"Bearer {GROK_API_KEY}" },
        json={
            "model": "grok-beta",
            "messages": [
                {"role": "system", "content": "You are an expert recruiter..."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }
    )
    return json.loads(response.json()["choices"][0]["message"]["content"])
```

#### 3.4 Try NVIDIA (Priority 3)
```python
if NVIDIA_ENABLED:
    response = httpx.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        headers={ "Authorization": f"Bearer {NVIDIA_API_KEY}" },
        json={
            "model": "meta/llama-3.1-70b-instruct",
            "messages": [...],
            "temperature": 0.3,
            "max_tokens": 2048
        }
    )
    return json.loads(response.json()["choices"][0]["message"]["content"])
```

#### 3.5 Try Ollama (Priority 4)
```python
if OLLAMA_ENABLED:
    response = httpx.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "qwen2.5:3b",
            "prompt": prompt,
            "stream": false,
            "format": "json",
            "options": {"temperature": 0.3, "num_predict": 2000}
        }
    )
    return json.loads(response.json()["response"])
```

#### 3.6 Mock Fallback (Priority 5)
```python
# If all providers fail, return realistic demo data
return _mock_result(role)
```

**Output**: AnalysisResult dict (see section 6.2)

**Duration**: 
- Gemini: 2-5 seconds
- Grok: 3-7 seconds
- NVIDIA: 4-8 seconds
- Ollama (3B): 5-10 seconds (CPU)
- Ollama (3B): 1-3 seconds (GPU)
- Mock: <100ms

**Error Handling**:
- 503/Unavailable → Try next model
- JSON parse error → Try next model
- All providers fail → Return mock result
- Network timeout → Try next provider

---

## 8. Error Handling & Fallbacks

### **8.1 GitHub Fetch Errors**

| Error | Code | Handling | User Impact |
|-------|------|----------|-------------|
| User not found | 404 | Raise `GitHubUserNotFoundError` | Shows error: "GitHub username 'xyz' does not exist" |
| Rate limited | 403 | Return empty string, log warning | Analysis continues without GitHub data |
| Network error | N/A | Catch, log, return empty | Analysis continues without GitHub data |
| Timeout | N/A | Catch after 10s, return empty | Analysis continues without GitHub data |

### **8.2 LLM Provider Errors**

| Provider | Error | Retry? | Fallback To |
|----------|-------|--------|-------------|
| Gemini 3.7 | 503 Unavailable | Yes | Gemini 3.5 |
| Gemini 3.5 | 503 Unavailable | Yes | Gemini 3.8 |
| Gemini 3.8 | 503 Unavailable | No | Grok |
| Grok | 500 Server Error | No | NVIDIA |
| NVIDIA | 429 Quota Exceeded | No | Ollama |
| Ollama | Connection Refused | No | Mock Data |

### **8.3 Resume Extraction Errors**

| Error | Handling |
|-------|----------|
| PDF corruption | Fallback to UTF-8 decode |
| Encoding error | Replace invalid chars with '?' |
| Empty file | Return empty string, LLM handles |
| File too large | Truncate to 6,000 chars for LLM |

---

## 9. Performance & Scaling

### **9.1 Performance Metrics**

| Operation | Duration | Bottleneck |
|-----------|----------|------------|
| Resume upload | 50-200ms | Network bandwidth |
| PDF extraction | 100-500ms | PyPDF2 processing |
| GitHub fetch | 500-2,000ms | GitHub API latency |
| Gemini API call | 2,000-5,000ms | LLM inference |
| Grok API call | 3,000-7,000ms | LLM inference |
| NVIDIA API call | 4,000-8,000ms | LLM inference |
| Ollama (CPU) | 5,000-10,000ms | Local CPU |
| Ollama (GPU) | 1,000-3,000ms | Local GPU |
| Total (success) | 5-15 seconds | LLM inference |

### **9.2 Concurrent Request Handling**

**In-Memory Job Store**:
- Jobs stored in Python dict: `_JOBS`
- Each job tracks progress, result, error
- SSE clients connect via asyncio queues
- No persistence (jobs lost on restart)

**Limitations**:
- Single process: ~100-500 concurrent analyses
- Memory: ~10 MB per job (resume + GitHub data)
- Recommended: 50 concurrent jobs max per instance

**Scaling Strategy**:
- **Horizontal**: Deploy multiple backend instances
- **Job Queue**: Move to Redis/RabbitMQ for persistence
- **Worker Pool**: Separate analysis workers
- **Database**: Store jobs in PostgreSQL

### **9.3 Caching Opportunities**

| Data | Cache Duration | Storage |
|------|----------------|---------|
| GitHub repos | 1 hour | Redis |
| LLM responses | N/A (never cache - unique) | - |
| Resume text | Job lifetime (20 min) | In-memory |
| User sessions | 1 week | Supabase |

---

## 10. Security Considerations

### **10.1 Data Privacy**

- **Resume data**: Processed in-memory, never persisted
- **GitHub tokens**: Not logged, only used for API calls
- **LLM prompts**: Resume text sent to 3rd party APIs (Gemini, Grok, NVIDIA)
- **Local Ollama**: Keeps data completely offline

### **10.2 Rate Limiting**

| Endpoint | Limit | Strategy |
|----------|-------|----------|
| POST /analyze | 10/min per IP | FastAPI rate limiter |
| GET /stream | 1 per job | Single SSE connection |
| GitHub API | Handled by token | Uses user's OAuth token |

### **10.3 Input Validation**

- File size: Max 10 MB
- File type: Only PDF, DOCX, TXT
- Role length: Max 100 chars
- GitHub username: Validated via API

---

## Summary

The Career Navigator uses a **3-stage pipeline** (Extract → GitHub → LLM) with **5-tier fallback** for LLM providers, ensuring analysis always completes. Real-time progress is streamed via **SSE**, and the entire system is designed for **low latency** (5-15 seconds end-to-end) with **graceful degradation** at every layer.

**Key Design Principles**:
1. **Asynchronous processing** - Background tasks, non-blocking I/O
2. **Progressive enhancement** - Works without GitHub, degrades with mock data
3. **Multi-provider redundancy** - 5 LLM options ensure reliability
4. **Real-time feedback** - SSE streaming keeps users informed
5. **Privacy-first** - In-memory processing, no resume persistence

---

**Document Version**: 1.0  
**Last Updated**: 2026-09-25  
**Maintained By**: Career Navigator Team

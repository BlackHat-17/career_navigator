# Career Navigator

Evidence-Based Skill & Career Navigator — full-stack app with a React frontend, a FastAPI backend, and four pluggable AI modules built by separate teammates.

---

## Architecture

```
React client  (client/  · port 3000)
      │
      │  /api/*  (proxied)
      ▼
FastAPI backend  (backend/  · port 8000)
      │
      ├── POST /api/analyze          ← SSE pipeline (resume + GitHub + Gemini)
      │
      └── /api/v1/...                ← structured REST API
            │
            ├── GitHub Agent         → http://localhost:8001
            ├── Resume Judge         → http://localhost:8002
            ├── Project Recommender  → http://localhost:8003
            └── Roadmap Generator    → http://localhost:8004
                      │
                      ▼
                PostgreSQL  (port 5432)
```

The four AI modules are **independent services** — their URLs are configured via environment variables. The backend only knows their HTTP contracts, not their internal logic.

---

## Folder structure

```
career_navigator/
├── client/                   React + Vite + Tailwind frontend
│   ├── src/
│   │   ├── pages/            UploadPage, ProcessingPage, ResultsPage, RoadmapPage
│   │   ├── components/       PageTransition
│   │   └── types.ts
│   └── vite.config.ts        proxies /api → localhost:8000
│
├── backend/
│   ├── app/
│   │   ├── main.py           FastAPI app factory
│   │   ├── api/v1/           REST route handlers
│   │   │   ├── analyze.py    SSE pipeline (replaces Node server)
│   │   │   ├── users.py
│   │   │   ├── github.py
│   │   │   ├── resume.py
│   │   │   ├── jobs.py
│   │   │   ├── analysis.py
│   │   │   ├── projects.py
│   │   │   └── roadmap.py
│   │   ├── schemas/          Pydantic v2 request/response models
│   │   ├── models/           SQLAlchemy ORM models
│   │   ├── services/         Business logic + orchestration
│   │   ├── clients/          HTTP clients for each AI module
│   │   ├── core/             config, database, logging, exceptions
│   │   └── utils/            helpers
│   ├── alembic/              migrations
│   ├── tests/                pytest suite (all AI services mocked)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
│
├── docker-compose.yml        postgres + backend
└── package.json              workspace root (client only)
```

---

## Environment variables

Copy `backend/.env.example` to `backend/.env` and fill in your values.

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL async URL | `postgresql+asyncpg://postgres:password@localhost:5432/career_navigator` |
| `GEMINI_API_KEY` | Gemini 1.5 Flash key for real analysis — get one at [aistudio.google.com](https://aistudio.google.com/app/apikey) | — |
| `MOCK_MODE` | `true` = skip Gemini, return demo data | `false` |
| `GITHUB_AGENT_URL` | URL of GitHub Agent service | `http://localhost:8001` |
| `RESUME_JUDGE_URL` | URL of Resume Judge service | `http://localhost:8002` |
| `PROJECT_RECOMMENDER_URL` | URL of Project Recommender service | `http://localhost:8003` |
| `ROADMAP_GENERATOR_URL` | URL of Roadmap Generator service | `http://localhost:8004` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000` |
| `SECRET_KEY` | App secret | `change-me-in-production` |
| `ENVIRONMENT` | `development` or `production` | `development` |
| `MAX_UPLOAD_SIZE_MB` | Max resume file size | `10` |

---

## Running locally (without Docker)

### 1. PostgreSQL

```bash
# macOS
brew install postgresql@16 && brew services start postgresql@16

# or run a one-liner with Docker
docker run -d --name pg -e POSTGRES_PASSWORD=password -e POSTGRES_DB=career_navigator -p 5432:5432 postgres:16-alpine
```

### 2. Backend

```bash
cd backend

# Create and activate virtualenv
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt

# Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL, GEMINI_API_KEY, etc.

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --port 8000
```

API available at: http://localhost:8000  
Swagger UI: http://localhost:8000/docs  
ReDoc: http://localhost:8000/redoc

### 3. Frontend (client)

```bash
cd client
npm install
npm run dev
```

App available at: http://localhost:3000

---

## Running with Docker

```bash
# 1. Copy and configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your GEMINI_API_KEY

# 2. Start postgres + backend
docker compose up --build

# 3. Start frontend separately (it's not containerised)
cd client && npm install && npm run dev
```

Backend: http://localhost:8000  
Swagger: http://localhost:8000/docs  
Frontend: http://localhost:3000

> The four AI teammate services are **not** in docker-compose. They run on their own ports (8001–8004) and are reached via `host.docker.internal` from inside the container.

---

## API endpoints

### Legacy pipeline (used by the React client)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/analyze` | Upload resume + role → returns `{ jobId }` |
| `GET` | `/api/analyze/{jobId}/stream` | SSE live progress stream |
| `GET` | `/api/analyze/{jobId}/status` | Polling fallback for job status |

### Structured REST API (`/api/v1/`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/users` | Create user |
| `GET` | `/api/v1/users/{id}` | Get user |
| `POST` | `/api/v1/github/analyze` | GitHub profile analysis |
| `POST` | `/api/v1/resume/analyze` | Resume analysis (multipart) |
| `POST` | `/api/v1/jobs/analyze` | Store job description |
| `POST` | `/api/v1/analysis` | **Full orchestration pipeline** |
| `GET` | `/api/v1/analysis/{id}` | Get analysis status + result |
| `POST` | `/api/v1/analysis/skills` | Cross-reference skills |
| `POST` | `/api/v1/projects/recommend` | Project recommendations |
| `POST` | `/api/v1/roadmap/generate` | Generate learning roadmap |
| `GET` | `/api/v1/roadmap/{analysis_id}` | Get stored roadmap |
| `GET` | `/health` | Health check |

### Error response shape (all endpoints)

```json
{
  "success": false,
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "GitHub Agent is unavailable"
  }
}
```

---

## Example requests

### Start a full analysis (React client flow)

```bash
curl -X POST http://localhost:8000/api/analyze \
  -F "resume=@/path/to/resume.pdf" \
  -F "role=Backend Engineer" \
  -F "githubUsername=BlackHat-17"
# → { "jobId": "abc-123" }

# Stream progress
curl -N http://localhost:8000/api/analyze/abc-123/stream
```

### Create a user + run full structured pipeline

```bash
# 1. Create user
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Aditya","email":"aditya@example.com","career_goal":"Backend Developer"}'

# 2. Full pipeline (multipart)
curl -X POST http://localhost:8000/api/v1/analysis \
  -F "user_id=<uuid>" \
  -F "github_username=BlackHat-17" \
  -F "target_role=Backend Developer" \
  -F "job_description=We need a Python backend developer..." \
  -F "resume_file=@resume.pdf"
```

---

## Database setup

Migrations are managed by Alembic and run automatically on container start.

```bash
# Create a new migration after changing models
alembic revision --autogenerate -m "add new table"

# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1
```

---

## Connecting teammate AI services

Each teammate's service only needs to expose one HTTP endpoint:

### GitHub Agent — `http://localhost:8001`
```
POST /analyze
Body: { "github_username": "...", "repositories": [] }
Response: { "skills": [...], "projects": [...], "recommended_projects": [] }
```

### Resume Judge — `http://localhost:8002`
```
POST /analyze
Body: { "target_role": "...", "resume_text": "...", "job_description": "..." }
Response: { "claimed_skills": [...], "feedback": [...], "overall_score": 72.5 }

POST /skill-analysis
Body: { "github_output": {...}, "resume_output": {...}, "job_title": "...", "job_description": "..." }
Response: { "verified_skills": [...], "partial_skills": [...], "missing_skills": [...], "unsupported_claims": [...] }
```

### Project Recommender — `http://localhost:8003`
```
POST /recommend
Body: { "career_goal": "...", "verified_skills": [...], "skill_gaps": [...] }
Response: { "recommendations": [{ "title": "...", "skills": [...], "difficulty": "intermediate", "reason": "..." }] }
```

### Roadmap Generator — `http://localhost:8004`
```
POST /generate
Body: { "career_goal": "...", "current_skills": [...], "skill_gaps": [...], "recommended_projects": [...] }
Response: { "career_goal": "...", "total_weeks": 8, "summary": "...", "roadmap": [{ "week": 1, "topic": "...", ... }] }
```

Set each URL in `backend/.env`. If a service isn't running, the backend returns `503 SERVICE_UNAVAILABLE` gracefully.

---

## GitHub OAuth setup (Supabase)

The "Connect GitHub" button uses Supabase as the OAuth provider. Follow these steps once:

### 1. Create a Supabase project

Go to [supabase.com](https://supabase.com) → New project. Free tier is fine.

### 2. Enable GitHub OAuth provider

Supabase dashboard → Authentication → Providers → GitHub → Enable.

You need a GitHub OAuth App:
1. GitHub → Settings → Developer settings → OAuth Apps → New OAuth App
2. Set **Homepage URL** to `http://localhost:3000`
3. Set **Authorization callback URL** to:
   ```
   https://<your-project-ref>.supabase.co/auth/v1/callback
   ```
4. Copy the **Client ID** and **Client Secret** into Supabase → GitHub provider settings

### 3. Add the redirect URL

Supabase dashboard → Authentication → URL Configuration → Add to **Redirect URLs**:
```
http://localhost:3000/auth/callback
```
For production add your real domain too.

### 4. Set client env vars

Create `client/.env` (or `client/.env.local`):
```
VITE_SUPABASE_URL=https://your-project-ref.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```
Get both values from: Supabase dashboard → Settings → API.

### How it works

```
User clicks "Connect GitHub"
  → Supabase redirects to GitHub OAuth consent screen
  → User approves "read:user public_repo" access
  → GitHub redirects back to /auth/callback
  → Supabase exchanges code for session + provider_token
  → AuthCallbackPage detects SIGNED_IN event → navigates to /
  → UploadPage shows connected state with avatar + @username
  → On submit, githubUsername + githubAccessToken sent to backend
  → Backend uses the OAuth token to call GitHub API as the user
```

The OAuth token gives:
- No rate limit issues (authenticated = 5,000 req/h)
- Access to private repos (if user approves)
- Verified username — no manual typing, no typos

---

```bash
cd backend

# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests (no real DB or AI calls needed — all mocked)
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run a specific file
pytest tests/test_users.py -v
```

All four AI services are mocked via `unittest.mock`. Tests use an in-memory SQLite database so no PostgreSQL instance is required.

---

## Mock mode

Set `MOCK_MODE=true` in `.env` to skip all Gemini API calls and return realistic hardcoded demo results. Useful when:
- You don't have a Gemini API key yet
- You're demoing at the hackathon
- You're running tests without spending API credits

```bash
MOCK_MODE=true uvicorn app.main:app --reload --port 8000
```

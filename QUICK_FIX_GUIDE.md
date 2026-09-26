# Quick Fix Guide - Get v1 Pipeline Working

**Goal**: Make the frontend use the proper `/api/v1/analysis` orchestrated pipeline  
**Time**: 2-4 hours  
**Priority**: 🔴 CRITICAL - Do this first before anything else

---

## Why This Matters

Your frontend currently calls `/api/analyze` (simple pipeline) instead of `/api/v1/analysis` (proper orchestrated pipeline). This means:

❌ GitHub Intelligence module is not used  
❌ Resume Judge module is not used  
❌ Project Recommender is not used  
❌ Roadmap Generator is not used  
❌ OrchestrationService is not used  

Fixing this gets you from **30% architecture implementation** to **80%** implementation.

---

## Step 1: Update UploadPage Form (15 minutes)

**File**: `client/src/pages/UploadPage.tsx`

### Add Job Description Field

Find the role selection section and add after it:

```tsx
{/* ── Job Description ─────────────────────────────────────────── */}
<div>
  <label className="block text-xs font-semibold mb-2 tracking-widest uppercase"
    style={{ color: '#71717a' }}>
    Job Description
    <span className="normal-case font-normal tracking-normal text-zinc-500 ml-2">
      — paste the full job posting
    </span>
  </label>
  <textarea
    value={jobDescription}
    onChange={e => setJobDescription(e.target.value)}
    placeholder="Paste the full job description here..."
    rows={6}
    className="w-full px-4 py-3 text-sm text-white placeholder-zinc-700 focus:outline-none rounded-xl resize-none"
    style={{ 
      background: 'rgba(255,255,255,0.04)', 
      border: '1px solid rgba(255,255,255,0.08)' 
    }}
  />
  <p className="text-xs text-zinc-600 mt-1.5">
    Include requirements, qualifications, and responsibilities
  </p>
</div>
```

### Add State Variable

```tsx
const [jobDescription, setJobDescription] = useState('');
```

### Update Validation

```tsx
const handleSubmit = async () => {
  if (!file || !resolvedRole || !jobDescription) {
    setError('Please attach a resume, select a role, and provide job description.');
    return;
  }
  // ...
}
```

---

## Step 2: Change API Endpoint (10 minutes)

**File**: `client/src/pages/UploadPage.tsx`

### Current Code:
```tsx
const { data } = await axios.post<{ jobId: string }>('/api/analyze', form);
await new Promise(resolve => setTimeout(resolve, 500));
navigate(`/processing/${data.jobId}`);
```

### Change To:
```tsx
// Get user ID from auth context
const userId = user?.id; // or generate a UUID

const form = new FormData();
form.append('resume_file', file);
form.append('target_role', resolvedRole);
form.append('job_description', jobDescription);
form.append('user_id', userId || crypto.randomUUID());

if (githubLogin) {
  form.append('github_username', githubLogin);
}

// Call v1 endpoint
const { data } = await axios.post('/api/v1/analysis', form);

// v1 returns full analysis immediately (when AI services are ready)
// For now, store the analysis_id and poll for status
navigate(`/processing/${data.analysis_id}`);
```

---

## Step 3: Update ProcessingPage Polling (20 minutes)

**File**: `client/src/pages/ProcessingPage.tsx`

### Current: SSE Stream
```tsx
const es = new EventSource(`/api/analyze/${jobId}/stream`);
```

### Change To: Polling

```tsx
useEffect(() => {
  if (!jobId) return;
  
  let pollInterval: NodeJS.Timeout;
  
  const pollStatus = async () => {
    try {
      const { data } = await axios.get(`/api/v1/analysis/${jobId}`);
      
      // Update status based on response
      if (data.status === 'PROCESSING') {
        // Extract step from status (you'll need to enhance this)
        setLog(prev => [...prev, {
          id: counter.current++,
          message: 'Processing...',
          type: 'step',
          ts: ts()
        }]);
      } else if (data.status === 'COMPLETED') {
        setComplete(true);
        clearInterval(pollInterval);
        setTimeout(() => {
          navigate(`/results/${jobId}`, { 
            state: { result: data.result } 
          });
        }, 1400);
      } else if (data.status === 'FAILED') {
        setFailed(data.error_message || 'Analysis failed');
        clearInterval(pollInterval);
      }
    } catch (err) {
      setFailed('Failed to fetch analysis status');
      clearInterval(pollInterval);
    }
  };
  
  // Poll every 2 seconds
  pollInterval = setInterval(pollStatus, 2000);
  pollStatus(); // Initial call
  
  return () => clearInterval(pollInterval);
}, [jobId, navigate]);
```

**Note**: This is temporary. You can add SSE back to v1 API later.

---

## Step 4: Update ResultsPage Data Structure (30 minutes)

**File**: `client/src/pages/ResultsPage.tsx`

### Current Structure:
```typescript
{
  claimed: Skill[],
  evidenced: Skill[],
  missing: MissingSkill[],
  roadmap: RoadmapItem[]
}
```

### New Structure from v1:
```typescript
{
  analysis_id: string,
  status: string,
  github_analysis: {
    skills: Array<{
      name: string,
      confidence: number,
      evidence: {...}
    }>,
    projects: [...]
  },
  skill_gap_analysis: {
    verified_skills: Array<{
      skill: string,
      confidence: number,
      evidence: string[],
      match_quality: string
    }>,
    partial_skills: [...],
    missing_skills: [...],
    unsupported_claims: [...]
  },
  project_recommendations: {...},
  roadmap: {...}
}
```

### Quick Adapter Function:

Add this to ResultsPage to maintain compatibility:

```tsx
function adaptLegacyFormat(newData: any) {
  return {
    claimed: newData.skill_gap_analysis?.unsupported_claims?.map((s: any) => ({
      skill: s.skill,
      evidence: s.claim
    })) || [],
    
    evidenced: newData.skill_gap_analysis?.verified_skills?.map((s: any) => ({
      skill: s.skill,
      evidence: s.evidence?.join('; ') || ''
    })) || [],
    
    missing: newData.skill_gap_analysis?.missing_skills?.map((s: any) => ({
      skill: s.skill,
      why: s.reason || s.gap
    })) || [],
    
    roadmap: newData.roadmap?.items || [],
    
    summary: newData.skill_gap_analysis?.overall_fit?.summary || ''
  };
}

// Then use it:
const adaptedData = adaptLegacyFormat(result);
```

This lets you keep your existing UI while using v1 data.

---

## Step 5: Test with Mock AI Services (30 minutes)

Since you don't have the actual AI services running yet, you need mock endpoints.

### Option A: Use Backend Mock Mode

Set in `backend/.env`:
```env
MOCK_MODE=true
```

But you'll need to modify OrchestrationService to check this flag.

### Option B: Run Mock AI Services

Create simple Flask apps for each service:

**File**: `mock-services/github-agent.py`
```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.post('/analyze')
def analyze():
    return jsonify({
        "skills": [
            {"name": "Python", "confidence": 0.92, "evidence": {...}}
        ],
        "projects": [...]
    })

if __name__ == '__main__':
    app.run(port=8001)
```

Repeat for ports 8002, 8003, 8004.

### Option C: Mock in OrchestrationService

Add to `backend/app/services/orchestration_service.py`:

```python
if os.getenv('MOCK_AI_SERVICES') == 'true':
    # Return mock data for each service
    github_result = {...}
    resume_result = {...}
    # etc.
```

---

## Step 6: Update Backend to Handle Missing Fields (15 minutes)

The v1 endpoint expects:
- `user_id`
- `github_username`  
- `target_role`
- `job_description`
- `resume_file`

But your current upload might not send `user_id` or `job_description`.

### Make Fields Optional Temporarily

**File**: `backend/app/api/v1/analysis.py`

```python
@router.post("")
async def full_analysis(
    github_username: str = Form(...),
    target_role: str = Form(...),
    job_description: str = Form(default="No description provided"),  # ← Make optional
    resume_file: UploadFile = File(...),
    user_id: UUID = Form(default_factory=uuid4),  # ← Auto-generate if not provided
    db: AsyncSession = Depends(get_db),
):
```

This lets you test without breaking existing functionality.

---

## Step 7: Verify the Chain Works (30 minutes)

### Test Checklist:

1. **Upload Form**
   - [ ] File uploads successfully
   - [ ] Role is selected
   - [ ] Job description is entered
   - [ ] Submits to `/api/v1/analysis`
   - [ ] No 400/422 errors

2. **Processing Page**
   - [ ] Polling starts
   - [ ] Status updates appear
   - [ ] No infinite loops
   - [ ] Transitions to results on completion

3. **Results Page**
   - [ ] Data displays correctly
   - [ ] Verified/Partial/Missing skills show
   - [ ] Roadmap renders
   - [ ] No console errors

4. **Backend Logs**
   - [ ] OrchestrationService.run() is called
   - [ ] All 5 steps execute (even if mocked)
   - [ ] Analysis persists to database
   - [ ] No unhandled exceptions

---

## Common Issues & Fixes

### Issue: 422 Validation Error

**Cause**: Missing required fields

**Fix**: Check FormData includes all required fields:
```typescript
console.log('Form data:', {
  user_id: form.get('user_id'),
  github_username: form.get('github_username'),
  target_role: form.get('target_role'),
  job_description: form.get('job_description'),
  resume_file: form.get('resume_file')?.name
});
```

### Issue: CORS Error

**Cause**: Vite proxy not forwarding to v1 correctly

**Fix**: Check `client/vite.config.ts`:
```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  }
}
```

### Issue: Processing Page Shows "Job Not Found"

**Cause**: Using old jobId format or wrong endpoint

**Fix**: Ensure you're using `analysis_id` from v1 response:
```typescript
const { data } = await axios.post('/api/v1/analysis', form);
navigate(`/processing/${data.analysis_id}`);  // ← Use analysis_id
```

### Issue: AI Services Connection Refused

**Cause**: Services not running on ports 8001-8004

**Fix**: Either:
1. Start mock services
2. Enable `MOCK_AI_SERVICES=true` in backend
3. Implement real services

---

## Success Criteria

You'll know this worked when:

✅ Frontend submits to `/api/v1/analysis`  
✅ OrchestrationService._execute_pipeline() runs  
✅ All 5 steps execute (even with mocks)  
✅ Analysis persists to PostgreSQL  
✅ Results page displays v1 data  
✅ No more calls to `/api/analyze`  

---

## What This Unlocks

Once this is working:

1. ✅ **Proper architecture** - All modules connected
2. ✅ **Database persistence** - Analyses saved
3. ✅ **Structured data** - Confidence scores, evidence
4. ✅ **Extensibility** - Easy to add O*NET, YouTube, etc.
5. ✅ **Team collaboration** - Each AI service independent

You can then implement the missing pieces (GitHub Intelligence, O*NET, YouTube) **without changing the frontend again**.

---

## Next Steps After This

Once the v1 pipeline works:

1. Implement GitHub Intelligence service (port 8001)
2. Add O*NET skill requirements
3. Add YouTube API resources
4. Remove hard-coded roadmap data
5. Enhance LLM prompts with structured data

But **do this migration first**. Everything else depends on it.

---

## Estimated Time

- Reading this guide: 15 min
- Making changes: 2 hours
- Testing: 1 hour
- **Total: 3-4 hours**

This is the **highest ROI** change you can make to the project right now.

---

## Questions?

If you run into issues:

1. Check `backend/app/services/orchestration_service.py` - The code is already there
2. Check `backend/app/api/v1/analysis.py` - The endpoint exists
3. Check PostgreSQL - Make sure migrations ran
4. Check logs - FastAPI logs will show errors

The architecture is **already built**. You're just connecting the frontend to it.

---

**DO THIS FIRST** before implementing any new features. Everything else builds on this foundation.

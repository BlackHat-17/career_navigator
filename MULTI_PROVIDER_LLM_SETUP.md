# Multi-Provider LLM Fallback System

Complete guide for the 5-tier intelligent LLM fallback system with Gemini, Grok, NVIDIA, and local Ollama support.

## 🎯 Fallback Strategy

```
┌────────────────────────────────────────────────────────────┐
│  Tier 1: Gemini (Google AI)                                │
│  ├─ gemini-3.7-flash (primary)                            │
│  ├─ gemini-3.5-flash (fallback 1)                         │
│  └─ gemini-3.8-flash (fallback 2)                         │
├────────────────────────────────────────────────────────────┤
│  Tier 2: Grok (xAI)                                       │
│  └─ grok-beta                                             │
├────────────────────────────────────────────────────────────┤
│  Tier 3: NVIDIA API Catalog                               │
│  └─ meta/llama-3.1-70b-instruct                          │
├────────────────────────────────────────────────────────────┤
│  Tier 4: Ollama (Local)                                   │
│  └─ qwen2.5:3b (or any local model)                      │
├────────────────────────────────────────────────────────────┤
│  Tier 5: Mock/Demo Results                                │
│  └─ Hardcoded realistic data (always succeeds)           │
└────────────────────────────────────────────────────────────┘
```

## 📋 Configuration

### Environment Variables (`backend/.env`)

```env
# ── Tier 1: Gemini (Primary) ──────────────────────────────────
GEMINI_API_KEY=AIza...                           # Get from https://aistudio.google.com/app/apikey
GEMINI_MODEL=gemini-3.7-flash
GEMINI_FALLBACK_MODELS=gemini-3.5-flash,gemini-3.8-flash

# ── Tier 2: Grok (xAI) ────────────────────────────────────────
GROK_ENABLED=false                                # Set to true to enable
GROK_API_KEY=                                     # Get from https://console.x.ai
GROK_MODEL=grok-beta

# ── Tier 3: NVIDIA API Catalog ────────────────────────────────
NVIDIA_ENABLED=false                              # Set to true to enable
NVIDIA_API_KEY=                                   # Get from https://build.nvidia.com
NVIDIA_MODEL=meta/llama-3.1-70b-instruct

# ── Tier 4: Ollama (Local) ────────────────────────────────────
OLLAMA_ENABLED=false                              # Set to true to enable
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b

# ── Emergency Override ─────────────────────────────────────────
MOCK_MODE=false                                   # Skip all AI, use demo data
```

## 🚀 Quick Start Configurations

### Configuration 1: Gemini Only (Free, Recommended)

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.7-flash
GEMINI_FALLBACK_MODELS=gemini-3.5-flash,gemini-3.8-flash

GROK_ENABLED=false
NVIDIA_ENABLED=false
OLLAMA_ENABLED=false
```

**Pros:** Fast, free tier available, reliable  
**Cons:** Requires internet, subject to rate limits

---

### Configuration 2: Maximum Reliability

```env
GEMINI_API_KEY=your_gemini_key
GROK_ENABLED=true
GROK_API_KEY=your_grok_key
NVIDIA_ENABLED=true
NVIDIA_API_KEY=your_nvidia_key
OLLAMA_ENABLED=true
```

**Pros:** Always completes, 4 cloud providers + local  
**Cons:** Requires multiple API keys

---

### Configuration 3: Privacy-First (Local Only)

```env
GEMINI_ENABLED=false
GROK_ENABLED=false
NVIDIA_ENABLED=false
OLLAMA_ENABLED=true
OLLAMA_MODEL=qwen2.5:7b                           # Use 7B for better quality
```

**Pros:** Completely offline, zero API costs, total privacy  
**Cons:** Slower, requires local GPU/CPU resources

---

### Configuration 4: Development/Testing

```env
MOCK_MODE=true
```

**Pros:** Instant results, no API keys needed  
**Cons:** Fake data only

---

## 📥 Provider Setup Guides

### 1. Gemini (Google AI) - Primary Provider

**Get API Key:**
1. Visit https://aistudio.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API key"
4. Copy the key starting with `AIza...`

**Free Tier Limits:**
- 15 requests/minute
- 1M tokens/minute
- 1,500 requests/day

**Cost:** Free tier available, paid plans start at $0.002/1K tokens

---

### 2. Grok (xAI) - Second Tier

**Get API Key:**
1. Visit https://console.x.ai
2. Sign up/sign in
3. Navigate to API section
4. Generate API key

**Enable in `.env`:**
```env
GROK_ENABLED=true
GROK_API_KEY=xai-...
GROK_MODEL=grok-beta
```

**Features:**
- Real-time web access
- Long context window
- Strong reasoning capabilities

**Cost:** Check https://x.ai/api for current pricing

---

### 3. NVIDIA API Catalog - Third Tier

**Get API Key:**
1. Visit https://build.nvidia.com
2. Create NVIDIA account
3. Go to "API Catalog"
4. Generate API key

**Enable in `.env`:**
```env
NVIDIA_ENABLED=true
NVIDIA_API_KEY=nvapi-...
NVIDIA_MODEL=meta/llama-3.1-70b-instruct
```

**Available Models:**
- `meta/llama-3.1-70b-instruct` (recommended)
- `meta/llama-3.1-405b-instruct` (highest quality)
- `mistralai/mixtral-8x22b-instruct-v0.1`
- Many more at https://build.nvidia.com/explore/discover

**Free Tier:** 1,000 free credits/month  
**Cost:** Pay-as-you-go after free credits

---

### 4. Ollama (Local) - Fourth Tier

**Installation:**

**Windows:**
```powershell
winget install Ollama.Ollama
```

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Pull Model:**
```bash
# Recommended: Fast, good quality
ollama pull qwen2.5:3b

# Better quality, slower
ollama pull qwen2.5:7b

# Best quality, requires more RAM
ollama pull qwen2.5:14b
```

**Enable in `.env`:**
```env
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
```

**Test Ollama:**
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5:3b",
  "prompt": "Hello!",
  "stream": false
}'
```

---

## 🔄 How Fallback Works

### Automatic Progression

The system tries providers in order until one succeeds:

```python
1. Try Gemini 3.7 Flash
   ↓ (fails with 503)
2. Try Gemini 3.5 Flash
   ↓ (fails with 503)
3. Try Gemini 3.8 Flash
   ↓ (all Gemini failed)
4. Try Grok (if GROK_ENABLED=true)
   ↓ (fails or disabled)
5. Try NVIDIA (if NVIDIA_ENABLED=true)
   ↓ (fails or disabled)
6. Try Ollama (if OLLAMA_ENABLED=true)
   ↓ (fails or disabled)
7. Return mock/demo data (always succeeds)
```

### Error Categorization

**Retryable Errors** (try next Gemini model):
- 503 Service Unavailable
- "High demand" / "Overloaded"
- "Temporarily unavailable"
- Network timeouts

**Non-Retryable Errors** (skip to next provider tier):
- 401 Unauthorized (bad API key)
- 404 Not Found (model doesn't exist)
- 429 Quota Exceeded
- JSON parse errors

---

## 📊 Performance Comparison

| Provider | Latency | Quality | Cost (per 1M tokens) | Free Tier |
|----------|---------|---------|----------------------|-----------|
| Gemini 3.7 Flash | ~2-4s | Excellent | $0.00 | 1,500 req/day |
| Gemini 3.5 Flash | ~2-4s | Excellent | $0.00 | 1,500 req/day |
| Grok Beta | ~3-5s | Excellent | ~$5.00 | Limited |
| NVIDIA Llama 3.1 70B | ~4-6s | Excellent | ~$0.90 | 1,000 credits |
| Ollama Qwen 2.5 3B | ~5-10s (CPU) | Good | $0.00 | Unlimited |
| Mock Data | <100ms | N/A (fake) | $0.00 | Unlimited |

---

## 🎛️ Advanced Configuration

### Custom Model Selection

**Use different Gemini models:**
```env
GEMINI_MODEL=gemini-3.5-flash
GEMINI_FALLBACK_MODELS=gemini-3.7-flash,gemini-3.8-flash
```

**Use Grok as primary (skip Gemini):**
```env
GEMINI_API_KEY=                                   # Leave empty
GROK_ENABLED=true
GROK_API_KEY=your_key
```

**Use larger local model:**
```env
OLLAMA_MODEL=qwen2.5:7b                           # Better quality
# or
OLLAMA_MODEL=llama3.2:3b                          # Alternative
```

### Cost Optimization

**Minimize costs:**
- Use Gemini free tier (primary)
- Enable Ollama (local backup)
- Disable paid providers

**Maximize quality:**
- Enable all providers
- Use larger models (Llama 3.1 405B, Qwen 2.5 14B)

**Balance:**
- Gemini 3.7 Flash (fast, free)
- NVIDIA Llama 3.1 70B (backup, paid)
- Ollama Qwen 2.5 3B (final fallback)

---

## 🐛 Troubleshooting

### All providers failing immediately

**Check:**
```bash
# Test Gemini
curl -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}' \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.7-flash:generateContent?key=YOUR_KEY"

# Test Ollama
curl http://localhost:11434/api/tags
```

**Common issues:**
- Invalid API keys
- Network/firewall blocking requests
- Ollama not running (run `ollama serve`)

### Getting demo results when you shouldn't

**Check backend logs:**
```bash
docker compose logs backend | grep -i "llm\|gemini\|grok\|nvidia\|ollama"
```

**Verify:**
- `MOCK_MODE=false`
- At least one provider is properly configured
- API keys are valid

### Provider-specific issues

**Gemini 503 errors:**
- Normal during peak times
- Fallback will handle automatically
- Try different model (3.5 vs 3.7)

**Grok/NVIDIA connection refused:**
- Check API key is valid
- Verify endpoint URLs are correct
- Check firewall/proxy settings

**Ollama not responding:**
```bash
# Check if running
ollama list

# Start service
ollama serve

# Pull model if missing
ollama pull qwen2.5:3b
```

---

## 📈 Monitoring

### Watch Real-Time Progress

The processing page shows which provider is being used:

```
▸ [17:42:15] Analysing with Gemini 3.7 Flash...
▸ [17:42:18] Trying Gemini fallback: gemini-3.5-flash
▸ [17:42:21] Trying Grok (grok-beta)...
▸ [17:42:25] Trying NVIDIA (meta/llama-3.1-70b-instruct)...
▸ [17:42:30] Using local qwen2.5:3b...
✓ [17:42:38] Analysis complete — building your report…
```

### Backend Logs

```bash
# View live logs
docker compose logs -f backend

# Search for LLM activity
docker compose logs backend | grep "LLM\|Gemini\|Grok\|NVIDIA\|Ollama"
```

---

## 🎉 Benefits Summary

✅ **Reliability** - 5 tiers ensure analysis always completes  
✅ **Cost** - Free options available (Gemini + Ollama)  
✅ **Privacy** - Local model option for sensitive data  
✅ **Speed** - Intelligent routing to fastest available  
✅ **Quality** - Multiple high-quality models  
✅ **Flexibility** - Easy to add/remove providers  
✅ **Transparency** - Real-time progress visibility  

---

## 📚 Related Documentation

- [AI_MODELS_FALLBACK.md](./AI_MODELS_FALLBACK.md) - Architecture details
- [OLLAMA_SETUP.md](./OLLAMA_SETUP.md) - Local model guide
- [backend/app/services/llm_fallback_service.py](./backend/app/services/llm_fallback_service.py) - Source code

---

## 🆘 Support

**Issues? Questions?**
1. Check this guide
2. Review backend logs
3. Test each provider individually
4. Enable `MOCK_MODE=true` for immediate testing
5. Create an issue with logs attached

**Quick test:**
```bash
# Test the entire system
docker compose restart backend
# Upload a resume and watch the processing page
```

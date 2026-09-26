# AI Models Fallback System

Career Navigator uses a **4-tier fallback system** to ensure analysis always completes, even when cloud models are unavailable.

## Fallback Priority

```
┌─────────────────────────────────────────┐
│  1. Gemini 3.7 Flash (Primary)          │  ← Cloud, Fast, Latest
├─────────────────────────────────────────┤
│  2. Gemini 3.5 Flash (Fallback 1)       │  ← Cloud, Reliable
├─────────────────────────────────────────┤
│  3. Gemini 3.8 Flash (Fallback 2)       │  ← Cloud, Alternative
├─────────────────────────────────────────┤
│  4. Qwen 2.5 3B Local (Fallback 3)      │  ← Offline, Always Available
│     via Ollama (if enabled)             │
├─────────────────────────────────────────┤
│  5. Mock/Demo Results (Final Fallback)  │  ← Hardcoded realistic data
└─────────────────────────────────────────┘
```

## Configuration

### Environment Variables

**backend/.env:**

```env
# ── Gemini Cloud Models ────────────────────────────────────────────
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.7-flash
GEMINI_FALLBACK_MODELS=gemini-3.5-flash,gemini-3.8-flash

# ── Local Model (Optional) ─────────────────────────────────────────
OLLAMA_ENABLED=true                    # Set to false to skip local fallback
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b

# ── Emergency Override ─────────────────────────────────────────────
MOCK_MODE=false                        # Set to true to skip all AI calls
```

## When Each Model is Used

### Gemini 3.7 Flash (Primary)
- **Used:** On every analysis attempt
- **Triggers fallback when:**
  - 503 Service Unavailable
  - High demand / overloaded
  - Model not found
  - Network errors

### Gemini 3.5 Flash (Fallback 1)
- **Used:** When Gemini 3.7 Flash fails with retryable error
- **Triggers fallback when:** Same as primary

### Gemini 3.8 Flash (Fallback 2)
- **Used:** When both 3.7 and 3.5 fail
- **Triggers local fallback when:** All Gemini models exhausted

### Qwen 2.5 Local (Fallback 3)
- **Used:** When all cloud models fail AND `OLLAMA_ENABLED=true`
- **Requires:** Ollama installed and `qwen2.5:3b` model pulled
- **Triggers demo when:**
  - Ollama not running
  - Model not found
  - JSON parse errors
  - Any local model error

### Mock/Demo Results (Final Fallback)
- **Always succeeds** with realistic hardcoded data
- **Used when:**
  - `MOCK_MODE=true` (immediate, skips all models)
  - All models failed (after trying all tiers)
  - No Gemini API key set
  - Ollama disabled or unavailable

## Error Handling

### Retryable Errors (Try next model)
- `503 Service Unavailable`
- `High demand`
- `Overloaded`
- `Temporarily unavailable`

### Non-Retryable Errors (Skip to local/demo)
- `401 Unauthorized` (bad API key)
- `404 Not Found` (model doesn't exist)
- Quota exceeded (429)
- JSON parse errors

## Performance Characteristics

| Model               | Latency    | Cost      | Availability | Quality    |
|---------------------|------------|-----------|--------------|------------|
| Gemini 3.7 Flash    | ~2-4s      | Free*     | 99.5%        | Excellent  |
| Gemini 3.5 Flash    | ~2-4s      | Free*     | 99.5%        | Excellent  |
| Gemini 3.8 Flash    | ~2-4s      | Free*     | 99.5%        | Excellent  |
| Qwen 2.5 3B (Local) | ~5-10s CPU | $0        | 100%         | Good       |
| Mock/Demo           | <100ms     | $0        | 100%         | N/A (fake) |

*Free tier limits apply. See https://ai.google.dev/pricing

## Setup Local Fallback

See [OLLAMA_SETUP.md](./OLLAMA_SETUP.md) for detailed instructions.

**Quick start:**

```bash
# Install Ollama (Windows)
winget install Ollama.Ollama

# Pull the model
ollama pull qwen2.5:3b

# Enable in .env
echo "OLLAMA_ENABLED=true" >> backend/.env

# Restart backend
docker compose restart backend
```

## Monitoring

Watch the processing page terminal for fallback messages:

```
▸ [17:42:15] Analysing with Gemini 3.7 Flash...
▸ [17:42:18] Trying fallback model: gemini-3.5-flash
▸ [17:42:21] Trying fallback model: gemini-3.8-flash
▸ [17:42:24] All Gemini models failed — trying local model
▸ [17:42:25] Using local qwen2.5:3b model...
✓ [17:42:32] Analysis complete — building your report…
```

## Best Practices

1. **Always keep Gemini API key valid** - Cloud models are fastest
2. **Enable Ollama for offline capability** - Useful for demos, travel
3. **Use MOCK_MODE=true for testing UI** - Instant results
4. **Monitor rate limits** - Free tier is generous but has limits
5. **Consider GPU for local model** - 5-10x faster than CPU

## Troubleshooting

**All models failing immediately:**
- Check internet connection
- Verify Gemini API key is valid
- Check Google AI Studio for service status

**Local model not working:**
- Run `ollama list` to verify model is installed
- Check `http://localhost:11434` is accessible
- Verify `OLLAMA_ENABLED=true` in .env

**Getting demo results when you shouldn't:**
- Check backend logs for actual error messages
- Verify `MOCK_MODE=false` in .env
- Ensure at least one model is properly configured

## Customizing Fallback Order

Edit `backend/.env`:

```env
# Change primary model
GEMINI_MODEL=gemini-3.5-flash

# Change fallback order (comma-separated)
GEMINI_FALLBACK_MODELS=gemini-3.7-flash,gemini-3.8-flash

# Use a different local model
OLLAMA_MODEL=llama3.2:3b
```

## Cost Optimization

**Free tier only (no cost):**
```env
GEMINI_MODEL=gemini-3.7-flash
OLLAMA_ENABLED=true
```

**Maximize speed (paid API):**
```env
GEMINI_MODEL=gemini-3.7-flash
OLLAMA_ENABLED=false  # Skip local fallback
```

**Offline-first (privacy):**
```env
OLLAMA_ENABLED=true
OLLAMA_MODEL=qwen2.5:7b  # Better quality
GEMINI_MODEL=gemini-3.7-flash  # Only if local fails
```

# Ollama Local LLM Setup (Optional)

This guide explains how to set up a local Qwen3 model as a final fallback when all Gemini models are unavailable.

## Why Use a Local Model?

- **Zero API costs** - Runs entirely on your machine
- **Offline capability** - Works without internet
- **Privacy** - Resume data never leaves your computer
- **Reliability** - Always available as last resort

## Installation

### 1. Install Ollama

**Windows:**
```powershell
# Download from https://ollama.ai/download/windows
# Or use winget:
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

### 2. Pull the Qwen 2.5 Model

```bash
ollama pull qwen2.5:3b
```

**Model options:**
- `qwen2.5:3b` (3B params, ~2GB, fast) - **Recommended**
- `qwen2.5:7b` (7B params, ~4.5GB, better quality)
- `qwen2.5:14b` (14B params, ~9GB, highest quality)

### 3. Enable in Backend

Edit `backend/.env`:

```env
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
```

### 4. Start Ollama Service

Ollama usually runs automatically after installation. If not:

```bash
ollama serve
```

## Testing

Test that Ollama is working:

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5:3b",
  "prompt": "Hello, how are you?",
  "stream": false
}'
```

## Fallback Priority

Your Career Navigator will try models in this order:

1. **Gemini 3.7 Flash** (primary, cloud)
2. **Gemini 3.5 Flash** (fallback 1, cloud)
3. **Gemini 3.8 Flash** (fallback 2, cloud)
4. **Qwen 2.5 (3B)** (fallback 3, local) ← **If OLLAMA_ENABLED=true**
5. **Mock/Demo Results** (final fallback)

## Performance

**Qwen 2.5 3B on typical hardware:**
- CPU: ~5-10 seconds per analysis
- GPU (if available): ~1-3 seconds per analysis

**To use GPU acceleration:**
- NVIDIA GPU: Ollama automatically uses CUDA if available
- AMD GPU: Follow Ollama ROCm setup guide
- Apple Silicon: Ollama automatically uses Metal

## Troubleshooting

**"connection refused" error:**
```bash
# Check if Ollama is running
ollama list

# Start the service
ollama serve
```

**"model not found" error:**
```bash
# Pull the model
ollama pull qwen2.5:3b
```

**Slow performance:**
- Use a smaller model (`qwen2.5:3b` instead of `7b`)
- Close other applications to free RAM
- Consider using GPU if available

## Disabling Local Fallback

Set in `backend/.env`:

```env
OLLAMA_ENABLED=false
```

The system will fall back to demo results when Gemini models fail.

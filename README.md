## Run API

python -m fastapi dev app/main.py

## OCR Backend (Qwen 3 VL 8B Instruct Q4 via Ollama)

This project is configured for Qwen 3 VL 8B Instruct Q4 through Ollama's OpenAI-compatible endpoint.

1. Ensure Ollama is running.
2. Pull the model in Ollama:

ollama pull qwen3-vl:8b-instruct-q4_K_M

3. Set environment variables:
   - `OLLAMA_API_BASE=http://127.0.0.1:11434/v1`
   - `OLLAMA_MODEL=qwen3-vl:8b-instruct-q4_K_M`
   - `OLLAMA_API_KEY=ollama`
   - `OLLAMA_TIMEOUT=120`
   - `OLLAMA_TEMPERATURE=0`
4. Run the smoke test:

python examples/basic_usage.py

If Ollama or the model is unavailable, the pipeline falls back to mock mode and logs the exact reason.

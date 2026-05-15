# 🎬 AnimaLearn — AI-Animated Educational Video Generator

Transforms any topic into **fully animated 1-minute educational videos** using:
- **Groq API** (free, no credit card) — Llama 3.3 70B for LLM reasoning
- **sentence-transformers** — local embeddings, no API key needed
- **Runway API** — AI scene animation (125 free credits)
- **D-ID API** — talking avatar clips (5 min free trial)
- **edge-tts** — free text-to-speech
- **LangGraph** — multi-agent orchestration with HiL approval gate

## Quick Start (5 Commands)

```bash
unzip animalearn-video-generator.zip && cd animalearn
pip install -r requirements.txt
cp .env.example .env          # MOCK_MODE=true — works without any API keys
# Optional: add GROQ_API_KEY (free: https://console.groq.com/)
streamlit run app.py          # Opens at localhost:8501
```

## API Keys (all free, no credit card)

| Key | Where | What |
|-----|-------|------|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com/) | LLM (Llama 3.3 70B, 30 RPM free) |
| `RUNWAY_API_KEY` | [dev.runwayml.com](https://dev.runwayml.com/) | AI scene animation (125 free credits) |
| `DID_API_KEY` | [studio.d-id.com](https://studio.d-id.com/) | Talking avatar (5 min free) |
| Embeddings | **None needed** | Local sentence-transformers |
| TTS | **None needed** | edge-tts (free, unlimited) |

## Default Topic: Neural Networks

Reference: `https://en.wikipedia.org/wiki/Neural_network_(machine_learning)`

## Tests

```bash
MOCK_MODE=true python -m pytest tests/ -v   # 17 tests, all pass
```

## Architecture

```
Streamlit UI → LangGraph StateGraph
  ├─ Research Agent (RAG + Qdrant + sentence-transformers)
  ├─ Curriculum Planner (Groq / Llama 3.3 70B)
  ├─ Scriptwriter (Groq + RAG citations)
  ├─ [HiL Gate — user approves/rejects]
  ├─ Media Producer (TTS + Runway animation + D-ID avatar)
  └─ Post-Production (FFmpeg subtitles + intro/outro)
```

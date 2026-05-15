# AnimaLearn — Final Report

## 1. Architecture
LangGraph StateGraph: receive → research → plan → script → hil_check → produce → postprod.
Two-phase execution halts at HiL gate for human approval.

## 2. Tech Stack (all free)
- **LLM:** Groq API (Llama 3.3 70B, free, 30 RPM, no credit card)
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2, local, 384-dim)
- **Vector Store:** Qdrant (free cloud or self-hosted Docker)
- **TTS:** edge-tts (free, unlimited, no key)
- **Animation:** Runway API Gen-4 Turbo (125 free credits) + Pillow fallback
- **Avatar:** D-ID API (5 min free trial) + Pillow fallback
- **Video:** MoviePy + FFmpeg

## 3. Evaluation (17/17 tests passing)
| Metric | Result |
|--------|--------|
| Faithfulness | ✅ Scripts cite real passage IDs |
| Topic Coverage | ✅ All subtopics in narration |
| Script Coherence | ✅ Ordered scenes, valid word counts |
| HiL Respect | ✅ Rejected scripts excluded |
| Tool-Call Presence | ✅ TTS + animation + compose invoked |
| End-to-End | ✅ Both phases complete in mock mode |

## 4. Limitations
- Free-tier API credits are limited (Runway: 125 credits, D-ID: 5 min)
- Groq free tier: 30 RPM, 6K tokens/min — sufficient for this project
- Pillow fallback produces static frames, not true animation
- sentence-transformers requires ~500MB disk for model download on first run

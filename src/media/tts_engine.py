"""AnimaLearn — TTS Engine (edge-tts, free, no API key)"""
from __future__ import annotations
import asyncio, os
from pathlib import Path
from src.settings import MOCK_MODE

async def _edge_tts(text, output_path, voice="en-US-AriaNeural"):
    import edge_tts
    c = edge_tts.Communicate(text, voice)
    await c.save(output_path)
    wc = len(text.split())
    return {"audio_path": output_path, "duration_seconds": round((wc / 150) * 60, 2), "word_count": wc}

def _gtts_fallback(text, output_path):
    from gtts import gTTS
    gTTS(text=text, lang="en").save(output_path)
    wc = len(text.split())
    return {"audio_path": output_path, "duration_seconds": round((wc / 150) * 60, 2), "word_count": wc}

def _mock_tts(text, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(b"\xff\xfb\x90\x00" + b"\x00" * 417)
    wc = len(text.split())
    return {"audio_path": output_path, "duration_seconds": round((wc / 150) * 60, 2), "word_count": wc}

def generate_tts(text, output_path, voice="en-US-AriaNeural"):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    if MOCK_MODE: return _mock_tts(text, output_path)
    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(_edge_tts(text, output_path, voice))
        loop.close()
        return result
    except Exception as e:
        print(f"[TTS] edge-tts failed ({e}), trying gTTS...")
        try: return _gtts_fallback(text, output_path)
        except: return _mock_tts(text, output_path)

"""AnimaLearn — AI Avatar Generator
Uses D-ID API (free trial: 5 minutes) with Pillow fallback.
"""
from __future__ import annotations
import time
from pathlib import Path
from src.settings import MOCK_MODE, DID_API_KEY

DEFAULT_AVATAR_URL = "https://create-images-results.d-id.com/DefaultPresenters/Emma_f/image.jpeg"

def generate_avatar_clip(text, output_path, avatar_image_url=""):
    """Generate a talking-avatar video clip."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    if not MOCK_MODE and DID_API_KEY:
        try:
            return _did_generate(text, output_path, avatar_image_url or DEFAULT_AVATAR_URL)
        except Exception as e:
            print(f"[Avatar] D-ID failed ({e}), using fallback")
    return _mock_avatar(text, output_path)

def _did_generate(text, output_path, avatar_url):
    """Call D-ID API to create a talking-head video."""
    import httpx
    # Create talk
    resp = httpx.post(
        "https://api.d-id.com/talks",
        headers={"Authorization": f"Basic {DID_API_KEY}", "Content-Type": "application/json"},
        json={
            "source_url": avatar_url,
            "script": {"type": "text", "input": text, "provider": {"type": "microsoft", "voice_id": "en-US-AriaNeural"}},
            "config": {"result_format": "mp4"},
        },
        timeout=30,
    )
    resp.raise_for_status()
    talk_id = resp.json()["id"]
    # Poll
    for _ in range(60):
        time.sleep(3)
        poll = httpx.get(f"https://api.d-id.com/talks/{talk_id}",
                         headers={"Authorization": f"Basic {DID_API_KEY}"}, timeout=15)
        data = poll.json()
        if data.get("status") == "done":
            vid_url = data["result_url"]
            vid = httpx.get(vid_url, timeout=60)
            with open(output_path, "wb") as f:
                f.write(vid.content)
            wc = len(text.split())
            return {"video_path": output_path, "duration_seconds": round((wc/150)*60, 2), "method": "d-id_api"}
        elif data.get("status") == "error":
            raise RuntimeError(f"D-ID error: {data.get('error')}")
    raise TimeoutError("D-ID timed out")

def _mock_avatar(text, output_path):
    """Fallback: generate avatar-style image with Pillow."""
    from src.media.animation_generator import _pillow_fallback
    wc = len(text.split())
    dur = max(5, round((wc / 150) * 60, 2))
    result = _pillow_fallback(
        prompt=f"Talking presenter: {text[:60]}...",
        output_path=output_path,
        bg_color="#1a1a2e",
        text_overlay="🎙️ AI Presenter",
        duration_seconds=dur,
    )
    result["method"] = "pillow_avatar_fallback"
    return result

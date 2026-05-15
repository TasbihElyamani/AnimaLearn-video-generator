"""AnimaLearn — AI Animation Generator
Uses Runway API (Gen-4 Turbo, 125 free credits) with Pillow fallback.
"""
from __future__ import annotations
import os, time, math, random
from pathlib import Path
from src.settings import MOCK_MODE, RUNWAY_API_KEY

def generate_animation(prompt, output_path, background_color="#0b3d91",
                       text_overlay="", duration_seconds=5):
    """Generate an animated video clip for a scene."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    if not MOCK_MODE and RUNWAY_API_KEY:
        try:
            return _runway_generate(prompt, output_path, duration_seconds)
        except Exception as e:
            print(f"[Animation] Runway failed ({e}), using Pillow fallback")
    return _pillow_fallback(prompt, output_path, background_color, text_overlay, duration_seconds)

def _runway_generate(prompt, output_path, duration_seconds):
    """Call Runway API to generate a video clip."""
    import httpx
    # Step 1: Create generation task
    resp = httpx.post(
        "https://api.dev.runwayml.com/v1/image_to_video",
        headers={"Authorization": f"Bearer {RUNWAY_API_KEY}", "X-Runway-Version": "2024-11-06"},
        json={"model": "gen4_turbo", "promptText": prompt, "duration": min(duration_seconds, 10),
              "ratio": "1280:720"},
        timeout=30,
    )
    resp.raise_for_status()
    task_id = resp.json()["id"]
    # Step 2: Poll for completion
    for _ in range(60):
        time.sleep(5)
        poll = httpx.get(
            f"https://api.dev.runwayml.com/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {RUNWAY_API_KEY}", "X-Runway-Version": "2024-11-06"},
            timeout=15,
        )
        data = poll.json()
        if data.get("status") == "SUCCEEDED":
            video_url = data["output"][0]
            # Download video
            vid = httpx.get(video_url, timeout=60)
            with open(output_path, "wb") as f:
                f.write(vid.content)
            return {"video_path": output_path, "duration_seconds": duration_seconds, "method": "runway_gen4_turbo"}
        elif data.get("status") == "FAILED":
            raise RuntimeError(f"Runway generation failed: {data.get('failure')}")
    raise TimeoutError("Runway generation timed out")

def _pillow_fallback(prompt, output_path, bg_color, text_overlay, duration_seconds):
    """Create an animated-style image and package as a video-like file."""
    from PIL import Image, ImageDraw, ImageFont
    width, height = 1280, 720

    def hex_to_rgb(h):
        h = h.lstrip("#")
        if len(h) == 3: h = "".join(c*2 for c in h)
        return tuple(int(h[i:i+2], 16) for i in (0,2,4))

    bg = hex_to_rgb(bg_color)
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    # Gradient
    for y in range(height):
        r = max(0, bg[0] - int(y * bg[0] / height * 0.4))
        g = max(0, bg[1] - int(y * bg[1] / height * 0.4))
        b = max(0, bg[2] - int(y * bg[2] / height * 0.4))
        draw.line([(0,y),(width,y)], fill=(r,g,b))

    # Grid
    gc = tuple(min(255, c + 15) for c in bg)
    for x in range(0, width, 40): draw.line([(x,0),(x,height)], fill=gc, width=1)
    for y in range(0, height, 40): draw.line([(0,y),(width,y)], fill=gc, width=1)

    # Decorative shapes
    random.seed(hash(prompt) % 2**32)
    accent = tuple(min(255, c + 80) for c in bg)
    for _ in range(5):
        cx, cy, r = random.randint(50,width-50), random.randint(50,height-50), random.randint(20,60)
        draw.ellipse([cx-r,cy-r,cx+r,cy+r], fill=accent, outline=tuple(min(255,c+40) for c in accent))

    # Font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
        sfont = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
        mfont = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except:
        font = sfont = mfont = ImageFont.load_default()

    # Title text
    if text_overlay:
        words = text_overlay.split()
        lines, cur = [], ""
        for w in words:
            test = f"{cur} {w}".strip()
            try: tw = font.getbbox(test)[2]
            except: tw = len(test) * 22
            if tw <= width * 0.8: cur = test
            else:
                if cur: lines.append(cur)
                cur = w
        if cur: lines.append(cur)
        y0 = height // 3 - len(lines) * 25
        for i, line in enumerate(lines):
            try: tw = font.getbbox(line)[2]
            except: tw = len(line) * 22
            draw.text(((width-tw)//2+2, y0+i*48+2), line, fill=tuple(max(0,c-60) for c in bg), font=font)
            draw.text(((width-tw)//2, y0+i*48), line, fill="white", font=font)

    # Prompt as subtitle
    if prompt:
        plines = []
        cur = ""
        for w in prompt.split()[:20]:
            test = f"{cur} {w}".strip()
            try: tw = sfont.getbbox(test)[2]
            except: tw = len(test) * 13
            if tw <= width * 0.7: cur = test
            else:
                if cur: plines.append(cur)
                cur = w
        if cur: plines.append(cur)
        for i, line in enumerate(plines):
            try: tw = sfont.getbbox(line)[2]
            except: tw = len(line) * 13
            draw.text(((width-tw)//2, int(height*0.62)+i*28), line, fill=tuple(min(255,c+100) for c in bg), font=sfont)

    draw.text((width-130, height-25), "AnimaLearn", fill=tuple(min(255,c+30) for c in bg), font=mfont)

    # Save as PNG (will be treated as a still frame by compositor)
    png_path = output_path.replace(".mp4", ".png")
    img.save(png_path, quality=95)
    # Also copy as the output path for consistency
    img.save(output_path.replace(".mp4",".png"), quality=95)

    return {"video_path": png_path, "duration_seconds": duration_seconds, "method": "pillow_fallback"}

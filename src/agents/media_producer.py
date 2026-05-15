"""AnimaLearn — Media Producer Agent"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from src.settings import VIDEO_DIR, MAX_TOOL_CALLS_PER_AGENT
from src.media.tts_engine import generate_tts
from src.media.animation_generator import generate_animation
from src.media.avatar_generator import generate_avatar_clip
from src.media.video_compositor import compose_video
from src.observability import PipelineTracer

def run_media_producer(script, tracer, progress_callback=None):
    vnum = script["video_number"]
    title = script.get("title", f"Video {vnum}")
    scenes = script.get("scenes", [])
    vdir = VIDEO_DIR / f"video_{vnum}"
    vdir.mkdir(parents=True, exist_ok=True)
    tracer.log("Media Producer", f"Producing Video {vnum}: '{title}'", "info")
    tc, audio_paths, clip_paths = 0, [], []
    limit = MAX_TOOL_CALLS_PER_AGENT - 1  # reserve 1 for compose

    for sc in scenes:
        if tc >= limit: break
        sn = sc.get("scene_number", len(audio_paths)+1)
        narr = sc.get("narration","")
        vd = sc.get("visual_direction", {})
        if isinstance(vd, str): vd = {"animation_prompt": vd, "avatar_mode": False}

        # TTS
        if narr.strip():
            apath = str(vdir / f"scene_{sn}_audio.mp3")
            tracer.log_tool_call("Media Producer", "generate_tts", {"scene":sn})
            r = generate_tts(narr, apath)
            audio_paths.append(r["audio_path"])
            tc += 1

        # Animation or Avatar
        cpath = str(vdir / f"scene_{sn}_clip.mp4")
        if vd.get("avatar_mode"):
            tracer.log_tool_call("Media Producer", "generate_avatar_clip", {"scene":sn})
            r = generate_avatar_clip(narr, cpath)
        else:
            prompt = vd.get("animation_prompt", f"Educational scene about {title}")
            tracer.log_tool_call("Media Producer", "generate_animation", {"scene":sn})
            r = generate_animation(prompt, cpath, vd.get("background_color","#0b3d91"), vd.get("text_overlay",""),
                                   sc.get("estimated_duration_seconds", 10))
        clip_paths.append(r["video_path"])
        tracer.log_generation("Media Producer", f"Scene {sn} clip ({r['method']})", r["video_path"])
        tc += 1

    # Compose
    out = str(vdir / f"video_{vnum}_raw.mp4")
    tracer.log_tool_call("Media Producer", "compose_video", {"clips":len(clip_paths)})
    cr = compose_video(clip_paths, audio_paths, out)
    tc += 1
    tracer.log("Media Producer", f"Video {vnum} done: {cr['duration_seconds']}s", "success")
    return {"video_number":vnum,"video_path":cr["video_path"],"audio_paths":audio_paths,
            "clip_paths":clip_paths,"duration_seconds":cr["duration_seconds"],"tool_calls":tc}

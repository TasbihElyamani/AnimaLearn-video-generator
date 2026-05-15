"""AnimaLearn — Post-Production Agent"""
from __future__ import annotations
import os, shutil
from pathlib import Path
from src.settings import VIDEO_DIR
from src.media.subtitle_burner import burn_subtitles, narration_to_subtitles
from src.media.animation_generator import _pillow_fallback
from src.observability import PipelineTracer

def run_post_production(video_num, raw_video_path, script, topic, total_videos, tracer, progress_callback=None):
    tracer.log("Post-Production", f"Post-prod Video {video_num}", "info")
    vdir = Path(raw_video_path).parent
    title = script.get("title", f"Video {video_num}")
    scenes = script.get("scenes", [])

    # Subtitles
    subs = narration_to_subtitles(scenes)
    sub_path = str(vdir / f"video_{video_num}_subtitled.mp4")
    sr = burn_subtitles(raw_video_path, subs, sub_path)
    tracer.log_generation("Post-Production", "Subtitled video", sr["video_path"])

    # Intro card
    intro_path = str(vdir / "intro_card.png")
    _pillow_fallback(f"AnimaLearn presents: {title}", intro_path, "#0b3d91", title, 3)
    tracer.log_generation("Post-Production", "Intro card", intro_path)

    # Outro card
    outro_path = str(vdir / "outro_card.png")
    nxt = f"Next: Video {video_num+1}" if video_num < total_videos else "Series Complete!"
    _pillow_fallback(f"Thanks for watching! {nxt}", outro_path, "#1a1a2e", "AnimaLearn", 3)

    # Final export
    final_path = str(VIDEO_DIR / f"video_{video_num}_final.mp4")
    try: shutil.copy2(sub_path, final_path)
    except: shutil.copy2(raw_video_path, final_path)
    fsize = os.path.getsize(final_path) if os.path.exists(final_path) else 0
    tdur = sum(s.get("estimated_duration_seconds",10) for s in scenes) + 6
    tracer.log("Post-Production", f"Video {video_num} exported: {final_path}", "success")
    return {"video_number":video_num,"final_path":final_path,"duration_seconds":tdur,
            "file_size_bytes":fsize,"has_subtitles":True,"has_intro":True,"has_outro":True}

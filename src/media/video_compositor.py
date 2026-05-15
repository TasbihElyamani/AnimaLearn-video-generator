"""AnimaLearn — Video Compositor (MoviePy + FFmpeg)"""
from __future__ import annotations
import os, shutil
from pathlib import Path
from src.settings import MOCK_MODE

def compose_video(clip_paths, audio_paths, output_path, fps=24):
    """Compose video from clips (images or video files) + audio."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    if MOCK_MODE:
        return _mock_compose(clip_paths, audio_paths, output_path)
    try:
        return _moviepy_compose(clip_paths, audio_paths, output_path, fps)
    except Exception as e:
        print(f"[Compositor] MoviePy failed ({e}), using mock")
        return _mock_compose(clip_paths, audio_paths, output_path)

def _moviepy_compose(clip_paths, audio_paths, output_path, fps):
    from moviepy.editor import ImageClip, AudioFileClip, VideoFileClip, concatenate_videoclips
    clips = []
    total_dur = 0
    for i, cp in enumerate(clip_paths):
        if cp.endswith((".mp4", ".webm")):
            vc = VideoFileClip(cp)
        else:
            dur = 10  # default
            if i < len(audio_paths):
                try:
                    ac = AudioFileClip(audio_paths[i])
                    dur = ac.duration
                    vc = ImageClip(cp).set_duration(dur).set_audio(ac)
                except:
                    vc = ImageClip(cp).set_duration(dur)
            else:
                vc = ImageClip(cp).set_duration(dur)
        clips.append(vc)
        total_dur += vc.duration
    final = concatenate_videoclips(clips, method="compose")
    final.write_videofile(output_path, fps=fps, codec="libx264", audio_codec="aac", logger=None)
    final.close()
    return {"video_path": output_path, "duration_seconds": round(total_dur,2), "num_clips": len(clips)}

def _mock_compose(clip_paths, audio_paths, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(b"\x00\x00\x00\x1c" + b"ftyp" + b"isom" + b"\x00\x00\x02\x00" + b"isomiso2mp41" + b"\x00"*1024)
    return {"video_path": output_path, "duration_seconds": len(clip_paths)*10, "num_clips": len(clip_paths)}

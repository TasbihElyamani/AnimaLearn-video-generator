"""AnimaLearn — Subtitle Burner"""
from __future__ import annotations
import shutil, subprocess
from pathlib import Path
from src.settings import MOCK_MODE

def _srt_time(sec):
    h,rem = divmod(sec, 3600)
    m,s = divmod(rem, 60)
    ms = int((s % 1) * 1000)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{ms:03d}"

def generate_srt(subtitles, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for i, s in enumerate(subtitles, 1):
        lines += [str(i), f"{_srt_time(s['start'])} --> {_srt_time(s['end'])}", s["text"], ""]
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    return output_path

def narration_to_subtitles(scenes):
    subs, t = [], 0.0
    for sc in scenes:
        narr = sc.get("narration","")
        dur = sc.get("estimated_duration_seconds", 10)
        words = narr.split()
        chunks = [" ".join(words[i:i+10]) for i in range(0, len(words), 10)]
        if not chunks: t += dur; continue
        cd = dur / len(chunks)
        for ch in chunks:
            subs.append({"start": round(t,3), "end": round(t+cd,3), "text": ch})
            t += cd
    return subs

def burn_subtitles(video_path, subtitles, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    if MOCK_MODE:
        try: shutil.copy2(video_path, output_path)
        except: Path(output_path).write_bytes(b"\x00"*512)
        return {"video_path": output_path, "num_subtitles": len(subtitles)}
    srt_path = output_path.replace(".mp4", ".srt")
    generate_srt(subtitles, srt_path)
    try:
        subprocess.run(["ffmpeg","-y","-i",video_path,"-i",srt_path,"-c:v","libx264","-c:a","copy","-c:s","mov_text",output_path],
                       capture_output=True, check=True)
    except:
        shutil.copy2(video_path, output_path)
    return {"video_path": output_path, "num_subtitles": len(subtitles)}

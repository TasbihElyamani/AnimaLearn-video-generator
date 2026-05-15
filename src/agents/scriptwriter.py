"""AnimaLearn — Scriptwriter Agent (Groq LLM)"""
from __future__ import annotations
import json
from src.settings import GROQ_API_KEY, GROQ_MODEL, GROQ_BASE_URL, MOCK_MODE, WORDS_PER_MINUTE
from src.rag_chain import retrieve_for_subtopics, format_passages_for_prompt
from src.observability import PipelineTracer
from src.prompts import SCRIPTWRITER_PROMPT


def _call_groq(prompt, temperature=0.7):
    from openai import OpenAI
    client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content


def run_scriptwriter(curriculum_plan, total_videos, duration_minutes, audience_tone, tracer):
    tracer.log("Scriptwriter", f"Writing {len(curriculum_plan)} scripts", "info")
    scripts = []
    target_words = duration_minutes * WORDS_PER_MINUTE

    for vp in curriculum_plan:
        vnum, title = vp["video_number"], vp["title"]
        subtopics = vp.get("subtopics", [])
        tracer.log("Scriptwriter", f"Script {vnum}: '{title}'", "info")

        sub_passages = retrieve_for_subtopics(subtopics)
        all_p, seen = [], set()
        for ps in sub_passages.values():
            for p in ps:
                if p["passage_id"] not in seen:
                    seen.add(p["passage_id"])
                    all_p.append(p)
        tracer.log_retrieval("Scriptwriter", f"video {vnum} subtopics", len(all_p))

        if MOCK_MODE:
            script = _mock_script(vnum, title, subtopics, vp.get("source_ids", []), target_words)
        else:
            prompt = SCRIPTWRITER_PROMPT.format(
                video_number=vnum, total_videos=total_videos, video_title=title,
                subtopics=", ".join(subtopics), audience_tone=audience_tone,
                reference_passages=format_passages_for_prompt(all_p))
            text = _call_groq(prompt)
            try:
                script = json.loads(text)
            except json.JSONDecodeError:
                script = json.loads(text.strip().split("```")[1].replace("json", "", 1).strip())

        script["video_number"] = vnum
        script["title"] = script.get("title", title)
        for sc in script.get("scenes", []):
            if "visual_direction" not in sc or not isinstance(sc["visual_direction"], dict):
                sc["visual_direction"] = {
                    "background_color": "#0b3d91", "text_overlay": sc.get("narration", "")[:50],
                    "animation_prompt": "Educational scene about " + title,
                    "avatar_mode": False, "shapes": [], "transition": "fade"}
            if "estimated_duration_seconds" not in sc:
                sc["estimated_duration_seconds"] = max(5, int((len(sc.get("narration", "").split()) / WORDS_PER_MINUTE) * 60))
        if "total_word_count" not in script:
            script["total_word_count"] = sum(len(s.get("narration", "").split()) for s in script.get("scenes", []))
        scripts.append(script)
        tracer.log("Scriptwriter", f"Script {vnum}: {len(script.get('scenes', []))} scenes, {script.get('total_word_count', 0)} words", "success")
    return scripts


def _mock_script(vnum, title, subtopics, source_ids, target_words):
    colors = ["#0b3d91", "#8b0000", "#2e8b57", "#4b0082", "#b8860b"]
    scenes = []
    # Intro
    ref0 = source_ids[0] if source_ids else "REF-001"
    scenes.append({
        "scene_number": 1,
        "narration": f"Welcome to AnimaLearn! Today we explore {title.lower()}. We will cover {', '.join(subtopics[:2])}, and more. [{ref0}]",
        "visual_direction": {
            "background_color": colors[vnum % 5], "text_overlay": title,
            "animation_prompt": f"Animated title card: {title} with neural network visualization, glowing nodes and connections",
            "avatar_mode": False, "shapes": ["circle", "star"], "transition": "fade"},
        "estimated_duration_seconds": 12})
    # Content scenes
    for i, sub in enumerate(subtopics):
        ref = source_ids[i % len(source_ids)] if source_ids else f"REF-{i + 1:03d}"
        scenes.append({
            "scene_number": i + 2,
            "narration": f"Let us discuss {sub}. This is a key aspect of {title.lower()}. According to our references [{ref}], this concept helps us understand how neural networks process information and learn patterns from data.",
            "visual_direction": {
                "background_color": colors[(vnum + i) % 5], "text_overlay": sub,
                "animation_prompt": f"Animated educational scene showing {sub.lower()} with diagrams, flowing data, and visual metaphors",
                "avatar_mode": i == 0,
                "shapes": ["circle", "arrow"] if i % 2 == 0 else ["line", "star"],
                "transition": "fade"},
            "estimated_duration_seconds": max(8, 48 // max(len(subtopics), 1))})
    # Outro
    scenes.append({
        "scene_number": len(scenes) + 1,
        "narration": f"That wraps up {title.lower()}! We covered {', '.join(subtopics[:2])}, and more. Thanks for watching!",
        "visual_direction": {
            "background_color": colors[vnum % 5], "text_overlay": "Thanks for watching!",
            "animation_prompt": "Outro card with AnimaLearn branding, animated neural network dissolving into particles",
            "avatar_mode": False, "shapes": ["star"], "transition": "fade"},
        "estimated_duration_seconds": 8})
    return {
        "video_number": vnum, "title": title, "scenes": scenes,
        "source_ids": source_ids or ["REF-001"],
        "total_word_count": sum(len(s["narration"].split()) for s in scenes)}

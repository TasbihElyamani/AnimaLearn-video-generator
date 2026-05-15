"""AnimaLearn — Curriculum Planner Agent (Groq LLM)"""
from __future__ import annotations
import json
from src.settings import GROQ_API_KEY, GROQ_MODEL, GROQ_BASE_URL, MOCK_MODE
from src.observability import PipelineTracer
from src.prompts import CURRICULUM_PLANNER_PROMPT


def _call_groq(prompt, temperature=0.3):
    from openai import OpenAI
    client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content


def run_curriculum_planner(topic, num_videos, duration_minutes, research_brief, tracer):
    tracer.log("Curriculum Planner", "Planning curriculum", "info")
    if MOCK_MODE:
        plan = _mock_plan(topic, num_videos, research_brief)
    else:
        brief_text = research_brief.get("research_brief", "")
        prompt = CURRICULUM_PLANNER_PROMPT.format(num_videos=num_videos, research_brief=brief_text)
        prompt += '\n\nReturn a JSON object with key "videos" containing the array.'
        text = _call_groq(prompt)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = json.loads(text.strip().split("```")[1].replace("json", "", 1).strip())
        plan = data.get("videos", data) if isinstance(data, dict) else data
        if not isinstance(plan, list):
            plan = [plan]
    for i, v in enumerate(plan):
        v["video_number"] = v.get("video_number", i + 1)
        v["target_duration_seconds"] = 60
    tracer.log("Curriculum Planner", f"Plan: {len(plan)} videos", "success")
    return plan


def _mock_plan(topic, num_videos, brief):
    sources = brief.get("sources_used", [])
    templates = [
        {"title": "What Are Neural Networks?",
         "subtopics": ["Biological inspiration", "Artificial neurons", "Layers and connections", "Activation functions"]},
        {"title": "How Neural Networks Learn",
         "subtopics": ["Forward pass", "Loss functions", "Backpropagation", "Gradient descent and optimizers"]},
        {"title": "Types of Neural Networks",
         "subtopics": ["CNNs for images", "RNNs and LSTMs for sequences", "Transformers and attention", "GANs for generation"]},
        {"title": "Neural Networks in Action",
         "subtopics": ["Computer vision", "Natural language processing", "AlphaGo and game playing", "Autonomous vehicles"]},
        {"title": "The Future of Neural Networks",
         "subtopics": ["Large language models", "AI safety and alignment", "Neuromorphic computing", "Emerging architectures"]},
    ]
    plan = []
    for i in range(min(num_videos, len(templates))):
        t = templates[i]
        plan.append({
            "video_number": i + 1, "title": t["title"], "subtopics": t["subtopics"],
            "target_duration_seconds": 60,
            "source_ids": sources[:2] if sources else [f"REF-nn_{i}"],
        })
    return plan

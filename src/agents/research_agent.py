"""AnimaLearn — Research Agent (Groq LLM)"""
from __future__ import annotations
import json
from typing import Any
import requests
from bs4 import BeautifulSoup
from src.settings import GROQ_API_KEY, GROQ_MODEL, GROQ_BASE_URL, MOCK_MODE, MAX_TOOL_CALLS_PER_AGENT
from src.rag_chain import retrieve, format_passages_for_prompt
from src.observability import PipelineTracer
from src.prompts import RESEARCH_AGENT_PROMPT


def _call_groq(prompt, temperature=0.3):
    """Call Groq API (OpenAI-compatible) and return text."""
    from openai import OpenAI
    client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content


def fetch_url_content(url, max_chars=50000):
    try:
        r = requests.get(url, headers={"User-Agent": "AnimaLearn/1.0"}, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for t in soup(["script", "style", "nav", "footer"]):
            t.decompose()
        title = soup.title.string if soup.title else url
        text = "\n".join(l.strip() for l in soup.get_text(separator="\n").splitlines() if l.strip())[:max_chars]
        return {"text": text, "title": str(title), "url": url}
    except Exception as e:
        return {"text": "", "title": url, "url": url, "error": str(e)}


def run_research_agent(topic, num_videos, duration_minutes, reference_urls, tracer):
    tracer.log("Research Agent", "Starting research", "info")

    if not MOCK_MODE:
        from src.ingest_qdrant import get_qdrant_client, ensure_collection, ingest_text
        client = get_qdrant_client()
        ensure_collection(client)
        for url in reference_urls[:3]:
            if not url.strip():
                continue
            tracer.log_tool_call("Research Agent", "fetch_reference", {"url": url})
            content = fetch_url_content(url)
            if content.get("text"):
                n = ingest_text(client, content["text"], content["title"][:50].replace(" ", "_").lower())
                tracer.log("Research Agent", f"Ingested {n} vectors from {url[:60]}", "success")

    passages = retrieve(topic, top_k=5)
    tracer.log_retrieval("Research Agent", topic, len(passages))

    if MOCK_MODE:
        brief = {
            "research_brief": f"Comprehensive brief about {topic}. Covers fundamentals, architectures, training, applications, and history.",
            "key_facts": [
                {"fact": "Neural networks consist of layers of interconnected nodes", "source": "REF-neural_networks_overview"},
                {"fact": "Transformers use self-attention for parallel processing", "source": "REF-nn_architectures"},
                {"fact": "Backpropagation is the core training algorithm", "source": "REF-nn_training"},
            ],
            "sources_used": [p["passage_id"] for p in passages],
            "gaps_identified": [],
            "passages": passages,
        }
    else:
        prompt = RESEARCH_AGENT_PROMPT.format(
            topic=topic, num_videos=num_videos,
            reference_urls=", ".join(reference_urls) if reference_urls else "None")
        full_prompt = f"{prompt}\n\nPassages:\n{format_passages_for_prompt(passages)}\n\nReturn valid JSON only."
        text = _call_groq(full_prompt)
        try:
            brief = json.loads(text)
        except json.JSONDecodeError:
            brief = {"research_brief": text[:500], "key_facts": [], "sources_used": [], "gaps_identified": []}
        brief["passages"] = passages

    tracer.log("Research Agent", f"Brief done: {len(passages)} passages", "success")
    return brief

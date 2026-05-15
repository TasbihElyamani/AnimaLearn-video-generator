"""AnimaLearn — DeepEval Test Suite"""
import json, os, sys, pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["MOCK_MODE"] = "true"

from src.agents.research_agent import run_research_agent
from src.agents.curriculum_planner import run_curriculum_planner
from src.agents.scriptwriter import run_scriptwriter
from src.agents.media_producer import run_media_producer
from src.agents.post_production import run_post_production
from src.hil_gate import HiLGateState, HiLDecision, initialize_hil_gate
from src.observability import PipelineTracer
from src.orchestrator import run_pipeline_phase1, run_pipeline_phase2
from src.settings import MAX_TOOL_CALLS_PER_AGENT

@pytest.fixture(scope="module")
def tracer(): return PipelineTracer("test_001")

@pytest.fixture(scope="module")
def research_brief(tracer):
    return run_research_agent("Neural Networks", 3, 1, [], tracer)

@pytest.fixture(scope="module")
def curriculum_plan(research_brief, tracer):
    return run_curriculum_planner("Neural Networks", 3, 1, research_brief, tracer)

@pytest.fixture(scope="module")
def scripts(curriculum_plan, tracer):
    return run_scriptwriter(curriculum_plan, 3, 1, "friendly and educational", tracer)

@pytest.fixture(scope="module")
def hil_gate(scripts):
    g = initialize_hil_gate(len(scripts))
    g.submit_review(1, HiLDecision.APPROVED, "Good!")
    g.submit_review(2, HiLDecision.APPROVED, "Nice.")
    if len(scripts) >= 3: g.submit_review(3, HiLDecision.REJECTED, "Rewrite needed.")
    return g

class TestFaithfulness:
    def test_scripts_cite_sources(self, scripts, research_brief):
        sources = set(research_brief.get("sources_used", []))
        for s in scripts:
            assert any(sid in sources for sid in s.get("source_ids",[])) or not sources

    def test_narration_has_refs(self, scripts):
        for s in scripts:
            assert any("[REF-" in sc.get("narration","") for sc in s.get("scenes",[]))

class TestTopicCoverage:
    def test_subtopics_covered(self, scripts, curriculum_plan):
        pmap = {p["video_number"]: p for p in curriculum_plan}
        for s in scripts:
            plan = pmap.get(s["video_number"], {})
            narr = " ".join(sc.get("narration","").lower() for sc in s.get("scenes",[]))
            for sub in plan.get("subtopics",[]):
                assert any(w in narr for w in sub.lower().split() if len(w) > 3)

    def test_correct_count(self, scripts, curriculum_plan):
        assert len(scripts) == len(curriculum_plan)

class TestScriptCoherence:
    def test_scenes_have_narration(self, scripts):
        for s in scripts:
            for sc in s.get("scenes",[]):
                assert len(sc.get("narration","").strip()) > 10

    def test_scenes_have_visual_direction(self, scripts):
        for s in scripts:
            for sc in s.get("scenes",[]):
                vd = sc.get("visual_direction")
                assert isinstance(vd, dict) and "animation_prompt" in vd

    def test_word_count(self, scripts):
        for s in scripts:
            assert 50 <= s.get("total_word_count", 0) <= 3000

class TestHiLRespect:
    def test_approved(self, hil_gate): assert 1 in hil_gate.get_approved_videos()
    def test_rejected(self, scripts, hil_gate):
        if len(scripts) >= 3: assert 3 in hil_gate.get_rejected_videos()
    def test_production_none_for_rejected(self, scripts, hil_gate):
        for s in scripts:
            r = hil_gate.get_script_for_production(s["video_number"], s)
            if s["video_number"] in hil_gate.get_rejected_videos(): assert r is None
    def test_all_reviewed(self, hil_gate): assert hil_gate.all_reviewed

class TestToolCallPresence:
    def test_media_produces_assets(self, scripts, tracer):
        r = run_media_producer(scripts[0], tracer)
        assert len(r["audio_paths"]) > 0 and len(r["clip_paths"]) > 0 and r["tool_calls"] > 0

    def test_post_prod(self, scripts, tracer):
        mr = run_media_producer(scripts[0], tracer)
        pp = run_post_production(scripts[0]["video_number"], mr["video_path"], scripts[0], "Neural Networks", 3, tracer)
        assert pp["has_subtitles"] and pp["has_intro"] and pp["has_outro"]

    def test_tool_limit(self, scripts, tracer):
        r = run_media_producer(scripts[0], tracer)
        assert r["tool_calls"] <= MAX_TOOL_CALLS_PER_AGENT

class TestEvalCases:
    def test_cases_exist(self):
        p = Path(__file__).parent / "eval_cases.jsonl"
        assert p.exists() and len(p.read_text().strip().split("\n")) >= 5

class TestEndToEnd:
    def test_phase1(self):
        s = run_pipeline_phase1("Neural Networks", 2, 1)
        assert s.get("scripts") and len(s["scripts"]) == 2

    def test_phase2(self):
        s = run_pipeline_phase1("Neural Networks", 2, 1)
        hil = HiLGateState(**s["hil_state"])
        for v in hil.reviews: hil.submit_review(v, HiLDecision.APPROVED)
        s["hil_state"] = hil.model_dump(); s["hil_pending"] = False
        r = run_pipeline_phase2(s)
        assert r.get("completed") and r.get("final_videos") and len(r["final_videos"]) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

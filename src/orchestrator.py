"""AnimaLearn — LangGraph Multi-Agent Orchestrator"""
from __future__ import annotations
from typing import Any, TypedDict, Optional
from langgraph.graph import StateGraph, END
from src.observability import PipelineTracer, generate_trace_id
from src.agents.research_agent import run_research_agent
from src.agents.curriculum_planner import run_curriculum_planner
from src.agents.scriptwriter import run_scriptwriter
from src.agents.media_producer import run_media_producer
from src.agents.post_production import run_post_production
from src.hil_gate import HiLGateState, HiLDecision, initialize_hil_gate
from src.settings import MAX_STEPS, DEFAULT_DURATION_MINUTES

class PipelineState(TypedDict):
    topic: str; num_videos: int; duration_minutes: int; reference_urls: list[str]; audience_tone: str
    trace_id: str; current_stage: str; step_count: int; error: Optional[str]
    research_brief: Optional[dict]; curriculum_plan: Optional[list]; scripts: Optional[list]
    hil_state: Optional[dict]; hil_pending: bool
    approved_scripts: Optional[list]; media_results: Optional[list]; post_production_results: Optional[list]
    completed: bool; final_videos: Optional[list]; progress_callback: Optional[Any]

def node_receive(state):
    t = PipelineTracer(state.get("trace_id") or generate_trace_id())
    t.log("System", f"Pipeline: '{state['topic']}', {state['num_videos']} videos")
    return {"trace_id":t.trace_id,"current_stage":"receive","step_count":1,"error":None,"completed":False}

def node_research(state):
    t = PipelineTracer(state["trace_id"])
    try:
        rb = run_research_agent(state["topic"], state["num_videos"], state["duration_minutes"], state.get("reference_urls",[]), t)
        return {"research_brief":rb,"current_stage":"research","step_count":state.get("step_count",0)+1}
    except Exception as e:
        t.log_error("Research",str(e))
        return {"research_brief":{"research_brief":str(e),"key_facts":[],"sources_used":[],"gaps_identified":[],"passages":[]},
                "current_stage":"research","step_count":state.get("step_count",0)+1,"error":str(e)}

def node_plan(state):
    t = PipelineTracer(state["trace_id"])
    plan = run_curriculum_planner(state["topic"], state["num_videos"], state["duration_minutes"], state.get("research_brief",{}), t)
    return {"curriculum_plan":plan,"current_stage":"plan","step_count":state.get("step_count",0)+1}

def node_script(state):
    t = PipelineTracer(state["trace_id"])
    scripts = run_scriptwriter(state.get("curriculum_plan",[]), state["num_videos"], state["duration_minutes"],
                                state.get("audience_tone","friendly and educational"), t)
    hil = initialize_hil_gate(len(scripts))
    return {"scripts":scripts,"hil_state":hil.model_dump(),"hil_pending":True,"current_stage":"script","step_count":state.get("step_count",0)+1}

def node_hil_check(state):
    hd = state.get("hil_state",{})
    hil = HiLGateState(**hd) if hd else HiLGateState()
    if not hil.all_reviewed: return {"hil_pending":True,"current_stage":"approve"}
    approved = [hil.get_script_for_production(s["video_number"],s) for s in state.get("scripts",[]) if hil.get_script_for_production(s["video_number"],s)]
    t = PipelineTracer(state["trace_id"])
    t.log("HiL Gate", f"{len(approved)} scripts approved", "success")
    return {"approved_scripts":approved,"hil_pending":False,"current_stage":"approve","step_count":state.get("step_count",0)+1}

def node_produce(state):
    t = PipelineTracer(state["trace_id"])
    results = []
    for s in state.get("approved_scripts",[]):
        try: results.append(run_media_producer(s, t))
        except Exception as e: t.log_error("Media Producer", str(e)); results.append({"video_number":s["video_number"],"error":str(e)})
    return {"media_results":results,"current_stage":"produce","step_count":state.get("step_count",0)+1}

def node_postprod(state):
    t = PipelineTracer(state["trace_id"])
    smap = {s["video_number"]:s for s in state.get("approved_scripts",[])}
    results, finals = [], []
    for m in state.get("media_results",[]):
        if "error" in m: continue
        vn = m["video_number"]
        try:
            r = run_post_production(vn, m["video_path"], smap.get(vn,{}), state["topic"], state["num_videos"], t)
            results.append(r); finals.append({"video_number":vn,"title":smap.get(vn,{}).get("title",f"Video {vn}"),"path":r["final_path"],"duration_seconds":r["duration_seconds"]})
        except Exception as e: t.log_error("Post-Production", str(e))
    t.log("System", f"Done! {len(finals)} videos", "success")
    return {"post_production_results":results,"final_videos":finals,"completed":True,"current_stage":"postprod","step_count":state.get("step_count",0)+1}

def should_continue(state):
    if state.get("hil_pending",True): return "wait"
    if state.get("step_count",0) >= MAX_STEPS: return "overflow"
    return "go"

def node_overflow(state):
    return {"error":"MAX_STEPS exceeded","completed":True,"current_stage":"overflow"}

def compile_pipeline():
    g = StateGraph(PipelineState)
    g.add_node("receive",node_receive); g.add_node("research",node_research); g.add_node("plan",node_plan)
    g.add_node("script",node_script); g.add_node("hil_check",node_hil_check)
    g.add_node("produce",node_produce); g.add_node("postprod",node_postprod); g.add_node("overflow",node_overflow)
    g.set_entry_point("receive")
    g.add_edge("receive","research"); g.add_edge("research","plan"); g.add_edge("plan","script"); g.add_edge("script","hil_check")
    g.add_conditional_edges("hil_check",should_continue,{"wait":END,"go":"produce","overflow":"overflow"})
    g.add_edge("produce","postprod"); g.add_edge("postprod",END); g.add_edge("overflow",END)
    return g.compile()

def run_pipeline_phase1(topic, num_videos, duration_minutes=1, reference_urls=None, audience_tone="friendly and educational"):
    initial = {"topic":topic,"num_videos":num_videos,"duration_minutes":duration_minutes,"reference_urls":reference_urls or [],
        "audience_tone":audience_tone,"trace_id":generate_trace_id(),"current_stage":"init","step_count":0,"error":None,
        "research_brief":None,"curriculum_plan":None,"scripts":None,"hil_state":None,"hil_pending":False,
        "approved_scripts":None,"media_results":None,"post_production_results":None,"completed":False,"final_videos":None,"progress_callback":None}
    return compile_pipeline().invoke(initial)

def run_pipeline_phase2(state):
    g = StateGraph(PipelineState)
    g.add_node("hil_check",node_hil_check); g.add_node("produce",node_produce); g.add_node("postprod",node_postprod); g.add_node("overflow",node_overflow)
    g.set_entry_point("hil_check")
    g.add_conditional_edges("hil_check",should_continue,{"wait":END,"go":"produce","overflow":"overflow"})
    g.add_edge("produce","postprod"); g.add_edge("postprod",END); g.add_edge("overflow",END)
    return g.compile().invoke(state)

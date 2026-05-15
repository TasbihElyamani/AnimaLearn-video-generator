"""AnimaLearn — Streamlit UI"""
import streamlit as st
import json, time, os
from pathlib import Path
from src.settings import OUTPUT_DIR, VIDEO_DIR, LOG_FILE, MOCK_MODE
from src.orchestrator import run_pipeline_phase1, run_pipeline_phase2
from src.hil_gate import HiLGateState, HiLDecision
from src.observability import PipelineTracer

st.set_page_config(page_title="AnimaLearn", page_icon="🎬", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
.main-header{font-size:2.5rem;font-weight:800;background:linear-gradient(135deg,#667eea,#764ba2);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:.5rem}
</style>""", unsafe_allow_html=True)

for k,v in [("pipeline_state",None),("phase","input"),("hil_decisions",{}),("trace_events",[])]:
    if k not in st.session_state: st.session_state[k] = v

# ── Sidebar ──
with st.sidebar:
    st.markdown("### 📊 Pipeline Trace")
    if st.session_state.pipeline_state:
        s = st.session_state.pipeline_state
        st.markdown(f"**Trace:** `{s.get('trace_id','N/A')}`")
        st.markdown(f"**Stage:** `{s.get('current_stage','N/A')}`")
        st.markdown(f"**Mock:** `{MOCK_MODE}`")
        if s.get("error"): st.error(s["error"])
    st.markdown("---")
    st.markdown("### Stage Progress")
    stages = [("receive","📥 Input"),("research","🔍 Research"),("plan","📚 Curriculum"),
              ("script","✍️ Scripts"),("approve","👤 HiL Review"),("produce","🎬 Production"),("postprod","🎞️ Post-Prod")]
    cur = st.session_state.pipeline_state.get("current_stage","") if st.session_state.pipeline_state else ""
    passed = False
    for sid,lab in stages:
        if sid == cur: st.markdown(f"▶️ **{lab}**"); passed = True
        elif not passed: st.markdown(f"✅ {lab}")
        else: st.markdown(f"⬜ {lab}")
    st.markdown("---")
    if LOG_FILE.exists():
        try:
            for line in reversed(LOG_FILE.read_text().strip().split("\n")[-15:]):
                e = json.loads(line)
                ic = {"info":"ℹ️","success":"✅","error":"❌","tool_call":"🔧","retrieval":"📚","hil_decision":"👤","generation":"🎨"}.get(e.get("event_type",""),"•")
                st.markdown(f"{ic} `{e.get('agent','')}` {e.get('event','')[:60]}")
        except: pass

# ── Main ──
st.markdown('<div class="main-header">🎬 AnimaLearn</div>', unsafe_allow_html=True)
st.markdown("**AI-Animated Educational Video Generator** — Neural Networks & more")

# PHASE: INPUT
if st.session_state.phase == "input":
    st.markdown("### 📥 Create Your Video Series")
    c1, c2 = st.columns([2,1])
    with c1:
        topic = st.text_input("Topic", value="Neural Networks & Deep Learning")
        urls = st.text_area("Reference URLs (one per line)", value="https://en.wikipedia.org/wiki/Neural_network_(machine_learning)", height=80)
        tone = st.selectbox("Audience", ["friendly and educational for beginners",
            "technical for university students","professional and concise","fun for high-school students"])
    with c2:
        num_videos = st.slider("Videos", 1, 5, 3)
        st.markdown("**Each video:** 1 minute")
        st.markdown(f"📝 ~**{150*num_videos:,}** words total")
        st.info(f"🎬 **{num_videos}** × 1 min = **{num_videos} min** series")
    if st.button("🚀 Generate Series", type="primary", use_container_width=True):
        ref_urls = [u.strip() for u in urls.split("\n") if u.strip()]
        with st.spinner("Phase 1: Research → Curriculum → Scripts..."):
            try:
                state = run_pipeline_phase1(topic, num_videos, 1, ref_urls, tone)
                st.session_state.pipeline_state = state
                st.session_state.phase = "approve"
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
                import traceback; st.code(traceback.format_exc())

# PHASE: APPROVE
elif st.session_state.phase == "approve":
    state = st.session_state.pipeline_state
    scripts = state.get("scripts", [])
    st.markdown("### 👤 Review Scripts")
    st.info(f"**{len(scripts)} scripts** ready. Approve or reject each before production.")
    if not scripts:
        st.warning("No scripts generated.")
        if st.button("← Back"): st.session_state.phase = "input"; st.rerun()
    else:
        tabs = st.tabs([f"Video {s['video_number']}: {s.get('title','')}" for s in scripts])
        for tab, script in zip(tabs, scripts):
            with tab:
                vn = script["video_number"]
                st.markdown(f"#### {script.get('title','')}")
                st.markdown(f"Scenes: {len(script.get('scenes',[]))} | Words: {script.get('total_word_count','?')}")
                for sc in script.get("scenes",[]):
                    with st.expander(f"Scene {sc.get('scene_number','?')} ({sc.get('estimated_duration_seconds','?')}s)"):
                        st.write(sc.get("narration",""))
                        vd = sc.get("visual_direction",{})
                        if isinstance(vd,dict):
                            st.markdown(f"**Animation:** {vd.get('animation_prompt','N/A')}")
                            st.markdown(f"**Avatar mode:** {'Yes' if vd.get('avatar_mode') else 'No'}")
                dec = st.radio(f"Decision", ["Approve","Reject"], key=f"d_{vn}", horizontal=True)
                fb = st.text_input("Feedback", key=f"fb_{vn}")
                st.session_state.hil_decisions[vn] = {"decision":dec, "feedback":fb}
        st.markdown("---")
        approved = sum(1 for d in st.session_state.hil_decisions.values() if d["decision"]=="Approve")
        c1,c2 = st.columns(2)
        with c1:
            if st.button("← Back"): st.session_state.phase = "input"; st.session_state.pipeline_state = None; st.rerun()
        with c2:
            if st.button(f"✅ Produce {approved} Videos", type="primary", use_container_width=True, disabled=approved==0):
                hil = HiLGateState(**state.get("hil_state",{}))
                for vn, d in st.session_state.hil_decisions.items():
                    hil.submit_review(vn, HiLDecision.APPROVED if d["decision"]=="Approve" else HiLDecision.REJECTED, d.get("feedback",""))
                state["hil_state"] = hil.model_dump(); state["hil_pending"] = False
                st.session_state.pipeline_state = state; st.session_state.phase = "phase2"; st.rerun()

# PHASE 2
elif st.session_state.phase == "phase2":
    with st.spinner("Phase 2: AI Animation → TTS → Video Compositing → Post-Production..."):
        try:
            result = run_pipeline_phase2(st.session_state.pipeline_state)
            st.session_state.pipeline_state = result; st.session_state.phase = "done"; st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# PHASE: DONE
elif st.session_state.phase == "done":
    state = st.session_state.pipeline_state
    finals = state.get("final_videos",[])
    st.markdown("### 🎉 Series Complete!")
    if finals:
        st.success(f"**{len(finals)} videos** generated!")
        for v in finals:
            with st.expander(f"🎬 Video {v.get('video_number')}: {v.get('title','')}", expanded=True):
                st.markdown(f"Duration: {v.get('duration_seconds',0):.0f}s | Path: `{v.get('path','')}`")
                p = v.get("path","")
                if os.path.exists(p) and os.path.getsize(p) > 2000:
                    try: st.video(p)
                    except: st.info("Preview not available (mock mode)")
                else: st.info("📁 File at outputs/videos/")
                if os.path.exists(p):
                    with open(p,"rb") as f:
                        st.download_button(f"⬇️ Download", f.read(), f"animalearn_video_{v.get('video_number')}.mp4", "video/mp4")
    c1,c2,c3 = st.columns(3)
    c1.metric("Videos", len(finals))
    c2.metric("Duration", f"{sum(v.get('duration_seconds',0) for v in finals):.0f}s")
    c3.metric("Steps", state.get("step_count",0))
    if st.button("🔄 New Series", type="primary"):
        st.session_state.phase = "input"; st.session_state.pipeline_state = None
        st.session_state.hil_decisions = {}; st.rerun()

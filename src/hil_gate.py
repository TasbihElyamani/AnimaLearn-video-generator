"""AnimaLearn — Human-in-the-Loop Gate"""
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class HiLDecision(str, Enum):
    APPROVED = "approved"; REJECTED = "rejected"; EDITED = "edited"; PENDING = "pending"

class ScriptReview(BaseModel):
    video_number: int
    decision: HiLDecision = HiLDecision.PENDING
    feedback: str = ""
    edited_script: Optional[dict] = None

class HiLGateState(BaseModel):
    reviews: dict[int, ScriptReview] = Field(default_factory=dict)
    all_reviewed: bool = False

    def submit_review(self, vnum, decision, feedback="", edited_script=None):
        self.reviews[vnum] = ScriptReview(video_number=vnum, decision=decision, feedback=feedback, edited_script=edited_script)
        self.all_reviewed = all(r.decision != HiLDecision.PENDING for r in self.reviews.values()) if self.reviews else False

    def get_approved_videos(self):
        return [r.video_number for r in self.reviews.values() if r.decision in (HiLDecision.APPROVED, HiLDecision.EDITED)]

    def get_rejected_videos(self):
        return [r.video_number for r in self.reviews.values() if r.decision == HiLDecision.REJECTED]

    def get_script_for_production(self, vnum, original):
        r = self.reviews.get(vnum)
        if not r or r.decision == HiLDecision.PENDING: return None
        if r.decision == HiLDecision.REJECTED: return None
        if r.decision == HiLDecision.EDITED and r.edited_script: return r.edited_script
        return original

def initialize_hil_gate(num_videos):
    state = HiLGateState()
    for i in range(1, num_videos + 1):
        state.reviews[i] = ScriptReview(video_number=i)
    return state

def format_script_for_review(script):
    lines = [f"═══ Video {script.get('video_number','?')} : {script.get('title','Untitled')} ═══", ""]
    for s in script.get("scenes", []):
        lines.append(f"  Scene {s.get('scene_number','?')}: {s.get('narration','')[:100]}...")
        lines.append(f"  Visual: {s.get('visual_direction',{}).get('animation_prompt','N/A')}")
        lines.append("")
    return "\n".join(lines)

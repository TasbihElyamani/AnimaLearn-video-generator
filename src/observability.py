"""AnimaLearn — Observability & Structured Logging"""
from __future__ import annotations
import uuid, json, time
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
import structlog
from src.settings import LOG_FILE

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.processors.JSONRenderer()],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

def generate_trace_id() -> str:
    return f"trace_{uuid.uuid4().hex[:12]}"

class PipelineTracer:
    def __init__(self, trace_id: str | None = None):
        self.trace_id = trace_id or generate_trace_id()
        self.start_time = time.time()
        self.events: list[dict] = []
        self._log = structlog.get_logger().bind(trace_id=self.trace_id)
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    def log(self, agent: str, event: str, event_type: str = "info", details: dict | None = None) -> dict:
        entry = {
            "trace_id": self.trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.time() - self.start_time, 3),
            "agent": agent, "event": event, "event_type": event_type,
            **(details or {}),
        }
        self.events.append(entry)
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
        self._log.info(event, agent=agent, event_type=event_type, **(details or {}))
        return entry

    def log_tool_call(self, agent, tool_name, params=None, result=None):
        return self.log(agent, f"Tool: {tool_name}", "tool_call",
                        {"tool": tool_name, "params": params or {}, "result_preview": (result or "")[:200]})

    def log_retrieval(self, agent, query, num_results):
        return self.log(agent, f"RAG: {num_results} passages for '{query}'", "retrieval",
                        {"query": query, "num_results": num_results})

    def log_hil_decision(self, video_number, decision, feedback=""):
        return self.log("HiL Gate", f"Script {video_number}: {decision}", "hil_decision",
                        {"video_number": video_number, "decision": decision, "feedback": feedback})

    def log_generation(self, agent, artifact, path):
        return self.log(agent, f"Generated: {artifact}", "generation", {"artifact": artifact, "path": path})

    def log_error(self, agent, error, details=None):
        return self.log(agent, f"ERROR: {error}", "error", details)

    def get_summary(self):
        tc = {}
        for e in self.events:
            t = e.get("event_type", "?")
            tc[t] = tc.get(t, 0) + 1
        return {"trace_id": self.trace_id, "total_events": len(self.events),
                "elapsed_seconds": round(time.time() - self.start_time, 2), "event_type_counts": tc}

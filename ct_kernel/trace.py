from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class GraphTraceEvent:
    timestamp: int
    node_id: str
    event_type: str
    input_state_hash: str
    output_hash: str
    dependency_snapshot: list[str]


@dataclass
class TraceEntry:
    trace_id: str
    task: str
    plan: list[str]
    memory_hits: list[dict]
    routing: dict
    prompt: str
    model_output: str
    tool_results: list[dict]
    final_output: str
    final_output_hash: str
    graph_snapshot: dict = field(default_factory=dict)
    graph_events: list[GraphTraceEvent] = field(default_factory=list)
    node_execution_log: list[dict] = field(default_factory=list)


class TraceStore:
    def __init__(self, path: Path = Path(".ct_kernel/traces.jsonl")) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("")

    def write(self, entry: TraceEntry) -> None:
        self.path.write_text(self.path.read_text() + json.dumps(asdict(entry), sort_keys=True) + "\n")

    def list_entries(self) -> list[dict]:
        lines = [line for line in self.path.read_text().splitlines() if line.strip()]
        return [json.loads(line) for line in lines]

    def get(self, trace_id: str) -> dict | None:
        for entry in self.list_entries():
            if entry["trace_id"] == trace_id:
                return entry
        return None

    @staticmethod
    def trace_id_for(task: str, prompt: str) -> str:
        return hashlib.sha256(f"{task}|{prompt}".encode("utf-8")).hexdigest()[:20]

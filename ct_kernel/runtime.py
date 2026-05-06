from __future__ import annotations

import hashlib
import json

from .adapter import adapter_for
from .agent import ExecutionAgent
from .compiler import compile_comptext_to_ast
from .execution_graph import GraphBuilder, GraphExecutor
from .memory import DeterministicMemory
from .planner import build_plan
from .router import DeterministicRouter
from .tools import ToolRegistry
from .trace import GraphTraceEvent, TraceEntry, TraceStore


class KernelRuntime:
    def __init__(self, provider: str = "mock") -> None:
        self.provider = provider
        self.memory = DeterministicMemory()
        self.router = DeterministicRouter()
        self.tools = ToolRegistry()
        self.tools.register("echo", lambda text: text)
        self.trace_store = TraceStore()

    def execute(self, task: str) -> dict:
        adapter = adapter_for(self.provider)
        available = ["mock", "claude", "openai", "local"]
        agent = ExecutionAgent(self.memory, self.router, self.tools)
        agent.bind_adapter(adapter)

        memories = self.memory.retrieve(task, top_k=3)
        plan = build_plan(task)
        route = self.router.route(task, plan, memories, available)
        prompt = agent._build_prompt(task, plan, memories)

        ast = compile_comptext_to_ast(task)
        graph = GraphBuilder().build(ast)
        execution = GraphExecutor().execute(graph, agent.run_step)

        model_output = json.dumps(execution["node_execution_log"], sort_keys=True)
        tool_results = [e["result"]["tool_result"] for e in execution["node_execution_log"] if "result" in e]
        final_output = f"GRAPH:{model_output}\nTOOLS:{tool_results}"
        final_hash = hashlib.sha256(final_output.encode("utf-8")).hexdigest()
        self.memory.store(final_output, {"task": task, "hash": final_hash})

        trace_id = self.trace_store.trace_id_for(task, prompt)
        entry = TraceEntry(
            trace_id=trace_id,
            task=task,
            plan=plan,
            memory_hits=memories,
            routing=route.__dict__,
            prompt=prompt,
            model_output=model_output,
            tool_results=tool_results,
            final_output=final_output,
            final_output_hash=final_hash,
            graph_snapshot=execution["graph_snapshot"],
            graph_events=[GraphTraceEvent(**e) for e in execution["graph_events"]],
            node_execution_log=execution["node_execution_log"],
        )
        self.trace_store.write(entry)
        return {"trace_id": trace_id, "output": final_output, "hash": final_hash}

    def replay(self, trace_id: str) -> dict:
        entry = self.trace_store.get(trace_id)
        if not entry:
            raise ValueError(f"trace not found: {trace_id}")
        events = entry.get("graph_events", [])
        if not events:
            entry["graph_events"] = []
            return entry
        reconstructed = []
        for event in sorted(events, key=lambda e: e.get("timestamp", 0)):
            reconstructed.append({
                "node_id": event.get("node_id"),
                "event_type": event.get("event_type"),
                "output_hash": event.get("output_hash", ""),
            })
        entry["replayed_from_events"] = reconstructed
        return entry

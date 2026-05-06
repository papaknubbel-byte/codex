from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .adapter import ModelAdapter
from .memory import DeterministicMemory
from .planner import build_plan
from .router import DeterministicRouter
from .tools import ToolRegistry


@dataclass
class AgentResult:
    task: str
    plan: list[str]
    memories: list[dict]
    route: dict
    prompt: str
    model_output: str
    tool_results: list[dict]
    final_output: str
    final_output_hash: str


class ExecutionAgent:
    def __init__(self, memory: DeterministicMemory, router: DeterministicRouter, tools: ToolRegistry) -> None:
        self.memory = memory
        self.router = router
        self.tools = tools
        self._adapter: ModelAdapter | None = None

    def bind_adapter(self, adapter: ModelAdapter) -> None:
        self._adapter = adapter

    def run_step(self, payload: dict) -> dict:
        if self._adapter is None:
            raise ValueError("adapter not bound")
        task = payload["task"]
        prompt = "\n".join(["CT-KERNEL graph step", f"TASK: {task}", f"NODE: {payload['node_id']}"])
        model_output = self._adapter.generate(prompt, payload)
        tool_result = self.tools.execute("echo", text=task)
        return {"prompt": prompt, "model_output": model_output, "tool_result": tool_result}

    def run(self, task: str, adapter: ModelAdapter, adapters_available: list[str]) -> AgentResult:
        memories = self.memory.retrieve(task, top_k=3)
        plan = build_plan(task)
        route = self.router.route(task, plan, memories, adapters_available)
        prompt = self._build_prompt(task, plan, memories)
        model_output = adapter.generate(prompt, {"task": task, "plan": plan, "memories": memories})
        tool_results = [self.tools.execute("echo", text=task)]
        final_output = f"{model_output}\nTOOLS:{tool_results}"
        final_hash = hashlib.sha256(final_output.encode("utf-8")).hexdigest()
        self.memory.store(final_output, {"task": task, "hash": final_hash})
        return AgentResult(task, plan, memories, route.__dict__, prompt, model_output, tool_results, final_output, final_hash)

    def _build_prompt(self, task: str, plan: list[str], memories: list[dict]) -> str:
        mem_lines = [f"- {m['id']}:{m['score']}:{m['content'][:80]}" for m in memories]
        plan_lines = [f"- {step}" for step in plan]
        return "\n".join([
            "CT-KERNEL deterministic prompt",
            f"TASK: {task}",
            "PLAN:",
            *plan_lines,
            "MEMORIES:",
            *(mem_lines or ["- none"]),
        ])

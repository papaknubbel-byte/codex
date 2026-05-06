from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RouteDecision:
    chosen_adapter: str
    scores: dict[str, int]


class DeterministicRouter:
    def route(self, task: str, plan: list[str], memories: list[dict], available: list[str]) -> RouteDecision:
        token_count = len(task.split())
        plan_size = len(plan)
        memory_signal = sum(item.get("score", 0) for item in memories)
        scores: dict[str, int] = {}
        for name in available:
            base = 50 if name == "mock" else 10
            scores[name] = base + token_count + (2 * plan_size) + memory_signal
        chosen = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        return RouteDecision(chosen_adapter=chosen, scores=scores)

from __future__ import annotations

import re


def _normalize(task: str) -> str:
    return " ".join(task.strip().split())


def build_plan(task: str) -> list[str]:
    normalized = _normalize(task)
    if not normalized:
        return ["step 0: parse intent", "step 1: return no-op output"]

    groups = build_plan_groups(task)
    steps: list[str] = []
    for group in groups:
        for part in group:
            steps.append(f"step {len(steps) + 1}: process {part}")

    if len(steps) < 2:
        steps.insert(0, "step 0: parse intent")
    if len(steps) > 6:
        steps = steps[:6]
    return steps


def build_plan_groups(task: str) -> list[list[str]]:
    normalized = _normalize(task)
    if not normalized:
        return [["no-op output"]]

    then_groups = [g.strip(" ,.;") for g in re.split(r"\bTHEN\b", normalized, flags=re.IGNORECASE)]
    grouped_steps: list[list[str]] = []
    for group in then_groups:
        if not group:
            continue
        branch_parts = [p.strip(" ,.;") for p in re.split(r"\bAND\b|,", group, flags=re.IGNORECASE)]
        branch_parts = [p for p in branch_parts if p]
        if branch_parts:
            grouped_steps.append(branch_parts)

    return grouped_steps or [[normalized]]

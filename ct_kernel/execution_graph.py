from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from .ast import CompTextAST, ParallelNode, SequenceNode, TaskNode

PENDING = "PENDING"
READY = "READY"
RUNNING = "RUNNING"
SUCCESS = "SUCCESS"
FAILED = "FAILED"
SKIPPED = "SKIPPED"


@dataclass
class Node:
    id: str
    task: dict[str, Any]
    dependencies: list[str]
    depth: int
    status: str = PENDING
    result: Any = None
    error: str | None = None


@dataclass
class ExecutionGraph:
    nodes: dict[str, Node] = field(default_factory=dict)

    def validate_dag(self) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def dfs(node_id: str) -> None:
            if node_id in visited:
                return
            if node_id in visiting:
                raise ValueError(f"cycle detected at {node_id}")
            visiting.add(node_id)
            for dep in self.nodes[node_id].dependencies:
                dfs(dep)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in sorted(self.nodes):
            dfs(node_id)

    def frontier(self) -> list[Node]:
        ready: list[Node] = []
        for node_id in sorted(self.nodes):
            node = self.nodes[node_id]
            if node.status != PENDING:
                continue
            if all(self.nodes[dep].status == SUCCESS for dep in node.dependencies):
                node.status = READY
                ready.append(node)
        return sorted(ready, key=lambda n: (n.depth, n.id))


class GraphBuilder:
    def __init__(self) -> None:
        self._counter = 0

    def _new_id(self) -> str:
        self._counter += 1
        return f"n{self._counter:03d}"

    def build(self, ast: CompTextAST) -> ExecutionGraph:
        nodes: dict[str, Node] = {}

        def walk(node: CompTextAST, prev: list[str], depth: int) -> list[str]:
            if isinstance(node, TaskNode):
                node_id = self._new_id()
                nodes[node_id] = Node(id=node_id, task={"action": node.value}, dependencies=list(prev), depth=depth)
                return [node_id]
            if isinstance(node, ParallelNode):
                tails: list[str] = []
                for child in node.children:
                    tails.extend(walk(child, list(prev), depth + 1))
                return sorted(tails)
            if isinstance(node, SequenceNode):
                tails = list(prev)
                for child in node.children:
                    tails = walk(child, tails, depth + 1)
                return tails
            raise ValueError("unsupported AST node")

        walk(ast, [], 0)
        graph = ExecutionGraph(nodes=nodes)
        graph.validate_dag()
        return graph


class GraphExecutor:
    def execute(self, graph: ExecutionGraph, run_step) -> dict:
        graph.validate_dag()
        events: list[dict] = []
        log: list[dict] = []
        t = 0
        running: set[str] = set()

        def state_hash(node: Node) -> str:
            data = {"id": node.id, "task": node.task, "dependencies": node.dependencies, "status": node.status}
            return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

        while any(n.status in {PENDING, READY, RUNNING} for n in graph.nodes.values()):
            frontier = graph.frontier()
            if not frontier:
                break
            for node in frontier:
                if node.id in running or node.status == SUCCESS:
                    continue
                running.add(node.id)
                t += 1
                dep_snap = [f"{d}:{graph.nodes[d].status}" for d in node.dependencies]
                in_hash = state_hash(node)
                events.append({"timestamp": t, "node_id": node.id, "event_type": "node_start", "input_state_hash": in_hash, "output_hash": "", "dependency_snapshot": dep_snap})
                node.status = RUNNING
                try:
                    node.result = run_step({"task": node.task["action"], "node_id": node.id})
                    node.status = SUCCESS
                    out_hash = hashlib.sha256(json.dumps(node.result, sort_keys=True).encode()).hexdigest()
                    t += 1
                    events.append({"timestamp": t, "node_id": node.id, "event_type": "node_success", "input_state_hash": in_hash, "output_hash": out_hash, "dependency_snapshot": dep_snap})
                    log.append({"node_id": node.id, "status": node.status, "result": node.result, "output_hash": out_hash})
                except Exception as exc:
                    node.status = FAILED
                    node.error = str(exc)
                    out_hash = hashlib.sha256(node.error.encode()).hexdigest()
                    t += 1
                    events.append({"timestamp": t, "node_id": node.id, "event_type": "node_failure", "input_state_hash": in_hash, "output_hash": out_hash, "dependency_snapshot": dep_snap})
                    log.append({"node_id": node.id, "status": node.status, "error": node.error, "output_hash": out_hash})
                    for dep_id, dep_node in sorted(graph.nodes.items()):
                        if node.id in dep_node.dependencies and dep_node.status == PENDING:
                            dep_node.status = SKIPPED
                            dep_node.error = "skipped_due_to_failure"
                            t += 1
                            skip_hash = hashlib.sha256(dep_node.error.encode()).hexdigest()
                            skip_dep = [f"{d}:{graph.nodes[d].status}" for d in dep_node.dependencies]
                            events.append({"timestamp": t, "node_id": dep_node.id, "event_type": "node_skipped", "input_state_hash": state_hash(dep_node), "output_hash": skip_hash, "dependency_snapshot": skip_dep})
                running.remove(node.id)

        snapshot = {
            node_id: {
                "task": node.task,
                "dependencies": node.dependencies,
                "status": node.status,
                "result": node.result,
                "error": node.error,
                "depth": node.depth,
            }
            for node_id, node in sorted(graph.nodes.items())
        }
        return {"graph_snapshot": snapshot, "graph_events": events, "node_execution_log": log}

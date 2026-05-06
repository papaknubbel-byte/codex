from __future__ import annotations

from .ast import CompTextAST, ParallelNode, SequenceNode, TaskNode


def _normalize(text: str) -> str:
    return " ".join(text.strip().split())


def _split_preserve(text: str, token: str) -> list[str]:
    parts = text.split(token)
    return [part.strip(" ,.;") for part in parts if part.strip(" ,.;")]


def _parse_parallel(segment: str) -> CompTextAST:
    comma_parts: list[str] = []
    for part in _split_preserve(segment, "AND"):
        comma_parts.extend(_split_preserve(part, ","))
    tasks = tuple(TaskNode(value=p) for p in comma_parts if p)
    if len(tasks) == 1:
        return tasks[0]
    return ParallelNode(children=tasks)


def compile_comptext_to_ast(user_input: str) -> CompTextAST:
    normalized = _normalize(user_input)
    if not normalized:
        return SequenceNode(children=(TaskNode("parse intent"), TaskNode("return no-op output")))

    seq_parts = _split_preserve(normalized, "THEN")
    seq_nodes = tuple(_parse_parallel(part) for part in seq_parts)
    if len(seq_nodes) == 1:
        return seq_nodes[0]
    return SequenceNode(children=seq_nodes)

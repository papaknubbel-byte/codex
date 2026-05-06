from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompTextAST:
    pass


@dataclass(frozen=True)
class TaskNode(CompTextAST):
    value: str


@dataclass(frozen=True)
class SequenceNode(CompTextAST):
    children: tuple[CompTextAST, ...]


@dataclass(frozen=True)
class ParallelNode(CompTextAST):
    children: tuple[CompTextAST, ...]

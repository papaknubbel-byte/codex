from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


@dataclass
class MemoryItem:
    id: str
    content: str
    metadata: dict
    tokens: list[str]


@dataclass
class DeterministicMemory:
    path: Path = Path(".ct_kernel/memory.json")
    items: list[MemoryItem] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            raw = json.loads(self.path.read_text())
            self.items = [MemoryItem(**item) for item in raw]

    def _persist(self) -> None:
        payload = [item.__dict__ for item in self.items]
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def store(self, content: str, metadata: dict) -> str:
        token_list = tokenize(content)
        base = json.dumps({"content": content, "metadata": metadata}, sort_keys=True)
        item_id = hashlib.sha256(base.encode("utf-8")).hexdigest()
        self.items.append(MemoryItem(id=item_id, content=content, metadata=metadata, tokens=token_list))
        self._persist()
        return item_id

    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        q_tokens = set(tokenize(query))
        scored: list[tuple[int, str, MemoryItem]] = []
        for item in self.items:
            overlap = len(q_tokens.intersection(item.tokens))
            tie_break = item.id
            scored.append((overlap, tie_break, item))
        scored.sort(key=lambda x: (-x[0], x[1]))
        out = []
        for score, _, item in scored[:top_k]:
            out.append({"id": item.id, "content": item.content, "metadata": item.metadata, "score": score})
        return out

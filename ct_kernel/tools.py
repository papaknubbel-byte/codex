from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolRegistry:
    tools: dict[str, callable] = field(default_factory=dict)

    def register(self, name: str, fn: callable) -> None:
        self.tools[name] = fn

    def execute(self, name: str, **kwargs) -> dict:
        fn = self.tools.get(name)
        if fn is None:
            return {"tool": name, "status": "missing", "result": None}
        result = fn(**kwargs)
        return {"tool": name, "status": "ok", "result": result}

from __future__ import annotations

import json
from pathlib import Path

from ct_kernel.runtime import KernelRuntime
from ct_kernel.trace import TraceStore

STATE_PATH = Path(".ct_kernel/state.json")


def _load_provider() -> str:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text()).get("provider", "mock")
    return "mock"


def _save_provider(provider: str) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps({"provider": provider}, sort_keys=True, indent=2))


def run(task: str, debug: bool = False) -> dict:
    runtime = KernelRuntime(provider=_load_provider())
    result = runtime.execute(task)
    if debug:
        trace = runtime.replay(result["trace_id"])
        result["debug"] = trace
    return result


def replay(trace_id: str) -> dict:
    runtime = KernelRuntime(provider=_load_provider())
    return runtime.replay(trace_id)


def attach_model(provider: str) -> dict:
    _save_provider(provider)
    return {"attached_provider": provider}


def trace_show() -> list[dict]:
    return TraceStore().list_entries()

from __future__ import annotations

import hashlib
from dataclasses import dataclass


class ModelAdapter:
    """Model adapter interface for deterministic text generation."""

    name = "base"

    def generate(self, prompt: str, context: dict) -> str:
        raise NotImplementedError


@dataclass
class MockAdapter(ModelAdapter):
    name: str = "mock"

    def generate(self, prompt: str, context: dict) -> str:
        digest = hashlib.sha256(f"{prompt}|{context}".encode("utf-8")).hexdigest()[:16]
        plan = context.get("plan", [])
        joined = " | ".join(plan) if plan else "no-plan"
        return f"MOCK[{digest}]::{joined}"


@dataclass
class ClaudeAdapter(ModelAdapter):
    name: str = "claude"

    def generate(self, prompt: str, context: dict) -> str:
        return f"UNAVAILABLE[{self.name}]::{hashlib.sha256(prompt.encode()).hexdigest()[:16]}"


@dataclass
class OpenAIAdapter(ModelAdapter):
    name: str = "openai"

    def generate(self, prompt: str, context: dict) -> str:
        return f"UNAVAILABLE[{self.name}]::{hashlib.sha256(prompt.encode()).hexdigest()[:16]}"


@dataclass
class LocalAdapter(ModelAdapter):
    name: str = "local"

    def generate(self, prompt: str, context: dict) -> str:
        return f"UNAVAILABLE[{self.name}]::{hashlib.sha256(prompt.encode()).hexdigest()[:16]}"


def adapter_for(provider: str) -> ModelAdapter:
    providers = {
        "mock": MockAdapter(),
        "claude": ClaudeAdapter(),
        "openai": OpenAIAdapter(),
        "local": LocalAdapter(),
    }
    return providers.get(provider.lower(), MockAdapter())

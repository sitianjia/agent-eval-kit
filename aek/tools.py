"""Tool registry — define mock tools that an agent can call during eval."""
from __future__ import annotations

import inspect
import json
import time
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]      # JSON schema
    fn: Callable[..., Any]
    latency_ms: float = 0.0
    fail_rate: float = 0.0          # synthetic flake for resilience tests

    def call(self, **kwargs) -> Any:
        if self.latency_ms > 0:
            time.sleep(self.latency_ms / 1000)
        if self.fail_rate > 0:
            import random
            if random.random() < self.fail_rate:
                raise RuntimeError(f"synthetic failure in tool '{self.name}'")
        return self.fn(**kwargs)


class ToolRegistry:
    """Holds tool specs and produces OpenAI/Anthropic-style tool definitions."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> "ToolRegistry":
        if spec.name in self._tools:
            raise ValueError(f"tool '{spec.name}' already registered")
        self._tools[spec.name] = spec
        return self

    def get(self, name: str) -> ToolSpec:
        return self._tools[name]

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> list[str]:
        return sorted(self._tools)

    def openai_schema(self) -> list[dict]:
        """Return tools formatted for OpenAI chat.completions API."""
        return [{
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        } for t in self._tools.values()]

    def anthropic_schema(self) -> list[dict]:
        return [{
            "name": t.name,
            "description": t.description,
            "input_schema": t.parameters,
        } for t in self._tools.values()]


def tool(name: str | None = None, description: str = "",
         latency_ms: float = 0.0, fail_rate: float = 0.0):
    """Decorator: turn a Python function into a ToolSpec.

    Parameters are inferred from the function signature; for now we only
    support simple types (str/int/float/bool/list/dict).
    """
    def deco(fn: Callable) -> ToolSpec:
        sig = inspect.signature(fn)
        props = {}
        required = []
        for pname, p in sig.parameters.items():
            ann = p.annotation if p.annotation is not inspect._empty else str
            props[pname] = {"type": _py_to_json(ann)}
            if p.default is inspect._empty:
                required.append(pname)
        params = {
            "type": "object",
            "properties": props,
            "required": required,
        }
        return ToolSpec(
            name=name or fn.__name__,
            description=description or (fn.__doc__ or "").strip().split("\n")[0],
            parameters=params,
            fn=fn,
            latency_ms=latency_ms,
            fail_rate=fail_rate,
        )
    return deco


_JSON_TYPES = {
    str: "string", int: "integer", float: "number",
    bool: "boolean", list: "array", dict: "object",
}


def _py_to_json(t: Any) -> str:
    return _JSON_TYPES.get(t, "string")

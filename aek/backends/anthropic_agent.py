"""Anthropic Claude variant of the agent loop."""
from __future__ import annotations

import json
import os
import time
from typing import Any

from ..schema import Case, Trace, Step, ToolCall
from ..tools import ToolRegistry


class AnthropicAgent:
    def __init__(
        self,
        registry: ToolRegistry,
        model: str = "claude-3-5-sonnet-latest",
        api_key_env: str = "ANTHROPIC_API_KEY",
        max_steps: int = 12,
        temperature: float = 0.0,
    ) -> None:
        try:
            import anthropic
        except ImportError as e:
            raise ImportError("pip install anthropic") from e
        self.client = anthropic.Anthropic(api_key=os.environ.get(api_key_env))
        self.registry = registry
        self.model = model
        self.max_steps = max_steps
        self.temperature = temperature

    def run(self, case: Case) -> Trace:
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": case.instruction
             + (f"\n\nInputs: {json.dumps(case.inputs)}" if case.inputs else "")},
        ]
        trace = Trace(case_id=case.id)
        trace.steps.append(Step(role="user", content=messages[0]["content"]))

        t0 = time.perf_counter()
        for _ in range(self.max_steps):
            t_step = time.perf_counter()
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                tools=self.registry.anthropic_schema() or None,
                messages=messages,
                temperature=self.temperature,
            )
            elapsed = (time.perf_counter() - t_step) * 1000

            text_parts = []
            tcs: list[ToolCall] = []
            for block in resp.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tcs.append(ToolCall(name=block.name, arguments=block.input,
                                        id=block.id))

            trace.steps.append(Step(
                role="assistant",
                content="\n".join(text_parts),
                tool_calls=tcs, elapsed_ms=elapsed,
            ))
            if resp.usage:
                trace.total_input_tokens += resp.usage.input_tokens
                trace.total_output_tokens += resp.usage.output_tokens

            if resp.stop_reason != "tool_use":
                trace.final_answer = "\n".join(text_parts)
                trace.succeeded = True
                break

            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for tc in tcs:
                if tc.name not in self.registry:
                    out = f"ERROR: unknown tool '{tc.name}'"
                else:
                    try:
                        result = self.registry.get(tc.name).call(**tc.arguments)
                        out = json.dumps(result) if not isinstance(result, str) else result
                    except Exception as e:
                        out = f"ERROR: {type(e).__name__}: {e}"
                trace.steps.append(Step(role="tool", content=out,
                                        tool_call_id=tc.id))
                tool_results.append({"type": "tool_result",
                                     "tool_use_id": tc.id, "content": out})
            messages.append({"role": "user", "content": tool_results})

        trace.total_elapsed_ms = (time.perf_counter() - t0) * 1000
        return trace

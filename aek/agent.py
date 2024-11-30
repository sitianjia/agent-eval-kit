"""A reference agent loop — feeds tools to an OpenAI-compatible chat API.

Kept deliberately minimal. The eval harness is what we actually care about;
the agent here is just a known-good baseline you can swap out.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any

from .schema import Case, Trace, Step, ToolCall
from .tools import ToolRegistry


class Agent:
    def __init__(
        self,
        registry: ToolRegistry,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
        max_steps: int = 12,
        temperature: float = 0.0,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("pip install openai") from e
        self.client = OpenAI(
            base_url=base_url,
            api_key=os.environ.get(api_key_env, "EMPTY"),
        )
        self.registry = registry
        self.model = model
        self.max_steps = max_steps
        self.temperature = temperature

    def run(self, case: Case) -> Trace:
        messages: list[dict[str, Any]] = []
        if case.meta.get("system_prompt"):
            messages.append({"role": "system",
                             "content": case.meta["system_prompt"]})
        user_content = case.instruction
        if case.inputs:
            user_content += "\n\nInputs:\n" + json.dumps(case.inputs, indent=2)
        messages.append({"role": "user", "content": user_content})

        trace = Trace(case_id=case.id)
        trace.steps.append(Step(role="user", content=user_content))

        t0 = time.perf_counter()
        for step_i in range(self.max_steps):
            t_step = time.perf_counter()
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.registry.openai_schema() or None,
                temperature=self.temperature,
            )
            msg = resp.choices[0].message
            elapsed = (time.perf_counter() - t_step) * 1000

            tcs: list[ToolCall] = []
            for tc in (msg.tool_calls or []):
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {"_raw": tc.function.arguments}
                tcs.append(ToolCall(name=tc.function.name,
                                    arguments=args, id=tc.id))

            trace.steps.append(Step(
                role="assistant",
                content=msg.content or "",
                tool_calls=tcs,
                elapsed_ms=elapsed,
            ))
            trace.total_input_tokens += (resp.usage.prompt_tokens
                                         if resp.usage else 0)
            trace.total_output_tokens += (resp.usage.completion_tokens
                                          if resp.usage else 0)

            if not tcs:
                trace.final_answer = msg.content or ""
                trace.succeeded = True
                break

            messages.append({
                "role": "assistant", "content": msg.content,
                "tool_calls": [{"id": tc.id, "type": "function",
                                "function": {"name": tc.function.name,
                                             "arguments": tc.function.arguments}}
                               for tc in (msg.tool_calls or [])],
            })

            for tc in tcs:
                if tc.name not in self.registry:
                    result = f"ERROR: unknown tool '{tc.name}'"
                else:
                    try:
                        out = self.registry.get(tc.name).call(**tc.arguments)
                        result = json.dumps(out) if not isinstance(out, str) else out
                    except Exception as e:
                        result = f"ERROR: {type(e).__name__}: {e}"
                trace.steps.append(Step(
                    role="tool", content=result, tool_call_id=tc.id,
                ))
                messages.append({"role": "tool", "content": result,
                                 "tool_call_id": tc.id})

        trace.total_elapsed_ms = (time.perf_counter() - t0) * 1000
        return trace

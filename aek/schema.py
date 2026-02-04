"""Core dataclasses for cases, traces, and verdicts.

Kept independent of OpenAI / Anthropic SDK types so we can adapt.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal, Optional


Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    id: Optional[str] = None


@dataclass
class Step:
    """One turn of the agent loop."""
    role: Role
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: Optional[str] = None
    elapsed_ms: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # drop empty fields to keep jsonl compact
        if not self.tool_calls:
            d.pop("tool_calls")
        if self.tool_call_id is None:
            d.pop("tool_call_id")
        if not self.meta:
            d.pop("meta")
        return d


@dataclass
class Trace:  # noqa: D101
    """A full agent rollout for one case."""
    case_id: str
    steps: list[Step] = field(default_factory=list)
    final_answer: str = ""
    succeeded: bool = False
    total_elapsed_ms: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    meta: dict[str, Any] = field(default_factory=dict)

    def n_tool_calls(self) -> int:
        return sum(len(s.tool_calls) for s in self.steps)

    def tool_names(self) -> list[str]:
        return [tc.name for s in self.steps for tc in s.tool_calls]


@dataclass
class Case:
    """One eval case — what we want the agent to do."""
    id: str
    instruction: str
    inputs: dict[str, Any] = field(default_factory=dict)
    expected_tools: Optional[list[str]] = None       # ordered or unordered
    expected_answer_pattern: Optional[str] = None    # regex or substring
    rubric: Optional[str] = None                     # for LLM-judge mode
    tags: list[str] = field(default_factory=list)
    timeout_s: float = 60.0
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Verdict:
    case_id: str
    passed: bool
    score: float = 0.0
    breakdown: dict[str, float] = field(default_factory=dict)
    notes: str = ""

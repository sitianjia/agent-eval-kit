"""Bootstrap eval cases from production agent traces.

Given a directory of saved traces (from agent-tape or your own logger),
extract candidate cases. This is a starting point — you still need to
hand-review and add expected_* fields.
"""
from __future__ import annotations

import json
from pathlib import Path

from .schema import Case


def cases_from_trace_dir(trace_dir: str | Path,
                         tag: str = "from_prod") -> list[Case]:
    out: list[Case] = []
    for f in sorted(Path(trace_dir).glob("*.json")):
        d = json.loads(f.read_text())
        # first user message becomes the instruction
        user_msg = next((s for s in d.get("steps", [])
                         if s.get("role") == "user"), None)
        if not user_msg:
            continue
        tools = [tc["name"] for s in d.get("steps", [])
                 for tc in s.get("tool_calls", [])]
        out.append(Case(
            id=f.stem,
            instruction=user_msg.get("content", ""),
            expected_tools=list(dict.fromkeys(tools)) or None,
            tags=[tag],
            meta={"bootstrapped_from": str(f)},
        ))
    return out

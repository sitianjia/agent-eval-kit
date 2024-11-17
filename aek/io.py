"""I/O for cases and traces."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, Iterator

import yaml

from .schema import Case, Trace, Step, ToolCall, Verdict


def load_cases(path: str | os.PathLike) -> list[Case]:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix in (".yaml", ".yml"):
        raw = yaml.safe_load(text)
    elif p.suffix == ".json":
        raw = json.loads(text)
    elif p.suffix == ".jsonl":
        raw = [json.loads(l) for l in text.splitlines() if l.strip()]
    else:
        raise ValueError(f"unsupported case file: {p.suffix}")
    if isinstance(raw, dict) and "cases" in raw:
        raw = raw["cases"]
    return [_to_case(d) for d in raw]


def _to_case(d: dict) -> Case:
    keys = {"id", "instruction", "inputs", "expected_tools",
            "expected_answer_pattern", "rubric", "tags",
            "timeout_s", "meta"}
    clean = {k: v for k, v in d.items() if k in keys}
    if "id" not in clean:
        raise ValueError(f"case missing `id`: {d}")
    return Case(**clean)


def save_trace(trace: Trace, path: str | os.PathLike) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    obj = {
        "case_id": trace.case_id,
        "succeeded": trace.succeeded,
        "final_answer": trace.final_answer,
        "total_elapsed_ms": trace.total_elapsed_ms,
        "total_input_tokens": trace.total_input_tokens,
        "total_output_tokens": trace.total_output_tokens,
        "meta": trace.meta,
        "steps": [s.to_dict() for s in trace.steps],
    }
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2))


def load_traces(path: str | os.PathLike) -> Iterator[Trace]:
    p = Path(path)
    if p.is_dir():
        files = sorted(p.glob("*.json"))
    else:
        files = [p]
    for f in files:
        d = json.loads(f.read_text())
        steps = []
        for s in d.get("steps", []):
            tcs = [ToolCall(**tc) for tc in s.get("tool_calls", [])]
            steps.append(Step(
                role=s["role"],
                content=s.get("content", ""),
                tool_calls=tcs,
                tool_call_id=s.get("tool_call_id"),
                elapsed_ms=s.get("elapsed_ms", 0.0),
                meta=s.get("meta", {}),
            ))
        yield Trace(
            case_id=d["case_id"], steps=steps,
            final_answer=d.get("final_answer", ""),
            succeeded=d.get("succeeded", False),
            total_elapsed_ms=d.get("total_elapsed_ms", 0.0),
            total_input_tokens=d.get("total_input_tokens", 0),
            total_output_tokens=d.get("total_output_tokens", 0),
            meta=d.get("meta", {}),
        )


def save_verdicts(verdicts: Iterable[Verdict], path: str | os.PathLike) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        for v in verdicts:
            f.write(json.dumps({
                "case_id": v.case_id, "passed": v.passed,
                "score": v.score, "breakdown": v.breakdown,
                "notes": v.notes,
            }, ensure_ascii=False) + "\n")

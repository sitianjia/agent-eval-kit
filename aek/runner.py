"""Drive a list of cases through the agent and produce verdicts."""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from .agent import Agent
from .schema import Case, Trace, Verdict
from . import checks as checks_mod
from .io import save_trace, save_verdicts


@dataclass
class CheckSpec:
    name: str
    kwargs: dict | None = None
    weight: float = 1.0
    required: bool = True   # if False, failure doesn't fail the case overall


def evaluate(case: Case, trace: Trace, specs: list["CheckSpec"]) -> Verdict:
    v = Verdict(case_id=case.id, passed=True, score=0.0)
    total_w = 0.0
    notes = []
    for spec in specs:
        fn = checks_mod.get(spec.name)
        ok, sub, note = fn(case, trace, **(spec.kwargs or {}))
        notes.append(f"[{spec.name}] {note}")
        v.breakdown[spec.name] = sub
        total_w += spec.weight
        v.score += sub * spec.weight
        if not ok and spec.required:
            v.passed = False
    v.score = v.score / max(total_w, 1)
    v.notes = " | ".join(notes)
    return v


def run_suite(
    cases: list[Case],
    agent: Agent,
    specs: list["CheckSpec"],
    out_dir: str | Path,
    progress_cb: Optional[Callable[[int, int, Verdict], None]] = None,
) -> list[Verdict]:
    out_dir = Path(out_dir)
    (out_dir / "traces").mkdir(parents=True, exist_ok=True)
    verdicts = []
    for i, case in enumerate(cases):
        t0 = time.perf_counter()
        try:
            trace = agent.run(case)
        except Exception as e:
            trace = Trace(case_id=case.id, succeeded=False,
                          meta={"error": f"{type(e).__name__}: {e}"})
        save_trace(trace, out_dir / "traces" / f"{case.id}.json")
        v = evaluate(case, trace, specs)
        v.breakdown["wall_sec"] = time.perf_counter() - t0
        verdicts.append(v)
        if progress_cb:
            progress_cb(i + 1, len(cases), v)
    save_verdicts(verdicts, out_dir / "verdicts.jsonl")
    return verdicts

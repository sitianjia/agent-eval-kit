"""Optional async runner — runs N cases concurrently against the agent.

Beware: agent reliability metrics get noisier under concurrency
(rate limits, retries). Use for throughput, not for grading.
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Callable, Optional

from .agent import Agent
from .schema import Case, Trace, Verdict
from .runner import CheckSpec, evaluate
from .io import save_trace, save_verdicts


async def _run_one(agent: Agent, case: Case, sem: asyncio.Semaphore) -> Trace:
    async with sem:
        return await asyncio.to_thread(agent.run, case)


async def run_suite_async(
    cases: list[Case],
    agent: Agent,
    specs: list[CheckSpec],
    out_dir: str | Path,
    concurrency: int = 4,
    progress_cb: Optional[Callable[[int, int, Verdict], None]] = None,
) -> list[Verdict]:
    out_dir = Path(out_dir)
    (out_dir / "traces").mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(concurrency)
    verdicts: list[Verdict] = []

    async def _do(case: Case) -> Verdict:
        t0 = time.perf_counter()
        trace = await _run_one(agent, case, sem)
        save_trace(trace, out_dir / "traces" / f"{case.id}.json")
        v = evaluate(case, trace, specs)
        v.breakdown["wall_sec"] = time.perf_counter() - t0
        return v

    pending = [asyncio.create_task(_do(c)) for c in cases]
    done = 0
    for fut in asyncio.as_completed(pending):
        v = await fut
        verdicts.append(v)
        done += 1
        if progress_cb:
            progress_cb(done, len(cases), v)

    save_verdicts(verdicts, out_dir / "verdicts.jsonl")
    return verdicts

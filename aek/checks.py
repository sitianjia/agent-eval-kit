"""Built-in checks. Each takes (case, trace) and returns (passed, score, note).

Compose them in YAML or programmatically.
"""
from __future__ import annotations

import re
from typing import Callable, Tuple

from .schema import Case, Trace


CheckResult = Tuple[bool, float, str]
CheckFn = Callable[[Case, Trace], CheckResult]


def answer_matches(case: Case, trace: Trace) -> CheckResult:
    pat = case.expected_answer_pattern
    if not pat:
        return True, 1.0, "no expected pattern, skipped"
    ans = trace.final_answer or ""
    try:
        ok = bool(re.search(pat, ans, re.IGNORECASE))
    except re.error:
        ok = pat.lower() in ans.lower()
    return ok, float(ok), f"pattern={pat!r}"


def used_expected_tools(case: Case, trace: Trace,
                        ordered: bool = False) -> CheckResult:
    exp = case.expected_tools
    if not exp:
        return True, 1.0, "no expected tools, skipped"
    used = trace.tool_names()
    if ordered:
        # subsequence match
        i = 0
        for u in used:
            if i < len(exp) and u == exp[i]:
                i += 1
        ok = i == len(exp)
        return ok, i / len(exp), f"ordered hit={i}/{len(exp)}"
    # multiset coverage
    from collections import Counter
    exp_c, used_c = Counter(exp), Counter(used)
    hit = sum(min(exp_c[t], used_c[t]) for t in exp_c)
    ok = hit == sum(exp_c.values())
    return ok, hit / max(sum(exp_c.values()), 1), f"unordered hit={hit}/{sum(exp_c.values())}"


def no_failed_tool_calls(case: Case, trace: Trace) -> CheckResult:
    bad = [s for s in trace.steps if s.role == "tool"
           and s.content.startswith("ERROR")]
    ok = not bad
    return ok, 1.0 if ok else 0.0, f"{len(bad)} tool errors"


def under_n_steps(case: Case, trace: Trace, n: int = 8) -> CheckResult:
    steps = sum(1 for s in trace.steps if s.role == "assistant")
    ok = steps <= n
    return ok, 1.0 if ok else max(0.0, 1 - (steps - n) / n), f"assistant steps={steps}"


def under_latency(case: Case, trace: Trace,
                  budget_ms: float = 10_000) -> CheckResult:
    ok = trace.total_elapsed_ms <= budget_ms
    return ok, 1.0 if ok else 0.0, f"elapsed={trace.total_elapsed_ms:.0f}ms"


def under_tokens(case: Case, trace: Trace,
                 budget: int = 4_000) -> CheckResult:
    total = trace.total_input_tokens + trace.total_output_tokens
    ok = total <= budget
    return ok, 1.0 if ok else 0.0, f"tokens={total}"


_REGISTRY: dict[str, CheckFn] = {
    "answer_matches": answer_matches,
    "used_expected_tools": used_expected_tools,
    "no_failed_tool_calls": no_failed_tool_calls,
    "under_n_steps": under_n_steps,
    "under_latency": under_latency,
    "under_tokens": under_tokens,
}


def get(name: str) -> CheckFn:
    if name not in _REGISTRY:
        raise KeyError(f"unknown check '{name}'. known: {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def list_checks() -> list[str]:
    return sorted(_REGISTRY)

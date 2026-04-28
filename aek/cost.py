"""Rough cost estimation for a run, based on token counts."""
from __future__ import annotations

from .schema import Trace


# rough rates in USD per 1M tokens, updated occasionally — adjust to your model
_RATES = {
    "gpt-4o":       {"in": 2.50, "out": 10.00},
    "gpt-4o-mini":  {"in": 0.15, "out": 0.60},
    "gpt-4.1":      {"in": 3.00, "out": 12.00},
    "claude-3-5-sonnet-latest": {"in": 3.00, "out": 15.00},
    "claude-3-5-haiku-latest":  {"in": 0.80,  "out": 4.00},
    "claude-3-7-sonnet-latest": {"in": 3.00, "out": 15.00},
    "claude-opus-4":            {"in": 15.00, "out": 75.00},
    "claude-sonnet-4-5":        {"in": 3.00, "out": 15.00},
}


def estimate_usd(trace: Trace, model: str) -> float:
    r = _RATES.get(model, {"in": 0.0, "out": 0.0})
    return (trace.total_input_tokens / 1e6 * r["in"]
            + trace.total_output_tokens / 1e6 * r["out"])


def total_usd(traces, model: str) -> float:
    return sum(estimate_usd(t, model) for t in traces)

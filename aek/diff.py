"""Compare two run directories — show per-case verdict deltas."""
from __future__ import annotations

import json
from pathlib import Path


def load_verdicts(path: str | Path) -> dict[str, dict]:
    out = {}
    p = Path(path) / "verdicts.jsonl"
    if not p.exists():
        return out
    with p.open() as f:
        for line in f:
            d = json.loads(line)
            out[d["case_id"]] = d
    return out


def diff(a_dir: str | Path, b_dir: str | Path) -> dict:
    a = load_verdicts(a_dir)
    b = load_verdicts(b_dir)
    rows = []
    keys = sorted(set(a) | set(b))
    for k in keys:
        av = a.get(k)
        bv = b.get(k)
        if av is None:
            rows.append({"case_id": k, "status": "new", "a": None, "b": bv["passed"]})
        elif bv is None:
            rows.append({"case_id": k, "status": "missing", "a": av["passed"], "b": None})
        else:
            if av["passed"] == bv["passed"]:
                status = "same"
            else:
                status = "regression" if av["passed"] and not bv["passed"] else "fix"
            rows.append({"case_id": k, "status": status,
                         "a": av["passed"], "b": bv["passed"],
                         "score_delta": bv["score"] - av["score"]})
    return {
        "rows": rows,
        "summary": {
            "regressions": sum(1 for r in rows if r["status"] == "regression"),
            "fixes": sum(1 for r in rows if r["status"] == "fix"),
            "same": sum(1 for r in rows if r["status"] == "same"),
        },
    }

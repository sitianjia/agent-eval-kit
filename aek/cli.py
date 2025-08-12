"""`aek` command-line interface."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

from .agent import Agent
from .checks import list_checks
from .io import load_cases
from .runner import CheckSpec, run_suite
from .tools import ToolRegistry


def _load_check_specs(path: str | Path) -> list[CheckSpec]:
    raw = yaml.safe_load(Path(path).read_text())
    out: list[CheckSpec] = []
    for entry in (raw.get("checks", raw) or []):
        if isinstance(entry, str):
            out.append(CheckSpec(name=entry))
        else:
            out.append(CheckSpec(
                name=entry["name"],
                kwargs=entry.get("kwargs"),
                weight=entry.get("weight", 1.0),
                required=entry.get("required", True),
            ))
    return out


def _import_registry(spec: str) -> ToolRegistry:
    """Import `module:attr` and return the registry."""
    mod, attr = spec.split(":")
    import importlib
    return getattr(importlib.import_module(mod), attr)


def main() -> None:
    p = argparse.ArgumentParser(prog="aek")
    sub = p.add_subparsers(dest="cmd")

    rp = sub.add_parser("run", help="run a case suite")
    rp.add_argument("--cases", required=True)
    rp.add_argument("--checks", required=True, help="yaml file with checks")
    rp.add_argument("--tools", required=True, help="module:registry path")
    rp.add_argument("--model", default="gpt-4o-mini")
    rp.add_argument("--base-url", default=None)
    rp.add_argument("--out", default="runs/latest")
    rp.add_argument("--tags", nargs="+", default=None, help="filter cases by tag(s)")

    lp = sub.add_parser("list-checks")

    dp = sub.add_parser("diff", help="compare two run directories")
    dp.add_argument("--a", required=True)
    dp.add_argument("--b", required=True)

    pp = sub.add_parser("report", help="generate html report")
    pp.add_argument("--run", required=True)
    pp.add_argument("--out", default="report.html")


    args = p.parse_args()
    console = Console()

    if args.cmd == "list-checks":
        for c in list_checks():
            console.print(f"  • {c}")
        return



    if args.cmd == "report":
        from .report import write_html
        write_html(args.run, args.out)
        console.print(f"wrote {args.out}")
        return
    if args.cmd == "diff":
        from .diff import diff as _diff
        result = _diff(args.a, args.b)
        for r in result["rows"]:
            color = {"regression": "[red]", "fix": "[green]",
                     "same": "[dim]", "new": "[yellow]",
                     "missing": "[yellow]"}.get(r["status"], "")
            console.print(f"{color}{r['status']:>11s}[/]  {r['case_id']}")
        s = result["summary"]
        console.print(f"\n[bold]regressions={s['regressions']}  fixes={s['fixes']}  same={s['same']}[/]")
        return
    if args.cmd != "run":
        p.print_help()
        sys.exit(2)

    cases = load_cases(args.cases)
    if args.tags:
        cases = [c for c in cases if set(args.tags) & set(c.tags)]
        if not cases:
            console.print("[yellow]no cases match those tags[/]")
            return
    specs = _load_check_specs(args.checks)
    registry = _import_registry(args.tools)
    agent = Agent(registry, model=args.model, base_url=args.base_url)

    def progress(i, n, v):
        mark = "[green]PASS[/]" if v.passed else "[red]FAIL[/]"
        console.print(f"  [{i}/{n}] {mark}  {v.case_id}  score={v.score:.2f}")

    verdicts = run_suite(cases, agent, specs, args.out, progress_cb=progress)

    # summary
    n = len(verdicts)
    passed = sum(v.passed for v in verdicts)
    table = Table(title=f"results — {passed}/{n} passed")
    table.add_column("case_id"); table.add_column("ok"); table.add_column("score")
    for v in verdicts:
        table.add_row(v.case_id,
                      "[green]✓[/]" if v.passed else "[red]✗[/]",
                      f"{v.score:.3f}")
    console.print(table)


if __name__ == "__main__":
    main()

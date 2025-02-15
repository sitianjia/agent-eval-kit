"""Generate a single-file HTML report from a run directory."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path


_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       max-width: 1100px; margin: 2rem auto; padding: 0 1rem; color: #222; }
h1 { border-bottom: 2px solid #eee; padding-bottom: 0.3rem; }
.pass { color: #0a7d24; font-weight: 600; }
.fail { color: #c0392b; font-weight: 600; }
table { border-collapse: collapse; width: 100%; }
th, td { padding: 0.4rem 0.7rem; border-bottom: 1px solid #eee;
         text-align: left; vertical-align: top; }
th { background: #fafafa; }
tr:hover { background: #fcfcfc; }
details { margin: 0.3rem 0; }
pre { background: #f4f4f4; padding: 0.7rem; border-radius: 6px;
      overflow-x: auto; font-size: 0.85rem; }
.tool { color: #1565c0; }
.summary { font-size: 1.1rem; margin: 1rem 0; }
"""


def _render_trace(trace: dict) -> str:
    rows = []
    for s in trace.get("steps", []):
        role = s.get("role", "")
        body = escape(s.get("content", "") or "")
        if s.get("tool_calls"):
            tc = "<br>".join(
                f"<span class='tool'>→ {escape(t['name'])}({escape(json.dumps(t.get('arguments', {})))})</span>"
                for t in s["tool_calls"]
            )
            body = (body + "<br>" + tc) if body else tc
        rows.append(f"<tr><td><b>{escape(role)}</b></td><td>{body}</td></tr>")
    return "<table>" + "".join(rows) + "</table>"


def write_html(run_dir: str | Path, out: str | Path) -> None:
    run = Path(run_dir)
    verdicts = []
    with (run / "verdicts.jsonl").open() as f:
        for line in f:
            verdicts.append(json.loads(line))

    n = len(verdicts)
    passed = sum(v["passed"] for v in verdicts)

    rows_html = []
    for v in verdicts:
        cid = v["case_id"]
        trace_path = run / "traces" / f"{cid}.json"
        trace = json.loads(trace_path.read_text()) if trace_path.exists() else {}
        status = "<span class='pass'>PASS</span>" if v["passed"] \
            else "<span class='fail'>FAIL</span>"
        rows_html.append(f"""
        <tr><td>{escape(cid)}</td>
            <td>{status}</td>
            <td>{v['score']:.3f}</td>
            <td><details><summary>trace</summary>{_render_trace(trace)}</details></td>
            <td>{escape(v.get('notes', ''))}</td></tr>
        """)

    html = f"""<!doctype html><html><head><meta charset='utf-8'>
<title>aek run — {escape(str(run.name))}</title>
<style>{_CSS}</style></head><body>
<h1>aek run — {escape(str(run.name))}</h1>
<div class='summary'>{passed}/{n} passed</div>
<table><thead><tr><th>case</th><th>status</th><th>score</th>
<th>trace</th><th>notes</th></tr></thead>
<tbody>{''.join(rows_html)}</tbody></table>
</body></html>"""
    Path(out).write_text(html, encoding="utf-8")

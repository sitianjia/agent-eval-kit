"""JSON-schema based answer validation.

For agents that are supposed to return structured output, this beats
regex matching.
"""
from __future__ import annotations

import json
import re

from .schema import Case, Trace


def answer_is_valid_json(case: Case, trace: Trace,
                         schema: dict | None = None) -> tuple[bool, float, str]:
    ans = (trace.final_answer or "").strip()
    # tolerate fenced code blocks
    m = re.search(r"```(?:json)?\s*(.+?)```", ans, re.S)
    if m:
        ans = m.group(1).strip()
    try:
        data = json.loads(ans)
    except json.JSONDecodeError as e:
        return False, 0.0, f"invalid json: {e}"
    if not schema:
        return True, 1.0, "json parsed"
    try:
        import jsonschema
        jsonschema.validate(data, schema)
    except ImportError:
        return True, 0.5, "json parsed (jsonschema not installed for validation)"
    except Exception as e:  # noqa: BLE001
        return False, 0.0, f"schema violation: {e}"
    return True, 1.0, "json + schema ok"

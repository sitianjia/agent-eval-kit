"""LLM-as-judge check.

Asks an LLM to score the trace against a rubric. Useful for fuzzy answer
quality. Treat this as one signal among many — never the only one.
"""
from __future__ import annotations

import json
import os
from typing import Optional

from .schema import Case, Trace


_JUDGE_PROMPT = """\
You are evaluating an agent. Given the agent's final answer and the
rubric, output a JSON object {{"passed": bool, "score": 0..1, "note": str}}.

Rubric:
{rubric}

User asked:
{instruction}

Agent's final answer:
{answer}

JSON only, no prose:"""


def llm_judge(case: Case, trace: Trace, model: str = "gpt-4o-mini",
              base_url: Optional[str] = None,
              api_key_env: str = "OPENAI_API_KEY") -> tuple[bool, float, str]:
    if not case.rubric:
        return True, 1.0, "no rubric, skipped"
    from openai import OpenAI
    client = OpenAI(base_url=base_url,
                    api_key=os.environ.get(api_key_env, "EMPTY"))
    prompt = _JUDGE_PROMPT.format(rubric=case.rubric,
                                  instruction=case.instruction,
                                  answer=trace.final_answer)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return False, 0.0, f"judge returned non-json: {raw[:80]}"
    return bool(data.get("passed", False)), float(data.get("score", 0.0)), \
        str(data.get("note", ""))

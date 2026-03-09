# agent-eval-kit
> A small, opinionated eval harness for tool-using LLM agents.

[![Python](https://img.shields.io/badge/python-3.10+-blue)](#)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![status](https://img.shields.io/badge/status-active-brightgreen)](#)

## Overview

If you have ever shipped an LLM agent to production, you know the depressing pattern: the model behaves great in a Jupyter notebook, you deploy it, and a week later three users hit edge cases your prompt-tuning never imagined. By the time you patch the prompt, two new prompts have rotted.

`agent-eval-kit` is the testing harness I wish I had when I first put an agent into a real system. It does four things, badly enough to be useful:

1. **Defines a case file format** — YAML/JSONL cases with instruction, expected tool calls, and answer rubric. Versioned in git.
2. **Runs the agent** with a configurable tool registry against an OpenAI-compatible API.
3. **Scores each case** with composable, deterministic checks — no flaky LLM-as-judge as the only signal.
4. **Records full traces** as structured JSON so you can replay, diff, and root-cause when CI says something regressed.

It is intentionally *not* a benchmark suite. You bring your own tools and cases. The kit handles the rest.

## Architecture

```
┌──────────┐       ┌──────────────┐       ┌──────────────┐
│ cases.yml│──────▶│   Runner     │──────▶│  traces/     │
└──────────┘       │              │       │  *.json      │
                   │   ┌──────┐   │       └──────────────┘
                   │   │Agent │   │              │
                   │   └──┬───┘   │              ▼
                   │      │       │       ┌──────────────┐
                   │      ▼       │       │   Checks     │
                   │  ┌────────┐  │       │ (composable) │
                   │  │ Tools  │  │       └──────┬───────┘
                   │  └────────┘  │              │
                   └──────────────┘              ▼
                                          ┌──────────────┐
                                          │ verdicts.jsonl│
                                          └──────────────┘
```

The runner is single-threaded by design — agent loops are I/O-bound and a clean serial trace is easier to debug than concurrent ones. Throughput comes from running multiple suites in parallel processes, not threading inside one.

## Installation

```bash
git clone https://github.com/sitianjia/agent-eval-kit
cd agent-eval-kit
pip install -r requirements.txt
pip install -e .
```

## Quick Start

The repo ships an `examples/` folder with a toy "fruit calculator" agent.

```bash
export OPENAI_API_KEY=...      # or point base-url at vLLM / Together / etc.

aek run \
    --cases   examples/cases.yaml \
    --checks  examples/checks.yaml \
    --tools   examples.tools_calc:registry \
    --model   gpt-4o-mini \
    --out     runs/baseline
```

You'll see a per-case pass/fail line as it runs, and a summary table at the end. Full traces live under `runs/baseline/traces/`.

## Case format

```yaml
cases:
  - id: cost_calc
    instruction: "If I buy 3 kg of oranges and 2 kg of grapes, how much do I pay?"
    expected_tools: [get_price, get_price, mul, mul, add]
    expected_answer_pattern: "45"
    tags: [arithmetic]
    timeout_s: 30
```

| Field | Required | What it does |
|-------|:--------:|--------------|
| `id` | ✅ | unique slug, used as filename |
| `instruction` | ✅ | what the user asks the agent |
| `inputs` | | extra structured input shown to the agent |
| `expected_tools` | | list of tool names (multiset by default — order-agnostic; pass `ordered: true` to a check) |
| `expected_answer_pattern` | | regex (case-insensitive) over the final answer |
| `rubric` | | freeform string for LLM-judge mode |
| `tags` | | filter / group runs |
| `timeout_s` | | per-case wall budget |

## Built-in checks

`aek list-checks` enumerates them:

- `answer_matches` — regex/substring on `final_answer`
- `used_expected_tools` — coverage of expected tool names (ordered or unordered)
- `no_failed_tool_calls` — no `ERROR:` outputs in the trace
- `under_n_steps` — caps assistant turns
- `under_latency` — wall-clock budget
- `under_tokens` — input + output token budget

Each check is `(case, trace) -> (passed, score, note)`. Add your own by importing `aek.checks` and writing a function with that signature.

## Filtering & tags

Tag cases and run only the subset you care about:

```bash
aek run --cases examples/cases.yaml --checks examples/checks.yaml \
    --tools examples.tools_calc:registry \
    --tags arithmetic compose \
    --out runs/arith
```

## Re-scoring

Because traces are saved verbatim, you can rerun checks without burning API calls:

```python
from aek.io import load_traces, load_cases
from aek.runner import CheckSpec, evaluate

cases = {c.id: c for c in load_cases("examples/cases.yaml")}
specs = [CheckSpec("answer_matches"), CheckSpec("under_n_steps", {"n": 4})]
for trace in load_traces("runs/baseline/traces"):
    v = evaluate(cases[trace.case_id], trace, specs)
    print(trace.case_id, v.passed, v.score)
```

This is the most common workflow in practice — most of my time is spent re-scoring with tighter checks, not re-running the agent.

## Why no LLM-as-judge by default

LLM-judges are useful but noisy. The harness treats them as just another check (one you'd add with `kwargs: { model: gpt-4o }`) — never as the only signal. A failing deterministic check should always tell you something concrete: wrong tool, wrong number, too many steps. LLM-judge can layer on top for fuzzier "did the answer read well" questions.

## What's intentionally missing

- **Concurrency knobs**: keep it serial. Run two suites in parallel shells if you need it.
- **Async**: same reason.
- **Web UI**: traces are JSON. Look at them in your editor.
- **A built-in case zoo**: the cases that matter are yours.

## Cost reporting

Token counts are recorded per trace, so a rough USD estimate is one line:

```python
from aek.cost import total_usd
from aek.io import load_traces

print(f"${total_usd(load_traces('runs/baseline/traces'), 'gpt-4o-mini'):.4f}")
```

Rates are best-effort and live in `aek/cost.py` — adjust them when prices move.

## Roadmap

- [x] Tool registry + decorator
- [x] YAML cases + check composition
- [x] Trace dump / replay
- [x] CLI with rich summary
- [x] LLM-as-judge check (`aek.checks.llm_judge`)
- [x] HTML report generator (`aek report`)
- [x] Diff mode: compare two run directories

## License

Apache 2.0 — see [LICENSE](LICENSE).

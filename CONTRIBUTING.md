# Contributing

PRs welcome. The two highest-value contribution surfaces are:

1. **New checks** — anything `(case, trace) -> (passed, score, note)`. Add it to `aek/checks.py` and register in `_REGISTRY`. Tests appreciated.
2. **New agent backends** — drop a file in `aek/backends/`. Keep the public API to `run(case) -> Trace`.

Run the suite locally before PRing:

```bash
pip install -e ".[dev]"
pytest -q
```

Style: no formatter forced; follow what's there. Type hints encouraged but not mandatory for tiny helpers.

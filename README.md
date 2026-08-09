# Baseball-Thoughts

[![CI](https://github.com/ideksec/Baseball-Thoughts/actions/workflows/ci.yml/badge.svg)](https://github.com/ideksec/Baseball-Thoughts/actions/workflows/ci.yml)

An analytics lab for learning baseball and Python through analysis, reusable code, and small apps. The side project to my side projects.

See [spec.md](spec.md) for the full operating spec, standards, and data policies.

## What's here

- **`baseball_lab`** — a Python package of tested, reusable analysis code:
  - `metrics.batting`: AVG, OBP, SLG, OPS, ISO, BABIP
  - `metrics.pitching`: ERA, WHIP, K/9, BB/9, K/BB, FIP, plus innings-notation conversion
  - `io`, `clean`, `models`, `viz`, `utils`: placeholders for future modules
- **Notebooks** — narrative analyses that use the package (see `notebooks/analysis/`), plus a reusable [template](notebooks/templates/analysis_template.ipynb)
- **Reports** — durable written answers to specific questions (see `reports/`)
- **Docs** — a [metrics glossary](docs/glossary.md) and a [data source catalog](docs/data_sources.md)

## Structure

```
docs/           Durable notes: glossary, sources, conventions
data/           raw/ and interim/ are local-only (gitignored); processed/ for small derivatives
notebooks/      templates/, exploration/, analysis/, modeling/, viz/
reports/        royals/, league/, publishable/
src/            baseball_lab Python package (io, clean, metrics, models, viz, utils)
scripts/        Small executable utilities
apps/           dashboards/, services/
tests/          pytest tests for src/
scratch/        Temporary work — promote, archive, or delete
```

## Getting started

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the package in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests and lint
pytest
ruff check .
```

Quick example:

```python
from baseball_lab.metrics import ops, era, innings_from_notation

ops(singles=30, doubles=10, triples=2, home_runs=8,
    walks=25, hbp=3, at_bats=200, sacrifice_flies=4)   # 0.776...

era(earned_runs=3, innings_pitched=innings_from_notation(6.1))  # 4.26...
```

## Principles

1. **One question, one artifact.** Each unit of work produces a notebook, report, or app.
2. **Reproducible by default.** Results recreatable from code + documented data steps.
3. **Separation of concerns.** Data, code, analysis, and outputs stay in their lanes.
4. **Publishable by default.** Written clearly and defensibly, with data handling explicit.
5. **Messy is allowed, but contained.** Experiments live in `scratch/` and get promoted or removed.

## Data policy

- Never commit large raw datasets — `data/raw/` and `data/interim/` are gitignored.
- Document all sources in [`docs/data_sources.md`](docs/data_sources.md).
- Only commit processed data that is small, reproducible, and license-safe.

## License

[MIT](LICENSE). Note that the license covers the code and writing in this repo; any external data sources have their own terms, cataloged in [`docs/data_sources.md`](docs/data_sources.md).

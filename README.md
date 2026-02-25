# Baseball-Thoughts

A private analytics lab for learning baseball and Python through analysis, reusable code, and small apps. The side project to my side projects.

See [spec.md](spec.md) for the full operating spec, standards, and data policies.

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

# Run tests
pytest
```

## Principles

1. **One question, one artifact.** Each unit of work produces a notebook, report, or app.
2. **Reproducible by default.** Results recreatable from code + documented data steps.
3. **Separation of concerns.** Data, code, analysis, and outputs stay in their lanes.
4. **Private-first.** Clean enough to publish later if desired.
5. **Messy is allowed, but contained.** Experiments live in `scratch/` and get promoted or removed.

## Data policy

- Never commit large raw datasets — `data/raw/` and `data/interim/` are gitignored.
- Document all sources in `docs/data_sources.md`.
- Only commit processed data that is small, reproducible, and license-safe.

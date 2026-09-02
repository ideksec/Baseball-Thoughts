# Baseball-Thoughts

[![CI](https://github.com/ideksec/Baseball-Thoughts/actions/workflows/ci.yml/badge.svg)](https://github.com/ideksec/Baseball-Thoughts/actions/workflows/ci.yml)
[![Publish reports site](https://github.com/ideksec/Baseball-Thoughts/actions/workflows/pages.yml/badge.svg)](https://github.com/ideksec/Baseball-Thoughts/actions/workflows/pages.yml)
[![Pipeline health](https://github.com/ideksec/Baseball-Thoughts/actions/workflows/health.yml/badge.svg)](https://github.com/ideksec/Baseball-Thoughts/actions/workflows/health.yml)

An analytics lab for learning baseball and Python through analysis, reusable code, and small apps. The side project to my side projects.

**📊 Read the daily Royals reports: [ideksec.github.io/Baseball-Thoughts](https://ideksec.github.io/Baseball-Thoughts/)**

Every Royals game is pulled, packaged, and narrated automatically overnight, and the
write-ups are published to that site. See [spec.md](spec.md) for the full operating
spec, standards, and data policies.

## What's here

- **`baseball_lab`** — a Python package of tested, reusable analysis code:
  - `metrics.batting`: AVG, OBP, SLG, OPS, ISO, BABIP
  - `metrics.pitching`: ERA, WHIP, K/9, BB/9, K/BB, FIP, plus innings-notation conversion
  - `metrics.rolling`: rolling and season summaries over the game log — blowout-adjusted
    run differential, feast-or-famine share, streaks
  - `io`: cache-first fetching from the MLB Stats API and Baseball Savant (Statcast)
  - `clean`: GUMBO live-feed and Statcast parsers, plus idempotent season game-log upserts
  - `statpack`: assembles the compact per-game JSON that the daily reports are written from
  - `models`, `viz`, `utils`: placeholders for future modules
- **Reports** — durable written answers to specific questions (see `reports/`):
  - `reports/royals/daily/` — the automated per-game write-ups, also served as the
    [published site](https://ideksec.github.io/Baseball-Thoughts/)
  - `reports/royals/` — longer standalone pieces, e.g. the
    [last-10-games variance themes](reports/royals/2026-07-08_last-10-games-variance-themes.md)
    and the [seven-inning season counterfactual](reports/royals/2026-07-30_seven-inning-season-counterfactual.md)
- **Notebooks** — narrative analyses that use the package (see `notebooks/analysis/`), plus a reusable [template](notebooks/templates/analysis_template.ipynb)
- **Docs** — a [metrics glossary](docs/glossary.md), a [data source catalog](docs/data_sources.md),
  the [pipeline design](docs/data_pipeline.md), and the daily reporter's
  [Routine instructions](docs/ROUTINE_PROMPT.md)

## Structure

```
docs/           Durable notes: glossary, sources, pipeline design, conventions
data/           raw/ and interim/ are local-only (gitignored); processed/ for small derivatives
notebooks/      templates/, exploration/, analysis/, modeling/, viz/
reports/        royals/ (incl. daily/), league/, publishable/
src/            baseball_lab Python package (io, clean, metrics, statpack, models, viz, utils)
scripts/        Small executable utilities: the nightly pull, site builder, health check
apps/           dashboards/, services/
tests/          pytest tests for src/ and scripts/
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

Tests are offline by default — network-touching tests are marked `live` and deselected.
Run them explicitly with `pytest -m live`. CI runs `pytest` and `ruff check .` on Python
3.10 through 3.13.

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

## Automation

Every Royals game produces a published write-up automatically, in three stages:

1. **Nightly stat pack** — [`nightly-royals.yml`](.github/workflows/nightly-royals.yml) runs after each game day, pulls the game from the MLB Stats API and Baseball Savant, and commits a compact per-game JSON to `data/processed/royals/statpacks/` plus a season game-log row. Deterministic Python (`scripts/nightly_royals.py`), fully covered by offline fixture tests.
2. **Morning narrative** — a scheduled Claude session reads any stat pack that lacks a report and writes a themed write-up to `reports/royals/daily/`, following [`docs/ROUTINE_PROMPT.md`](docs/ROUTINE_PROMPT.md). It works entirely from committed data — every number traces back to the stat pack — and pushes the report to `main`.
3. **Published site** — [`pages.yml`](.github/workflows/pages.yml) renders the daily reports to GitHub Pages via [`scripts/build_site.py`](scripts/build_site.py), and deploys to
   **[ideksec.github.io/Baseball-Thoughts](https://ideksec.github.io/Baseball-Thoughts/)**. Stage 2 commits with `[skip ci]`, so the site also rebuilds on a daily schedule rather than relying on the push trigger alone.

Each stage fails quietly on its own — a broken pull writes no stat pack, stage 2 ends
quietly when there are no packs, and a failed deploy just leaves the last good site up.
All three look like a Royals off day, so a fourth workflow watches the seams:
[`health.yml`](.github/workflows/health.yml) runs [`scripts/pipeline_health.py`](scripts/pipeline_health.py)
daily and fails loudly if the game log has gone stale in-season, a logged game has no
stat pack, a stat pack has no report, or the published site is missing the newest report.
Run it yourself any time:

```bash
python scripts/pipeline_health.py            # all four checks
python scripts/pipeline_health.py --offline  # skip the published-site check
```

Design details in [`docs/data_pipeline.md`](docs/data_pipeline.md).

To build the site locally:

```bash
pip install -e ".[site]"
python scripts/build_site.py --out site
# then open site/index.html
```

## Data policy

- Never commit large raw datasets — `data/raw/` and `data/interim/` are gitignored.
- Document all sources in [`docs/data_sources.md`](docs/data_sources.md).
- Only commit processed data that is small, reproducible, and license-safe.

## License

[MIT](LICENSE). Note that the license covers the code and writing in this repo; any external data sources have their own terms, cataloged in [`docs/data_sources.md`](docs/data_sources.md).

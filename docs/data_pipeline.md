# Data Pipeline Design

> Date: 2026-08-09
> Status: proposal — researched and verified as of this date; sources and pricing change, re-verify before major investments

## Goal

Replace ad-hoc web searching and manual recap-reading with a reproducible pipeline for scores, box scores, play-by-play, and pitch-level data — so every report and notebook can pull from cached, structured data instead of news snippets. (Motivating failure: the July 2026 Royals report had to be compiled from cross-checked news recaps because no structured pull existed.)

## Requirements

- Live/recent scores, schedules, linescores, box scores (game-level reports)
- Play-by-play and pitch-level data (deeper analysis, Statcast-style metrics)
- Season and historical stats (league context, long-run questions)
- Player ID mapping across sources
- Respect data-source terms; keep the public repo license-safe
- Cheap: free where possible, modest paid spend only where it closes a real gap

## Source landscape (verified August 2026)

### Recommended core (all free)

| Source | Role | Access | Key facts (as of Aug 2026) |
|--------|------|--------|----------------------------|
| **MLB Stats API** (`statsapi.mlb.com`) | Scores, schedule, linescore, boxscore, play-by-play, standings, season stats — the workhorse | JSON, no key. Plain `requests` or the [MLB-StatsAPI](https://github.com/toddrob99/MLB-StatsAPI) wrapper (v1.9.0, Apr 2025 — dormant but working) or the typed [python-mlb-statsapi](https://pypi.org/project/python-mlb-statsapi/) (v1.0.0, Aug 2026, actively maintained) | Same API that powers MLB Gameday. The GUMBO live feed (`/api/v1.1/game/{gamePk}/feed/live`) includes per-pitch velocity/spin/launch data. No published rate limits — cache aggressively, keep to a few req/s. Endpoints documented by the community: [Endpoints wiki](https://github.com/toddrob99/MLB-StatsAPI/wiki/Endpoints), [Public-MLB-API](https://github.com/pseudo-r/Public-MLB-API) |
| **Baseball Savant / Statcast** | Pitch-level detail, 2015–present (PITCHf/x back to 2008) | `statcast_search/csv` endpoint via pybaseball's `statcast()` functions, or direct requests | Hard cap: **25,000 rows per query** (~5 league days) — chunk by day and cache. Savant data is retroactively revised; re-pull historical windows occasionally |
| **Retrosheet** | Historical play-by-play 1910–2025, game logs to the 1800s | **Pre-parsed CSVs** (new): [csvdownloads](https://www.retrosheet.org/downloads/csvdownloads.html) — `plays.csv`, `batting.csv`, `gameinfo.csv`, etc. No event-file parsing needed | Semi-annual releases (Fall 2025 covers through 2025). Most permissive license of any source |
| **Lahman Database (SABR)** | Season-level historical stats 1871–2025 | CSV download from [SABR](https://sabr.org/lahman-database/) (2025 edition released Jan 2026) | The old `chadwickbureau/baseballdatabank` GitHub mirror **no longer exists** — download from SABR. CC BY-SA 3.0 |
| **Chadwick Bureau register** | Player ID crosswalk (MLBAM ↔ Retrosheet ↔ BBRef ↔ FanGraphs) | CSVs on [GitHub](https://github.com/chadwickbureau/register), updated ~weekly | ODC-By 1.0 — cleanly redistributable with attribution |

### Use with care

- **pybaseball**: install **from git master, not PyPI** (PyPI is at 2.2.7 from Sept 2023; master got fixes through Jan 2026). Its Statcast functions are healthy; its **FanGraphs functions are broken** (403/CAPTCHA since ~2025) and its **Lahman loader is broken** (points at the deleted GitHub mirror). Treat it as a Statcast + player-ID tool only.
- **FanGraphs**: site is healthy but actively blocks programmatic access; ToS prohibits redistribution. Use the manual "Export Data" CSV button for one-off pulls (may require a paid Membership); keep raw exports out of this repo.
- **Baseball Reference**: posted [bot policy](https://www.sports-reference.com/bot-traffic.html) allows ≤20 req/min but the [data-use policy](https://www.sports-reference.com/data_use.html) prohibits building tools on scraped data or republishing it. Most of what we'd want from BR is Retrosheet/Lahman data anyway — get it from those sources, where redistribution is clean. Their sanctioned query tool is Stathead (subscription).

### What can be committed to this public repo

| Data origin | Commit raw? | Commit small derived tables? |
|-------------|-------------|------------------------------|
| Retrosheet | Yes, with the required notice: *"The information used here was obtained free of charge from and is copyrighted by Retrosheet."* | Yes (same notice) |
| Chadwick register | Yes (ODC-By, attribute) | Yes |
| Lahman | Yes (CC BY-SA, attribute; share-alike applies; Negro Leagues tables from Seamheads may carry separate terms — verify before redistributing those) | Yes |
| MLB Stats API / Statcast | No (MLBAM terms: individual, non-commercial, **non-bulk**) | Small aggregates/derived metrics with attribution — common practice, formally gray; keep them minimal |
| FanGraphs / Baseball Reference | No | No raw tables; own computed values referencing public stats only |

This maps directly onto the existing data policy: raw pulls live in gitignored `data/raw/`; only small, license-safe derivatives reach `data/processed/`.

## Architecture

Layers map onto the existing package skeleton:

```
                    ┌─────────────────────────────────────────────┐
 sources            │ statsapi.mlb.com   savant   retrosheet CSVs │
                    └───────────────┬─────────────────────────────┘
 ingest             baseball_lab.io  (cache-first clients, retry/backoff)
                                    │  → data/raw/<source>/<date>/*.json|csv   (gitignored)
 normalize          baseball_lab.clean  (raw → tidy frames, validated)
                                    │  → data/interim/*.parquet                (gitignored)
 derive             baseball_lab.metrics  (existing) + aggregations
                                    │  → data/processed/*.csv   (small, license-safe, committed)
 consume            notebooks / reports / scripts / apps
```

Principles:

1. **Cache-first ingest.** Every fetch is keyed (source, endpoint, date/params) and lands verbatim in `data/raw/`. Re-runs read from disk and never re-fetch an existing key. This makes analyses reproducible, keeps request volume polite, and means one season of Royals data is pulled exactly once.
2. **Raw is immutable, interim is disposable.** `data/interim/` parquet can always be rebuilt from raw; only `data/processed/` derivatives are precious, and those are committed.
3. **Notebooks never fetch.** All network access goes through `baseball_lab.io`; notebooks and reports import clean frames. (Spec rule: reusable logic lives in `src/`.)
4. **No silent failures.** Parsers validate expected fields and raise; the MLB API is undocumented and fields can drift.

### Planned modules

- `baseball_lab.io.statsapi` — schedule, linescore, boxscore, play-by-play/GUMBO pulls with caching (start with plain `requests`; adopt `python-mlb-statsapi` if typed models earn their keep)
- `baseball_lab.io.statcast` — day-chunked Savant pulls (respecting the 25k-row cap) with local cache
- `baseball_lab.io.retrosheet` / `baseball_lab.io.lahman` — download + load the released CSV bundles
- `baseball_lab.clean.games` — GUMBO/boxscore JSON → tidy game-level and plate-appearance-level frames
- `scripts/pull_games.py --team KC --start ... --end ...` — CLI wrapper: raw pull → processed Royals game log
- `scripts/game_report.py --date ...` — emits a pre-filled report skeleton (linescore, decisions, notable lines) following `reports/report_template.md`

### Testing

- Commit small fixture JSON (one schedule day, one boxscore, one GUMBO snippet) under `tests/fixtures/`; unit-test parsers offline.
- Live-API integration tests behind a pytest marker (`-m live`), excluded in CI.

## Phased plan

| Phase | Deliverable | Depends on | Status |
|-------|-------------|------------|--------|
| 1 | `io.statsapi` + `clean.games`; committed Royals season game log in `data/processed/` | nothing — free API | **Done** (as part of the daily pipeline) |
| 2 | Automated per-game reports (superseded `game_report.py`: stat packs + a report-writing Routine, see below) | Phase 1 | **Done** |
| 3 | `io.statcast` single-game pulls + Statcast highlights in each stat pack; day-chunked bulk pulls for notebooks | Phase 1 patterns | **Partial** (single-game done) |
| 4 | Historical layer: Retrosheet CSVs + Lahman loaders; league-context notebooks | independent | Not started |
| 5 | Automation: nightly in-season pull + morning narrative (`.github/workflows/nightly-royals.yml` + `docs/ROUTINE_PROMPT.md`) | Phases 1–2 | **Done** |

## Automation and environments

- **Local runs** are the default: `pull_games.py` after a game, or local cron in-season.
- **GitHub Actions cron** (optional, Phase 5): a scheduled workflow can refresh `data/processed/` derivatives nightly. Keep commits to small derived tables only — never raw MLBAM payloads — for the licensing reasons above.
- **Claude Code web sessions currently cannot run pulls.** Verified 2026-08-09: this environment's network egress policy blocks `statsapi.mlb.com`, `baseballsavant.mlb.com`, `retrosheet.org`, and `seanlahman.com` (PyPI and GitHub are open). To let Claude sessions fetch data and draft reports end-to-end, edit the environment's network policy at claude.ai/code (environment settings) and allowlist at minimum `statsapi.mlb.com`, ideally also `baseballsavant.mlb.com`.

## Paid options — is paying worth it?

**Short answer: not for the pipeline itself.** Baseball is unusual among sports: the free baseline (official MLB Stats API + Baseball Savant) is *better* than the paid mid-market. No product under ~$100/month matches Savant's free 2015-present pitch-level data — even Sportradar's enterprise Statcast add-on only covers 2020+. Pricing below researched August 2026, mostly via search snippets (provider sites block direct fetches) — verify on the provider's pricing page before paying.

### Provider survey

| Provider | MLB depth | Price (2026) | Verdict for this project |
|----------|-----------|--------------|--------------------------|
| [Sportradar](https://developer.sportradar.com/baseball/reference/mlb-overview) | Deepest commercial feed incl. Statcast (2020+) | Enterprise contract; free 30-day trial (1,000 calls) | Companies only. Trial is a fun sandbox, nothing more |
| [SportsDataIO](https://sportsdata.io/mlb-api) | Full stack + BAKER projections; event-level PBP, not pitch-tracking | Discovery Lab $99–149/mo (delayed data); real-time is sales-only | Overkill; delayed data at $99/mo loses to free real-time statsapi |
| [Goalserve](https://www.goalserve.com/en/sport-data-feeds/MLB-api/prices) | Scores, stats, odds since 2010; XML-first | $250/mo or $1,500/yr | Poor value for solo Python analytics |
| [Rolling Insights](https://rolling-insights.com/rolling-insights-datafeeds/price-plans/price-plans-mlb/) | Schedules/stats ($100/mo tier); box scores only at $4,200/yr tier | $100–600/mo | Dominated by free options; their free 2017+ historical sets are the only interesting part |
| [balldontlie](https://www.balldontlie.io/) | Stats/standings/PBP summaries 2002+, odds/props on higher tier; official Python SDK | $9.99/mo (stats), $39.99/mo (odds/props) | Cheapest credible paid API; buys a *documented, stable contract*, not more data |
| [API-Sports](https://api-sports.io/sports/baseball), [Highlightly](https://highlightly.net/mlb-api/), [TheSportsDB](https://www.thesportsdb.com/pricing) | Scores/standings/odds; no PBP or pitch data | ~$6–39/mo | Scoreboard-grade; an analytics project outgrows them in a week |
| [MySportsFeeds](https://www.mysportsfeeds.com/feed-pricing/) | PBP + projections add-ons | **Free for approved non-commercial use** | Sleeper pick — worth an application if statsapi ever becomes insufficient |
| [Stathead](https://stathead.com/baseball/) | Query tool over all of Baseball-Reference (not an API) | ~$9/mo / ~$80/yr | Best value on the list for historical *questions*; share-with-citation is public-repo-friendly |
| [FanGraphs Membership](https://plus.fangraphs.com/product/fangraphs-membership/) | CSV exports incl. ZiPS/Steamer/THE BAT projections (not an API) | ~$80/yr | The cheapest legitimate source of projections |
| [The Odds API](https://theoddsapi.com/) | Odds/props only | $29/mo (props at $99/mo) | Only if betting-market analysis enters the project |

### What paying actually closes

- **Projections** — the realest gap in the free stack. Cheapest fill: FanGraphs Membership (~$80/yr).
- **Deep historical query convenience** — Stathead (~$80/yr) answers "every player since 1901 who…" questions that would take real engineering over Retrosheet/Lahman.
- **API stability** — balldontlie ($9.99/mo) offers a documented, versioned contract if statsapi's undocumented-field drift or pybaseball's scraping fragility ever becomes a maintenance burden.
- **Not closed by paying**: pitch-level depth (free Savant wins), SLA at hobbyist prices (nobody offers one under $100/mo), redistribution rights (paid ToS are generally *more* restrictive than Retrosheet/Lahman/Chadwick).

### Recommendation

Build Phases 1–5 on the free stack: **$0**. If spending anything, **Stathead + FanGraphs ≈ $160/yr** closes the only two genuine gaps (historical queries, projections) — both are research tools feeding analysis, not pipeline dependencies. Revisit balldontlie or The Odds API only when a concrete need appears.

## References

Full source-by-source research notes with URLs are preserved in the repo history of this document; headline references:

- MLB-StatsAPI wrapper: https://github.com/toddrob99/MLB-StatsAPI (endpoints wiki documents the raw API)
- python-mlb-statsapi (typed, active): https://pypi.org/project/python-mlb-statsapi/
- pybaseball: https://github.com/jldbc/pybaseball (install from master; see issues #507, #489 for FanGraphs/Lahman breakage)
- Retrosheet CSV downloads: https://www.retrosheet.org/downloads/csvdownloads.html — license: https://www.retrosheet.org/notice.txt
- SABR Lahman Database: https://sabr.org/lahman-database/
- Chadwick register: https://github.com/chadwickbureau/register
- Sports Reference bot/data policies: https://www.sports-reference.com/bot-traffic.html, https://www.sports-reference.com/data_use.html
- MLBAM data notice: http://gdx.mlb.com/components/copyright.txt

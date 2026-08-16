# Data Sources

Document every data source used in this repo. Keep this file current.

## Source catalog

| Source | URL | Access method | Refresh cadence | License / ToS | Local-only? |
|--------|-----|---------------|-----------------|---------------|-------------|
| Baseball Reference | baseballreference.com | Manual download / CSV | As needed | Personal use; no bulk scraping | Yes (raw/) |
| Statcast / Baseball Savant | baseballsavant.mlb.com | CSV export or pybaseball | Daily during season | MLB terms apply | Yes (raw/) |
| Lahman Database | seanlahman.com | Annual release / CSV | Annual | CC-BY-SA 4.0 | Small subsets may be committed (processed/) |
| Retrosheet | retrosheet.org | Event files / CSV | Periodic | Free for non-commercial use; attribution required | Yes (raw/) |
| Game recaps (ESPN / MLB.com / CBS Sports) | espn.com, mlb.com, cbssports.com | Manual web search; facts quoted with inline links in reports | As needed | News content; quote with attribution, no bulk scraping | n/a (facts cited in reports only) |
| MLB Stats API | statsapi.mlb.com | HTTP JSON (schedule, linescore endpoints) | As needed | MLB terms apply; personal/analytical use | Yes (raw/) — note: blocked from some sandboxed environments |
| Baseball Almanac box scores | baseball-almanac.com/box-scores/ | Per-game pages (boxid=YYYYMMDD0TTT, TTT = home team retrosheet code); facts quoted via web search | As needed | Personal use; no bulk scraping | n/a (facts cited in reports/processed CSVs) |
| plaintextsports line scores | plaintextsports.com/mlb/DATE/AWAY-HOME | Per-game line scores; facts quoted via web search | Daily during season | Personal use | n/a (facts cited in reports/processed CSVs) |
| Neil Paine MLB Elo / game results | github.com/Neil-Paine-1/MLB-WAR-data-historical | CSV via raw.githubusercontent.com | Irregular (ends 2025 as of 2026-07) | Public repo; attribute | Yes (raw/) |

## Automated pulls

The nightly workflow (`.github/workflows/nightly-royals.yml`) pulls each Royals game from the MLB Stats API (schedule, GUMBO live feed, winProbability) and Baseball Savant (single-game Statcast CSV) on a GitHub Actions runner. Raw payloads stay on the runner (ephemeral, never committed); only compact per-game stat packs and a season game-log CSV land in `data/processed/royals/` — small derived tables, consistent with the licensing posture in `data_pipeline.md`.

## Notes

- **raw/** and **interim/** are gitignored — never committed.
- **processed/** may contain small, reproducible derivatives only.
- Always record how a dataset was obtained (script, manual download, API) so runs are reproducible.
- Check each source's terms before automated access.

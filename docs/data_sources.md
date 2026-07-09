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

## Notes

- **raw/** and **interim/** are gitignored — never committed.
- **processed/** may contain small, reproducible derivatives only.
- Always record how a dataset was obtained (script, manual download, API) so runs are reproducible.
- Check each source's terms before automated access.

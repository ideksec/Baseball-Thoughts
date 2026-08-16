#!/usr/bin/env python3
"""Render the daily Royals reports as a static site.

Reads the committed markdown in reports/royals/daily/ and the season game log,
and writes a browsable site: one page per report plus an index. Report files
are the only source of prose — this script adds no numbers of its own, and the
per-game facts on the index (result, score, record) come from the game log.

Usage:
    python scripts/build_site.py --out site
"""

from __future__ import annotations

import argparse
import re
import shutil
from dataclasses import dataclass
from html import escape
from pathlib import Path

import markdown
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = REPO_ROOT / "reports" / "royals" / "daily"
GAMELOG_GLOB = "gamelog_*.csv"
GAMELOG_DIR = REPO_ROOT / "data" / "processed" / "royals"
REPO_URL = "https://github.com/ideksec/Baseball-Thoughts"

# {date}_{vs|at}-{opp}[_gmN].md — the filename contract in statpack.report_filename
FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(vs|at)-([a-z]+)(?:_gm(\d))?\.md$")

STYLESHEET = """
:root {
  --bg: #fbfaf8;
  --surface: #ffffff;
  --border: #e2ded7;
  --text: #1c1a17;
  --muted: #6b655c;
  --accent: #004687;      /* Royals blue */
  --accent-soft: #e8eef5;
  --win: #1c6b3f;
  --win-bg: #e4f2ea;
  --loss: #97341f;
  --loss-bg: #f8e8e3;
  --radius: 10px;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #14161a;
    --surface: #1b1e24;
    --border: #2e333c;
    --text: #e8e6e3;
    --muted: #9aa1ad;
    --accent: #7fb2e5;
    --accent-soft: #1e2937;
    --win: #6ed09b;
    --win-bg: #17301f;
    --loss: #e89a86;
    --loss-bg: #331d18;
  }
}
:root[data-theme="dark"] {
  --bg: #14161a;
  --surface: #1b1e24;
  --border: #2e333c;
  --text: #e8e6e3;
  --muted: #9aa1ad;
  --accent: #7fb2e5;
  --accent-soft: #1e2937;
  --win: #6ed09b;
  --win-bg: #17301f;
  --loss: #e89a86;
  --loss-bg: #331d18;
}

* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI",
        Helvetica, Arial, sans-serif;
}
.wrap { max-width: 46rem; margin: 0 auto; padding: 2.5rem 1.25rem 4rem; }
a { color: var(--accent); }

header.masthead {
  border-bottom: 1px solid var(--border); margin-bottom: 2rem; padding-bottom: 1.5rem;
}
header.masthead h1 {
  font-size: 1.9rem; line-height: 1.2; margin: 0 0 .4rem; letter-spacing: -.02em;
}
header.masthead p { color: var(--muted); margin: 0; }
.backlink {
  display: inline-block; margin-bottom: 1.5rem; font-size: .9rem; text-decoration: none;
}
.backlink:hover { text-decoration: underline; }

.season {
  display: flex; flex-wrap: wrap; gap: .5rem 2rem; margin: 1.25rem 0 0;
  padding: 0; list-style: none;
}
.season div { display: flex; flex-direction: column; }
.season dt, .season .k {
  font-size: .72rem; text-transform: uppercase; letter-spacing: .08em; color: var(--muted);
}
.season dd, .season .v {
  margin: 0; font-size: 1.25rem; font-variant-numeric: tabular-nums; font-weight: 600;
}

ul.games { list-style: none; margin: 0; padding: 0; }
ul.games li { margin: 0 0 .75rem; }
.game {
  display: block; padding: 1rem 1.1rem; background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--radius);
  text-decoration: none; color: inherit;
}
.game:hover { border-color: var(--accent); }
.game .meta {
  display: flex; flex-wrap: wrap; align-items: baseline; gap: .6rem; margin-bottom: .3rem;
}
.game .date { font-size: .8rem; color: var(--muted); font-variant-numeric: tabular-nums; }
.badge {
  font-size: .72rem; font-weight: 700; letter-spacing: .06em; padding: .1rem .45rem;
  border-radius: 4px; text-transform: uppercase;
}
.badge.w { color: var(--win); background: var(--win-bg); }
.badge.l { color: var(--loss); background: var(--loss-bg); }
.game .score { font-size: .8rem; color: var(--muted); font-variant-numeric: tabular-nums; }
.game .title { font-weight: 600; line-height: 1.35; }

article h1 { font-size: 1.75rem; line-height: 1.25; letter-spacing: -.02em; margin: 0 0 1rem; }
article h2 {
  font-size: 1.15rem; margin: 2.25rem 0 .75rem; padding-bottom: .3rem;
  border-bottom: 1px solid var(--border);
}
article h3 { font-size: 1rem; margin: 1.75rem 0 .5rem; color: var(--accent); }
article blockquote {
  margin: 0 0 1.5rem; padding: .6rem 0 .6rem 1rem;
  border-left: 3px solid var(--border); color: var(--muted); font-size: .9rem;
}
article blockquote p { margin: .15rem 0; }
article code {
  background: var(--accent-soft); padding: .1rem .3rem; border-radius: 3px;
  font-size: .87em; word-break: break-word;
}
.table-scroll { overflow-x: auto; margin: 1.25rem 0; }
table {
  border-collapse: collapse; width: 100%; font-size: .87rem;
  font-variant-numeric: tabular-nums;
}
th, td {
  padding: .4rem .55rem; text-align: right; border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
th:first-child, td:first-child { text-align: left; }
thead th {
  color: var(--muted); font-size: .72rem; text-transform: uppercase; letter-spacing: .06em;
}

footer.site {
  margin-top: 3.5rem; padding-top: 1.25rem; border-top: 1px solid var(--border);
  color: var(--muted); font-size: .82rem;
}
footer.site a { color: var(--muted); }
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<style>{css}</style>
</head>
<body>
<div class="wrap">
{body}
<footer class="site">
  Generated from the committed reports in
  <a href="{repo}/tree/main/reports/royals/daily">reports/royals/daily</a>
  by <a href="{repo}/blob/main/scripts/build_site.py">scripts/build_site.py</a>.
</footer>
</div>
</body>
</html>
"""


@dataclass
class Report:
    """One daily report and the game-log facts that go with it."""

    path: Path
    date: str
    home_away: str
    opponent: str
    game_number: int
    title: str
    html: str

    @property
    def slug(self) -> str:
        return self.path.stem

    @property
    def matchup(self) -> str:
        prefix = "vs" if self.home_away == "vs" else "at"
        return f"{prefix} {self.opponent.upper()}"


def load_gamelog(gamelog_dir: Path) -> pd.DataFrame:
    """Concatenate every season game log found, or return an empty frame."""
    frames = [pd.read_csv(p) for p in sorted(gamelog_dir.glob(GAMELOG_GLOB))]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _first_heading(md_text: str) -> str:
    for line in md_text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled report"


def render_markdown(md_text: str) -> str:
    """Markdown -> HTML, with tables wrapped so they scroll instead of
    overflowing the page on narrow screens."""
    html = markdown.markdown(md_text, extensions=["tables", "sane_lists"])
    return html.replace("<table>", '<div class="table-scroll"><table>').replace(
        "</table>", "</table></div>"
    )


def collect_reports(daily_dir: Path) -> list[Report]:
    """Every daily report, newest first. Files that do not match the pipeline's
    filename contract are skipped rather than guessed at."""
    reports = []
    for path in sorted(daily_dir.glob("*.md")):
        match = FILENAME_RE.match(path.name)
        if not match:
            continue
        date, prefix, opponent, game_number = match.groups()
        text = path.read_text()
        reports.append(
            Report(
                path=path,
                date=date,
                home_away=prefix,
                opponent=opponent,
                game_number=int(game_number or 1),
                title=_first_heading(text),
                html=render_markdown(text),
            )
        )
    reports.sort(key=lambda r: (r.date, r.game_number), reverse=True)
    return reports


def game_facts(gamelog: pd.DataFrame, report: Report) -> dict | None:
    """The game-log row for a report, as display strings. None when the log has
    no matching row — the index then shows the report without a result badge."""
    if gamelog.empty:
        return None
    rows = gamelog[
        (gamelog["date"] == report.date) & (gamelog["game_number"] == report.game_number)
    ]
    if rows.empty:
        return None
    row = rows.iloc[0]
    return {
        "result": str(row["result"]),
        "royals_runs": int(row["royals_runs"]),
        "opponent_runs": int(row["opponent_runs"]),
        "wins_after": int(row["royals_wins_after"]),
        "losses_after": int(row["royals_losses_after"]),
    }


def season_strip(gamelog: pd.DataFrame, reports: list[Report]) -> str:
    """Record and run differential through the most recent report's game."""
    if gamelog.empty or not reports:
        return ""
    newest = reports[0]
    played = gamelog[gamelog["date"] <= newest.date]
    if played.empty:
        return ""
    wins = int((played["result"] == "W").sum())
    losses = int((played["result"] == "L").sum())
    run_diff = int(played["royals_runs"].sum() - played["opponent_runs"].sum())
    return (
        '<div class="season">'
        f'<div><span class="k">Record</span><span class="v">{wins}&#8211;{losses}</span></div>'
        f'<div><span class="k">Run diff</span><span class="v">{run_diff:+d}</span></div>'
        f'<div><span class="k">Games</span><span class="v">{len(played)}</span></div>'
        f'<div><span class="k">Reports</span><span class="v">{len(reports)}</span></div>'
        "</div>"
    )


def render_index(reports: list[Report], gamelog: pd.DataFrame) -> str:
    items = []
    for report in reports:
        facts = game_facts(gamelog, report)
        if facts:
            badge = (
                f'<span class="badge {facts["result"].lower()}">{escape(facts["result"])}</span>'
            )
            score = (
                f'<span class="score">{facts["royals_runs"]}&#8211;{facts["opponent_runs"]}'
                f' &middot; {facts["wins_after"]}&#8211;{facts["losses_after"]}</span>'
            )
        else:
            badge, score = "", ""
        items.append(
            f'<li><a class="game" href="reports/{escape(report.slug)}.html">'
            f'<span class="meta"><span class="date">{escape(report.date)}</span>'
            f'{badge}<span class="score">{escape(report.matchup)}</span>{score}</span>'
            f'<span class="title">{escape(report.title)}</span>'
            "</a></li>"
        )
    body = (
        '<header class="masthead">'
        "<h1>Royals daily reports</h1>"
        "<p>Game-by-game writeups generated from committed stat packs. "
        "Every number traces to a file in the repository.</p>"
        f"{season_strip(gamelog, reports)}"
        "</header>"
        f'<ul class="games">{"".join(items)}</ul>'
    )
    return PAGE.format(
        title="Royals daily reports",
        description="Game-by-game Kansas City Royals reports generated from committed stat packs.",
        css=STYLESHEET,
        body=body,
        repo=REPO_URL,
    )


def render_report(report: Report) -> str:
    body = (
        '<a class="backlink" href="../index.html">&larr; All reports</a>'
        f"<article>{report.html}</article>"
    )
    return PAGE.format(
        title=f"{report.date} {report.matchup} — Royals daily reports",
        description=escape(report.title, quote=True),
        css=STYLESHEET,
        body=body,
        repo=REPO_URL,
    )


def build(out_dir: Path, daily_dir: Path = DAILY_DIR, gamelog_dir: Path = GAMELOG_DIR) -> int:
    """Write the site to out_dir. Returns the number of reports rendered."""
    reports = collect_reports(daily_dir)
    gamelog = load_gamelog(gamelog_dir)

    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "reports").mkdir(parents=True)

    (out_dir / "index.html").write_text(render_index(reports, gamelog))
    for report in reports:
        (out_dir / "reports" / f"{report.slug}.html").write_text(render_report(report))
    # Pages runs the output through Jekyll unless told not to.
    (out_dir / ".nojekyll").write_text("")
    return len(reports)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="site", help="output directory (default: site)")
    args = parser.parse_args()

    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    count = build(out_dir)
    print(f"RESULT: rendered {count} report(s) to {out_dir}")


if __name__ == "__main__":
    main()

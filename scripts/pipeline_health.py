#!/usr/bin/env python3
"""Pipeline health check — asserts the three-stage daily pipeline is intact.

Every stage of this pipeline fails quietly. A broken nightly pull writes no
stat pack; stage 2's instructions say "no new packs -> end quietly"; a failed
Pages deploy just leaves the last good site up. All three look exactly like a
Royals off day, which is how a 17-run Pages outage and two weeks of unpushed
reports went unnoticed in August 2026.

This turns each handoff into an assertion, so the next scheduled run is loud:

  1. game log is fresh    — stage 1 is still ingesting during the season
  2. packs cover games    — every logged game since the pipeline began has a pack
  3. reports cover packs  — every pack has a report at its contract path
  4. site is current      — the published index lists the newest report

Usage:
    python scripts/pipeline_health.py            # all four checks
    python scripts/pipeline_health.py --offline  # skip the published-site check

Exits 0 when every check passes, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests

from baseball_lab.statpack import report_filename

REPO_ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = REPO_ROOT / "reports" / "royals" / "daily"
STATPACK_DIR = REPO_ROOT / "data" / "processed" / "royals" / "statpacks"
GAMELOG_DIR = REPO_ROOT / "data" / "processed" / "royals"
GAMELOG_GLOB = "gamelog_*.csv"
SITE_URL = "https://ideksec.github.io/Baseball-Thoughts/"

# The nightly workflow only runs March-November; outside that window a stale
# game log is the off-season, not a fault.
SEASON_MONTHS = range(3, 12)
FULL_SEASON_GAMES = 162
# The longest scheduled in-season gap (the All-Star break) is about four days.
STALE_AFTER_DAYS = 5
SITE_TIMEOUT_SECONDS = 30


@dataclass
class Check:
    """One invariant: its name, why it was skipped, and what broke."""

    name: str
    failures: list[str] = field(default_factory=list)
    skipped: str = ""

    @property
    def ok(self) -> bool:
        return not self.failures

    def render(self) -> str:
        if self.skipped:
            return f"SKIP {self.name}: {self.skipped}"
        if self.ok:
            return f"OK   {self.name}"
        return f"FAIL {self.name}\n" + "\n".join(f"       - {f}" for f in self.failures)


def load_gamelog(gamelog_dir: Path = GAMELOG_DIR) -> pd.DataFrame:
    """Concatenate every season game log found, or return an empty frame."""
    frames = [pd.read_csv(p) for p in sorted(gamelog_dir.glob(GAMELOG_GLOB))]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).sort_values("date", ignore_index=True)


def load_packs(statpack_dir: Path = STATPACK_DIR) -> list[tuple[Path, dict]]:
    return [(p, json.loads(p.read_text())) for p in sorted(statpack_dir.glob("*.json"))]


def check_gamelog_fresh(gamelog: pd.DataFrame, today: date) -> Check:
    """Stage 1 is still ingesting — the loudest sign the nightly pull died."""
    check = Check("game log is fresh")
    if gamelog.empty:
        check.failures.append(f"no {GAMELOG_GLOB} found under {GAMELOG_DIR}")
        return check
    if len(gamelog) >= FULL_SEASON_GAMES:
        check.skipped = f"season complete ({len(gamelog)} games logged)"
        return check
    if today.month not in SEASON_MONTHS:
        check.skipped = "off-season"
        return check

    newest = gamelog["date"].max()
    age = (today - datetime.strptime(newest, "%Y-%m-%d").date()).days
    if age > STALE_AFTER_DAYS:
        check.failures.append(
            f"newest logged game is {newest} ({age} days ago, limit {STALE_AFTER_DAYS}) "
            f"— stage 1 (nightly-royals.yml) may have stopped"
        )
    return check


def check_packs_cover_gamelog(gamelog: pd.DataFrame, root: Path = REPO_ROOT) -> Check:
    """Every game logged since the pipeline began carries a stat pack.

    Rows before the first pack are the pre-pipeline schedule backfill and are
    expected to have none, so the pipeline's own start date sets the bound.
    """
    check = Check("packs cover logged games")
    if gamelog.empty:
        check.skipped = "no game log"
        return check

    with_pack = gamelog[gamelog["statpack"].notna() & (gamelog["statpack"] != "")]
    if with_pack.empty:
        check.skipped = "no stat packs yet"
        return check

    start = with_pack["date"].min()
    for row in gamelog[gamelog["date"] >= start].itertuples():
        label = f"{row.date} game {row.game_pk}"
        pack = "" if pd.isna(row.statpack) else str(row.statpack)
        if not pack:
            check.failures.append(f"{label}: game log row has no stat pack")
        elif not (root / pack).exists():
            check.failures.append(f"{label}: stat pack {pack} is missing from disk")
    return check


def check_reports_cover_packs(packs: list[tuple[Path, dict]], daily_dir: Path) -> Check:
    """Every stat pack has a report — the stage 2 handoff that broke in August."""
    check = Check("reports cover stat packs")
    if not packs:
        check.skipped = "no stat packs yet"
        return check
    for path, pack in packs:
        expected = daily_dir / report_filename(pack)
        if not expected.exists():
            check.failures.append(
                f"{path.name}: no report at reports/royals/daily/{expected.name}"
            )
    return check


def check_site_current(packs: list[tuple[Path, dict]], url: str = SITE_URL) -> Check:
    """The published index lists the newest report — stage 3 actually deployed."""
    check = Check("published site is current")
    if not packs:
        check.skipped = "no stat packs yet"
        return check

    newest_slug = Path(report_filename(packs[-1][1])).stem
    try:
        response = requests.get(url, timeout=SITE_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as err:
        check.failures.append(f"could not fetch {url}: {err}")
        return check

    if newest_slug not in response.text:
        check.failures.append(
            f"{url} does not list {newest_slug} "
            f"— stage 3 (pages.yml) has not deployed the newest report"
        )
    return check


def run_checks(*, offline: bool = False, today: date | None = None) -> list[Check]:
    gamelog = load_gamelog()
    packs = load_packs()
    checks = [
        check_gamelog_fresh(gamelog, today or date.today()),
        check_packs_cover_gamelog(gamelog),
        check_reports_cover_packs(packs, DAILY_DIR),
    ]
    if offline:
        checks.append(Check("published site is current", skipped="--offline"))
    else:
        checks.append(check_site_current(packs))
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline", action="store_true", help="skip the published-site check"
    )
    args = parser.parse_args(argv)

    checks = run_checks(offline=args.offline)
    for check in checks:
        print(check.render())

    broken = [c for c in checks if not c.ok]
    if broken:
        print(f"\nRESULT: {len(broken)} of {len(checks)} checks failed")
        return 1
    print(f"\nRESULT: pipeline healthy ({len(checks)} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Nightly Royals stat-pack builder (Stage 1 of the daily pipeline).

Default mode scans the last --days-back Central-time dates for final
Royals games and builds a stat pack + game-log row for each game that
doesn't have one yet (idempotent; --force rebuilds). Designed to run on
a GitHub Actions cron at ~08:30 UTC, after West Coast games end.

Prints machine-greppable "RESULT: ..." lines the workflow folds into its
commit message. No-op runs leave the tree untouched, so the workflow's
commit step naturally skips them.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from baseball_lab.clean.gamelog import (
    gamelog_row,
    gamelog_row_from_schedule_game,
    load_gamelog,
    upsert_gamelog,
)
from baseball_lab.io.statcast import StatcastUnavailable, get_statcast_game
from baseball_lab.io.statsapi import (
    final_games,
    get_live_feed,
    get_schedule,
    get_schedule_range,
    get_win_probability,
)
from baseball_lab.statpack import build_stat_pack, stat_pack_path, write_stat_pack

CENTRAL = ZoneInfo("America/Chicago")
STATCAST_RETRY_DAYS = 3


def gamelog_path(root: Path, date: str) -> Path:
    return root / "processed" / "royals" / f"gamelog_{date[:4]}.csv"


def recent_central_dates(days_back: int) -> list[str]:
    """Yesterday backwards, in Central time — the game days that have ended."""
    today = datetime.now(CENTRAL).date()
    return [(today - timedelta(days=offset)).isoformat() for offset in range(1, days_back + 1)]


def needs_statcast_retry(pack_path: Path, date: str) -> bool:
    """An existing pack without Statcast gets retried while the game is fresh."""
    pack = json.loads(pack_path.read_text())
    if pack.get("sources", {}).get("statcast"):
        return False
    game_date = datetime.strptime(date, "%Y-%m-%d").date()
    age = (datetime.now(CENTRAL).date() - game_date).days
    return age <= STATCAST_RETRY_DAYS


def process_game(game: dict, date: str, *, root: Path, force: bool, dry_run: bool) -> str:
    game_pk = game["gamePk"]
    pack_path = stat_pack_path(root, date, game_pk)
    if pack_path.exists() and not force and not needs_statcast_retry(pack_path, date):
        return f"RESULT: exists {date} game {game_pk}"

    raw = root / "raw"
    feed = get_live_feed(game_pk, cache_dir=raw, force=force)
    win_probability = get_win_probability(game_pk, cache_dir=raw, force=force)
    statcast_df, statcast_error = None, None
    try:
        statcast_df = get_statcast_game(game_pk, date, cache_dir=raw, force=force)
    except StatcastUnavailable as err:
        statcast_error = str(err)

    log_path = gamelog_path(root, date)
    row = gamelog_row(feed, statpack=str(pack_path))
    gamelog = upsert_gamelog(log_path, [row], write=not dry_run)

    pack = build_stat_pack(
        feed=feed,
        win_probability=win_probability,
        statcast_df=statcast_df,
        gamelog=gamelog,
        statcast_error=statcast_error,
    )
    if dry_run:
        print(json.dumps(pack, indent=1, sort_keys=True))
        return f"RESULT: dry-run {date} game {game_pk}"
    write_stat_pack(pack, root)
    statcast_note = "with statcast" if statcast_df is not None else "NO statcast"
    summary = pack["game"]
    return (
        f"RESULT: wrote {date} game {game_pk} "
        f"{summary['result']} {summary['score']['royals']}-{summary['score']['opponent']} "
        f"({statcast_note})"
    )


def process_date(date: str, *, root: Path, force: bool, dry_run: bool) -> list[str]:
    schedule = get_schedule(date, cache_dir=root / "raw", force=force)
    games = final_games(schedule)
    if not games:
        return [f"RESULT: no-games {date}"]
    return [
        process_game(game, date, root=root, force=force, dry_run=dry_run) for game in games
    ]


def backfill(start: str, end: str, *, root: Path, dry_run: bool) -> list[str]:
    """Seed the season game log from one hydrated schedule call (no packs)."""
    schedule = get_schedule_range(start, end, cache_dir=root / "raw")
    games = final_games(schedule)
    if not games:
        return [f"RESULT: no-games {start}..{end}"]
    log_path = gamelog_path(root, start)
    existing = load_gamelog(log_path)
    known = set(existing["game_pk"].tolist()) if not existing.empty else set()
    # Never overwrite richer nightly rows with thin backfill rows.
    rows = [
        gamelog_row_from_schedule_game(g) for g in games if g["gamePk"] not in known
    ]
    if not rows:
        return [f"RESULT: backfill-noop {start}..{end}"]
    upsert_gamelog(log_path, rows, write=not dry_run)
    return [f"RESULT: backfill {start}..{end} added {len(rows)} games"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Process one date (YYYY-MM-DD) instead of the lookback")
    parser.add_argument("--days-back", type=int, default=3, help="Lookback window (default 3)")
    parser.add_argument("--backfill", metavar="START:END", help="Seed game log for a date range")
    parser.add_argument("--force", action="store_true", help="Rebuild even if packs exist")
    parser.add_argument("--dry-run", action="store_true", help="Print packs, write nothing")
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    args = parser.parse_args(argv)

    if args.backfill:
        start, _, end = args.backfill.partition(":")
        if not (start and end):
            parser.error("--backfill requires START:END")
        results = backfill(start, end, root=args.data_root, dry_run=args.dry_run)
    else:
        dates = [args.date] if args.date else recent_central_dates(args.days_back)
        results = []
        for date in dates:
            results.extend(
                process_date(date, root=args.data_root, force=args.force, dry_run=args.dry_run)
            )
    for line in results:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())

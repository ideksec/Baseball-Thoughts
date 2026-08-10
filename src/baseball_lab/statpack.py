"""Stat pack assembly — the contract between the nightly pull and the
morning narrative.

A stat pack is one compact JSON per game (top-N lists and aggregates
only, target <=15 KB) committed to data/processed/royals/statpacks/.
Stage 2 (the report-writing Routine) consumes packs and nothing else, so
validate_stat_pack is the drift alarm for the whole handoff.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from baseball_lab.clean.games import (
    parse_batting_highlights,
    parse_decisions,
    parse_game_summary,
    parse_linescore,
    parse_pitching_lines,
    parse_plays,
    rank_top_plays,
)
from baseball_lab.clean.statcast import statcast_highlights
from baseball_lab.metrics.rolling import last_n_summary, season_summary

STAT_PACK_VERSION = 1

_REQUIRED_KEYS = {
    "schema_version",
    "generated_at",
    "sources",
    "game",
    "linescore",
    "decisions",
    "top_plays",
    "top_plays_ranking_basis",
    "pitching",
    "batting_highlights",
    "rolling",
    "statcast",
}


class StatPackError(RuntimeError):
    """A stat pack failed validation — do not commit it."""


def build_stat_pack(
    *,
    feed: dict,
    win_probability: list[dict],
    statcast_df: pd.DataFrame | None,
    gamelog: pd.DataFrame,
    statcast_error: str | None = None,
    generated_at: datetime | None = None,
) -> dict:
    """Assemble a stat pack from parsed sources.

    gamelog must already include this game's row so rolling numbers
    reflect the game being written up.
    """
    summary = parse_game_summary(feed)
    royals_home = summary["home_away"] == "home"
    plays = parse_plays(feed, win_probability or None)
    top_plays, basis = rank_top_plays(plays, royals_home=royals_home)

    if statcast_df is not None and not statcast_df.empty:
        player_names = {
            p["id"]: p["fullName"] for p in feed["gameData"]["players"].values()
        }
        statcast = statcast_highlights(
            statcast_df, royals_home=royals_home, player_names=player_names
        )
        statcast_note = f"statcast rows: {len(statcast_df)}"
    else:
        statcast = {"available": False}
        statcast_note = f"statcast unavailable: {statcast_error or 'unknown'}"

    when = generated_at or datetime.now(timezone.utc)
    return {
        "schema_version": STAT_PACK_VERSION,
        "generated_at": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": {
            "statsapi_gumbo": True,
            "win_probability_endpoint": bool(win_probability),
            "statcast": statcast["available"],
            "statcast_error": statcast_error,
        },
        "game": summary,
        "linescore": parse_linescore(feed),
        "decisions": parse_decisions(feed),
        "top_plays": top_plays,
        "top_plays_ranking_basis": basis,
        "pitching": parse_pitching_lines(feed),
        "batting_highlights": parse_batting_highlights(feed),
        "rolling": {
            "last10": last_n_summary(gamelog, 10),
            "season": season_summary(gamelog),
        },
        "statcast": statcast,
        "notes": [statcast_note],
    }


def validate_stat_pack(pack: dict) -> None:
    """Raise StatPackError if the pack is structurally unsound."""
    missing = _REQUIRED_KEYS - set(pack)
    if missing:
        raise StatPackError(f"Stat pack missing keys: {sorted(missing)}")
    if pack["schema_version"] != STAT_PACK_VERSION:
        raise StatPackError(
            f"Stat pack schema_version {pack['schema_version']} != {STAT_PACK_VERSION}"
        )
    game = pack["game"]
    for key in ("game_pk", "date", "result", "score", "opponent"):
        if key not in game:
            raise StatPackError(f"Stat pack game section missing '{key}'")
    if game["result"] not in ("W", "L"):
        raise StatPackError(f"Invalid result: {game['result']}")
    if pack["top_plays_ranking_basis"] not in (
        "win_probability",
        "captivating_index",
        "leverage_heuristic",
    ):
        raise StatPackError(f"Invalid ranking basis: {pack['top_plays_ranking_basis']}")
    if not isinstance(pack["statcast"].get("available"), bool):
        raise StatPackError("statcast.available must be a bool")


def stat_pack_path(root: Path, date: str, game_pk: int) -> Path:
    """data/processed/royals/statpacks/{date}_{gamePk}.json under the given data root."""
    return root / "processed" / "royals" / "statpacks" / f"{date}_{game_pk}.json"


def write_stat_pack(pack: dict, root: Path) -> Path:
    validate_stat_pack(pack)
    path = stat_pack_path(root, pack["game"]["date"], pack["game"]["game_pk"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pack, indent=1, sort_keys=True) + "\n")
    return path


def report_filename(pack: dict) -> str:
    """Deterministic report filename shared by both pipeline stages:
    {date}_{vs|at}-{opp}[_gmN].md"""
    game = pack["game"]
    prefix = "vs" if game["home_away"] == "home" else "at"
    opp = game["opponent"]["abbrev"].lower()
    suffix = "" if game["doubleheader"] == "N" else f"_gm{game['game_number']}"
    return f"{game['date']}_{prefix}-{opp}{suffix}.md"

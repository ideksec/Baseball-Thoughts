"""Season game-log rows and idempotent CSV upserts.

One row per game, keyed on game_pk. A full season is <=162 rows, so the
whole CSV is rewritten on every upsert — trivially cheap and keeps the
committed file canonically sorted.
"""

from pathlib import Path

import pandas as pd

from baseball_lab.clean.games import (
    parse_decisions,
    parse_game_summary,
    parse_linescore,
    parse_pitching_lines,
)
from baseball_lab.io.statsapi import ROYALS_TEAM_ID

GAMELOG_COLUMNS = [
    "game_pk",
    "date",
    "game_number",
    "doubleheader",
    "home_away",
    "opponent_abbrev",
    "opponent_name",
    "result",
    "royals_runs",
    "opponent_runs",
    "innings",
    "walk_off",
    "royals_hits",
    "royals_errors",
    "opponent_hits",
    "opponent_errors",
    "win_pitcher",
    "loss_pitcher",
    "save_pitcher",
    "royals_starter",
    "royals_starter_ip",
    "royals_starter_er",
    "royals_wins_after",
    "royals_losses_after",
    "statpack",
]


def gamelog_row(feed: dict, *, statpack: str = "") -> dict:
    """Build a game-log row from a GUMBO feed (the nightly path)."""
    summary = parse_game_summary(feed)
    linescore = parse_linescore(feed)
    decisions = parse_decisions(feed)
    pitching = parse_pitching_lines(feed)
    side = summary["home_away"]
    opp_side = "away" if side == "home" else "home"
    return {
        "game_pk": summary["game_pk"],
        "date": summary["date"],
        "game_number": summary["game_number"],
        "doubleheader": summary["doubleheader"],
        "home_away": side,
        "opponent_abbrev": summary["opponent"]["abbrev"],
        "opponent_name": summary["opponent"]["name"],
        "result": summary["result"],
        "royals_runs": summary["score"]["royals"],
        "opponent_runs": summary["score"]["opponent"],
        "innings": summary["innings"],
        "walk_off": summary["walk_off"],
        "royals_hits": linescore[side]["hits"],
        "royals_errors": linescore[side]["errors"],
        "opponent_hits": linescore[opp_side]["hits"],
        "opponent_errors": linescore[opp_side]["errors"],
        "win_pitcher": decisions["winner"]["name"],
        "loss_pitcher": decisions["loser"]["name"],
        "save_pitcher": decisions["save"]["name"] if decisions["save"] else "",
        "royals_starter": pitching["royals_starter"]["name"],
        "royals_starter_ip": pitching["royals_starter"]["ip"],
        "royals_starter_er": pitching["royals_starter"]["er"],
        "royals_wins_after": summary["royals_record_after"]["wins"],
        "royals_losses_after": summary["royals_record_after"]["losses"],
        "statpack": statpack,
    }


def gamelog_row_from_schedule_game(game: dict) -> dict:
    """Build a (thinner) game-log row from a hydrated schedule entry (backfill)."""
    teams = game["teams"]
    side = "home" if teams["home"]["team"]["id"] == ROYALS_TEAM_ID else "away"
    opp_side = "away" if side == "home" else "home"
    royals, opp = teams[side], teams[opp_side]
    record = royals.get("leagueRecord", {})
    return {
        "game_pk": game["gamePk"],
        "date": game["officialDate"],
        "game_number": game.get("gameNumber", 1),
        "doubleheader": game.get("doubleHeader", "N"),
        "home_away": side,
        "opponent_abbrev": opp["team"].get("abbreviation", ""),
        "opponent_name": opp["team"].get("name", ""),
        "result": "W" if royals.get("score", 0) > opp.get("score", 0) else "L",
        "royals_runs": royals.get("score", 0),
        "opponent_runs": opp.get("score", 0),
        "innings": game.get("scheduledInnings", 9),
        "walk_off": False,
        "royals_hits": "",
        "royals_errors": "",
        "opponent_hits": "",
        "opponent_errors": "",
        "win_pitcher": "",
        "loss_pitcher": "",
        "save_pitcher": "",
        "royals_starter": "",
        "royals_starter_ip": "",
        "royals_starter_er": "",
        "royals_wins_after": record.get("wins", ""),
        "royals_losses_after": record.get("losses", ""),
        "statpack": "",
    }


def load_gamelog(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame(columns=GAMELOG_COLUMNS)


def upsert_gamelog(path: Path, rows: list[dict], *, write: bool = True) -> pd.DataFrame:
    """Insert or replace rows keyed on game_pk; returns the updated frame."""
    gamelog = load_gamelog(path)
    new = pd.DataFrame(rows, columns=GAMELOG_COLUMNS)
    if not gamelog.empty:
        gamelog = gamelog[~gamelog["game_pk"].isin(new["game_pk"])]
    combined = pd.concat([gamelog, new], ignore_index=True)
    combined = combined.sort_values(["date", "game_number"]).reset_index(drop=True)
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(path, index=False)
    return combined

"""Parsers from GUMBO live-feed JSON to tidy structures.

The MLB Stats API is undocumented, so every parser validates the fields
it needs via _require and raises ParseError naming the missing path —
field drift fails loudly, never silently.
"""

import pandas as pd

from baseball_lab.io.statsapi import ROYALS_TEAM_ID


class ParseError(RuntimeError):
    """A GUMBO payload is missing an expected field (API drift alarm)."""


def _require(mapping: dict, path: str):
    cur = mapping
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            raise ParseError(f"Missing expected field: {path}")
        cur = cur[key]
    return cur


def royals_side(feed: dict) -> str:
    """'home' or 'away' — which side the Royals are on."""
    if _require(feed, "gameData.teams.home")["id"] == ROYALS_TEAM_ID:
        return "home"
    if _require(feed, "gameData.teams.away")["id"] == ROYALS_TEAM_ID:
        return "away"
    raise ParseError(f"Royals (team {ROYALS_TEAM_ID}) not in this feed")


def parse_game_summary(feed: dict) -> dict:
    """Game-level summary: teams, result, score, record, walk-off flag."""
    side = royals_side(feed)
    opp_side = "away" if side == "home" else "home"
    teams = _require(feed, "gameData.teams")
    linescore_teams = _require(feed, "liveData.linescore.teams")
    royals_runs = _require(linescore_teams[side], "runs")
    opp_runs = _require(linescore_teams[opp_side], "runs")
    plays = _require(feed, "liveData.plays.allPlays")
    innings = _require(feed, "liveData.linescore.innings")

    walk_off = False
    if plays and _require(feed, "gameData.status.codedGameState") == "F":
        last = plays[-1]
        home_won = _require(feed, "liveData.linescore.teams.home")["runs"] > _require(
            feed, "liveData.linescore.teams.away"
        )["runs"]
        walk_off = (
            home_won
            and last.get("about", {}).get("halfInning") == "bottom"
            and bool(last.get("about", {}).get("isScoringPlay"))
        )

    return {
        "game_pk": (
            _require(feed, "gamePk") if "gamePk" in feed else _require(feed, "gameData.game.pk")
        ),
        "date": _require(feed, "gameData.datetime.officialDate"),
        "game_number": _require(feed, "gameData.game.gameNumber"),
        "doubleheader": _require(feed, "gameData.game.doubleHeader"),
        "venue": _require(feed, "gameData.venue.name"),
        "home_away": side,
        "opponent": {
            "id": teams[opp_side]["id"],
            "name": teams[opp_side]["name"],
            "abbrev": _require(teams[opp_side], "abbreviation"),
        },
        "result": "W" if royals_runs > opp_runs else "L",
        "score": {"royals": royals_runs, "opponent": opp_runs},
        "innings": len(innings),
        "walk_off": walk_off,
        "royals_record_after": {
            "wins": _require(teams[side], "record.wins"),
            "losses": _require(teams[side], "record.losses"),
        },
    }


def parse_linescore(feed: dict) -> dict:
    """Runs by inning plus R/H/E for both sides."""
    innings = _require(feed, "liveData.linescore.innings")
    teams = _require(feed, "gameData.teams")
    out = {}
    for side in ("away", "home"):
        totals = _require(feed, f"liveData.linescore.teams.{side}")
        out[side] = {
            "abbrev": _require(teams[side], "abbreviation"),
            "runs_by_inning": [
                inning[side]["runs"] for inning in innings if "runs" in inning.get(side, {})
            ],
            "runs": _require(totals, "runs"),
            "hits": _require(totals, "hits"),
            "errors": _require(totals, "errors"),
        }
    return out


def parse_decisions(feed: dict) -> dict:
    """Winning/losing pitcher and save (save may be absent)."""
    decisions = _require(feed, "liveData.decisions")
    out = {}
    for role in ("winner", "loser", "save"):
        person = decisions.get(role)
        out[role] = (
            {"id": _require(person, "id"), "name": _require(person, "fullName")}
            if person
            else None
        )
    if out["winner"] is None or out["loser"] is None:
        raise ParseError("Missing expected field: liveData.decisions.winner/loser")
    return out


def parse_plays(feed: dict, win_probability: list[dict] | None = None) -> pd.DataFrame:
    """One row per play, optionally joined with win-probability entries."""
    rows = []
    for play in _require(feed, "liveData.plays.allPlays"):
        about = _require(play, "about")
        result = _require(play, "result")
        rows.append(
            {
                "at_bat_index": _require(about, "atBatIndex"),
                "inning": _require(about, "inning"),
                "half": _require(about, "halfInning"),
                "batter": _require(play, "matchup.batter.fullName"),
                "pitcher": _require(play, "matchup.pitcher.fullName"),
                "event": _require(result, "event"),
                "event_type": result.get("eventType"),
                "description": _require(result, "description"),
                "rbi": result.get("rbi", 0),
                "home_score": _require(result, "homeScore"),
                "away_score": _require(result, "awayScore"),
                "captivating_index": about.get("captivatingIndex"),
                "is_scoring_play": bool(about.get("isScoringPlay")),
            }
        )
    plays = pd.DataFrame(rows).sort_values("at_bat_index").reset_index(drop=True)
    if win_probability:
        wp = pd.DataFrame(
            [
                {
                    "at_bat_index": e["atBatIndex"],
                    "home_wp": e.get("homeTeamWinProbability"),
                    "home_wpa": e.get("homeTeamWinProbabilityAdded"),
                }
                for e in win_probability
                if "atBatIndex" in e
            ]
        )
        plays = plays.merge(wp, on="at_bat_index", how="left")
    else:
        plays["home_wp"] = None
        plays["home_wpa"] = None
    return plays


def _heuristic_scores(plays: pd.DataFrame) -> pd.Series:
    """Leverage-ish fallback: runs on the play x lateness / closeness,
    doubled on lead changes (taking the lead included)."""
    total_after = plays["home_score"] + plays["away_score"]
    runs_on_play = total_after.diff().fillna(total_after.iloc[0] if len(plays) else 0)
    margin_after = plays["home_score"] - plays["away_score"]
    margin_before = margin_after.shift(1).fillna(0)
    gap_before = margin_before.abs()
    lead_change = (margin_after != 0) & (
        margin_after.apply(lambda m: 0 if m == 0 else (1 if m > 0 else -1))
        != margin_before.apply(lambda m: 0 if m == 0 else (1 if m > 0 else -1))
    )
    scores = runs_on_play * (1 + plays["inning"] / 9) / (1 + gap_before)
    return scores * lead_change.map({True: 2.0, False: 1.0})


def rank_top_plays(
    plays: pd.DataFrame, *, royals_home: bool, n: int = 5
) -> tuple[list[dict], str]:
    """Top plays and the basis used to rank them.

    Basis cascade: win-probability swing when WP joined for >=80% of
    plays; else GUMBO captivatingIndex when present for >=80%; else a
    score/lateness/closeness heuristic. Downstream narration phrases the
    section according to the basis, so degradation never breaks anything.
    """
    if plays.empty:
        return [], "leverage_heuristic"
    wpa = pd.to_numeric(plays["home_wpa"], errors="coerce")
    capt = pd.to_numeric(plays["captivating_index"], errors="coerce")
    if wpa.notna().mean() >= 0.8:
        basis = "win_probability"
        scores = wpa.abs()
    elif capt.notna().mean() >= 0.8:
        basis = "captivating_index"
        scores = capt
    else:
        basis = "leverage_heuristic"
        scores = _heuristic_scores(plays)

    top = plays.assign(_score=scores).nlargest(n, "_score")
    sign = 1.0 if royals_home else -1.0
    out = []
    for rank, (_, row) in enumerate(top.iterrows(), start=1):
        home_wp = row["home_wp"]
        home_wpa = row["home_wpa"]
        if pd.notna(home_wp) and float(home_wp) > 1.5:  # normalize percent scale to 0-1
            home_wp = float(home_wp) / 100
        if pd.notna(home_wpa) and abs(float(home_wpa)) > 1.5:
            home_wpa = float(home_wpa) / 100
        royals_score = row["home_score"] if royals_home else row["away_score"]
        opp_score = row["away_score"] if royals_home else row["home_score"]
        out.append(
            {
                "rank": rank,
                "inning": int(row["inning"]),
                "half": row["half"],
                "at_bat_index": int(row["at_bat_index"]),
                "batter": row["batter"],
                "pitcher": row["pitcher"],
                "event": row["event"],
                "rbi": int(row["rbi"]),
                "description": row["description"],
                "score_after": {"royals": int(royals_score), "opponent": int(opp_score)},
                "wpa_royals": round(sign * float(home_wpa), 3) if pd.notna(home_wpa) else None,
                "wp_royals_after": (
                    round(float(home_wp) if royals_home else 1 - float(home_wp), 3)
                    if pd.notna(home_wp)
                    else None
                ),
                "captivating_index": (
                    int(row["captivating_index"])
                    if pd.notna(row["captivating_index"])
                    else None
                ),
            }
        )
    return out, basis


def _pitching_line(player: dict) -> dict:
    stats = _require(player, "stats.pitching")
    return {
        "id": _require(player, "person.id"),
        "name": _require(player, "person.fullName"),
        "ip": _require(stats, "inningsPitched"),
        "h": _require(stats, "hits"),
        "r": _require(stats, "runs"),
        "er": _require(stats, "earnedRuns"),
        "bb": _require(stats, "baseOnBalls"),
        "k": _require(stats, "strikeOuts"),
        "hr": _require(stats, "homeRuns"),
        "pitches": stats.get("numberOfPitches"),
        "strikes": stats.get("strikes"),
    }


def parse_pitching_lines(feed: dict) -> dict:
    """Royals starter + bullpen and the opposing starter, in appearance order."""
    side = royals_side(feed)
    opp_side = "away" if side == "home" else "home"
    box = _require(feed, "liveData.boxscore.teams")

    def lines(team_side: str) -> list[dict]:
        team = box[team_side]
        players = _require(team, "players")
        result = []
        for pid in _require(team, "pitchers"):
            key = f"ID{pid}"
            if key not in players:
                raise ParseError(f"Missing expected field: boxscore players {key}")
            result.append(_pitching_line(players[key]))
        return result

    royals = lines(side)
    opponent = lines(opp_side)
    if not royals or not opponent:
        raise ParseError("Missing expected field: boxscore pitchers list")
    return {
        "royals_starter": royals[0],
        "royals_bullpen": royals[1:],
        "opponent_starter": opponent[0],
    }


def _batting_line_str(b: dict) -> str:
    parts = [f"{b.get('hits', 0)}-{b.get('atBats', 0)}"]
    for key, label in (("doubles", "2B"), ("triples", "3B"), ("homeRuns", "HR")):
        count = b.get(key, 0)
        if count == 1:
            parts.append(label)
        elif count > 1:
            parts.append(f"{count} {label}")
    for key, label in (("baseOnBalls", "BB"), ("runs", "R"), ("rbi", "RBI")):
        count = b.get(key, 0)
        if count == 1:
            parts.append(label)
        elif count > 1:
            parts.append(f"{count} {label}")
    return ", ".join(parts)


def parse_batting_highlights(feed: dict) -> dict:
    """Royals home runs, multi-hit games, and the best batting line."""
    side = royals_side(feed)
    team = _require(feed, f"liveData.boxscore.teams.{side}")
    players = _require(team, "players")

    home_runs, multi_hit, best = [], [], None
    for player in players.values():
        batting = player.get("stats", {}).get("batting", {})
        if not batting:
            continue
        name = _require(player, "person.fullName")
        if batting.get("homeRuns", 0) > 0:
            home_runs.append(
                {
                    "name": name,
                    "count": batting["homeRuns"],
                    "season_total": (
                        player.get("seasonStats", {}).get("batting", {}).get("homeRuns")
                    ),
                }
            )
        if batting.get("hits", 0) >= 2:
            multi_hit.append(
                {"name": name, "hits": batting["hits"], "ab": batting.get("atBats", 0)}
            )
        key = (batting.get("hits", 0), batting.get("homeRuns", 0), batting.get("rbi", 0))
        if best is None or key > best[0]:
            best = (key, {"name": name, "line": _batting_line_str(batting)})

    multi_hit.sort(key=lambda m: m["hits"], reverse=True)
    return {
        "royals_home_runs": home_runs,
        "royals_multi_hit": multi_hit,
        "royals_top_line": best[1] if best else None,
    }

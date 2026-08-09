"""Rolling and season summaries over the Royals game log.

Pure functions over the game-log DataFrame — reusable from notebooks and
the nightly stat pack alike. These quantify the July 2026 report's themes:
blowout-adjusted run differential and feast-or-famine offense.
"""

import pandas as pd


def _sorted(gamelog: pd.DataFrame) -> pd.DataFrame:
    return gamelog.sort_values(["date", "game_number"]).reset_index(drop=True)


def last_n_summary(
    gamelog: pd.DataFrame,
    n: int = 10,
    *,
    blowout_margin: int = 7,
    low_scoring_max: int = 2,
) -> dict:
    """Summary of the last n games: record, run diff, blowout-adjusted diff,
    and feast-or-famine offense measures."""
    recent = _sorted(gamelog).tail(n)
    if recent.empty:
        return {
            "games": 0,
            "wins": 0,
            "losses": 0,
            "runs_scored": 0,
            "runs_allowed": 0,
            "run_diff": 0,
            "run_diff_excl_blowouts": 0,
            "blowouts_excluded": 0,
            "blowout_margin": blowout_margin,
            "games_le_2_runs": 0,
            "top_game_runs": 0,
            "top_game_run_share": 0.0,
        }
    scored = recent["royals_runs"].astype(int)
    allowed = recent["opponent_runs"].astype(int)
    margin = (scored - allowed).abs()
    blowouts = margin >= blowout_margin
    total_scored = int(scored.sum())
    return {
        "games": len(recent),
        "wins": int((recent["result"] == "W").sum()),
        "losses": int((recent["result"] == "L").sum()),
        "runs_scored": total_scored,
        "runs_allowed": int(allowed.sum()),
        "run_diff": int(scored.sum() - allowed.sum()),
        "run_diff_excl_blowouts": int(scored[~blowouts].sum() - allowed[~blowouts].sum()),
        "blowouts_excluded": int(blowouts.sum()),
        "blowout_margin": blowout_margin,
        "games_le_2_runs": int((scored <= low_scoring_max).sum()),
        "top_game_runs": int(scored.max()),
        "top_game_run_share": (
            round(float(scored.max()) / total_scored, 4) if total_scored else 0.0
        ),
    }


def season_summary(gamelog: pd.DataFrame) -> dict:
    """Season-to-date record, run differential, streak, and last-10 string."""
    games = _sorted(gamelog)
    if games.empty:
        return {
            "wins": 0,
            "losses": 0,
            "run_diff": 0,
            "games_played": 0,
            "streak": "",
            "last10": "0-0",
        }
    results = games["result"].tolist()
    streak_kind = results[-1]
    streak_len = 0
    for result in reversed(results):
        if result != streak_kind:
            break
        streak_len += 1
    last10 = games.tail(10)
    return {
        "wins": int((games["result"] == "W").sum()),
        "losses": int((games["result"] == "L").sum()),
        "run_diff": int(
            games["royals_runs"].astype(int).sum() - games["opponent_runs"].astype(int).sum()
        ),
        "games_played": len(games),
        "streak": f"{streak_kind}{streak_len}",
        "last10": (
            f"{int((last10['result'] == 'W').sum())}-{int((last10['result'] == 'L').sum())}"
        ),
    }

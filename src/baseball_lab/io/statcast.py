"""Baseball Savant (Statcast) pulls, scoped to a single game.

A single game is ~300 pitch rows — far below Savant's 25,000-row query
cap. Primary path queries by game_pk; fallback pulls the whole day for
the team and filters. Savant sometimes lags the night of a game; callers
convert StatcastUnavailable into statcast.available = false in the stat
pack and retry on a later run.
"""

import io as _io
from pathlib import Path

import pandas as pd

from baseball_lab.io.cache import DATA_RAW, FetchError, cached_get_text

SAVANT_CSV_URL = "https://baseballsavant.mlb.com/statcast_search/csv"


class StatcastUnavailable(FetchError):
    """Savant returned no rows for this game (often lag; retry later)."""


def get_statcast_game(
    game_pk: int,
    date: str,
    *,
    cache_dir: Path = DATA_RAW,
    force: bool = False,
) -> pd.DataFrame:
    """Pitch-level Statcast rows for one game. Raises StatcastUnavailable if empty."""
    cache_path = cache_dir / "savant" / f"game_{game_pk}.csv"
    try:
        text = cached_get_text(
            SAVANT_CSV_URL,
            params={"all": "true", "type": "details", "game_pk": game_pk},
            cache_path=cache_path,
            force=force,
        )
        df = _parse_csv(text)
    except (FetchError, pd.errors.ParserError):
        df = pd.DataFrame()
    if df.empty:
        # Fallback: day pull for the team, filtered to this game.
        try:
            text = cached_get_text(
                SAVANT_CSV_URL,
                params={
                    "all": "true",
                    "type": "details",
                    "game_date_gt": date,
                    "game_date_lt": date,
                    "hfTeam": "KC|",
                },
                cache_path=cache_dir / "savant" / f"day_{date}_KC.csv",
                force=force,
            )
            day_df = _parse_csv(text)
        except (FetchError, pd.errors.ParserError) as err:
            raise StatcastUnavailable(f"Savant unreachable for game {game_pk}: {err}") from err
        if "game_pk" in day_df.columns:
            df = day_df[day_df["game_pk"] == game_pk].reset_index(drop=True)
    if df.empty:
        raise StatcastUnavailable(f"Savant returned no rows for game {game_pk} ({date})")
    return df


def _parse_csv(text: str) -> pd.DataFrame:
    if not text.strip():
        return pd.DataFrame()
    return pd.read_csv(_io.StringIO(text))

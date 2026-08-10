"""MLB Stats API (statsapi.mlb.com) pulls with local caching.

The API is free and keyless but officially undocumented; endpoint shapes
are community-documented. Parsers downstream validate the fields they
need and raise on drift.
"""

import logging
from pathlib import Path

from baseball_lab.io.cache import DATA_RAW, FetchError, cached_get_json

logger = logging.getLogger(__name__)

ROYALS_TEAM_ID = 118
STATSAPI_V1 = "https://statsapi.mlb.com/api/v1"
STATSAPI_V11 = "https://statsapi.mlb.com/api/v1.1"


def get_schedule(
    date: str,
    *,
    team_id: int = ROYALS_TEAM_ID,
    cache_dir: Path = DATA_RAW,
    force: bool = False,
) -> dict:
    """Schedule for one date (YYYY-MM-DD) for one team."""
    return cached_get_json(
        f"{STATSAPI_V1}/schedule",
        params={"sportId": 1, "teamId": team_id, "date": date},
        cache_path=cache_dir / "statsapi" / "schedule" / f"{date}_t{team_id}.json",
        force=force,
    )


def get_schedule_range(
    start: str,
    end: str,
    *,
    team_id: int = ROYALS_TEAM_ID,
    hydrate: str = "linescore,decisions,team",
    cache_dir: Path = DATA_RAW,
    force: bool = False,
) -> dict:
    """Hydrated schedule over a date range — used for season game-log backfill."""
    return cached_get_json(
        f"{STATSAPI_V1}/schedule",
        params={
            "sportId": 1,
            "teamId": team_id,
            "startDate": start,
            "endDate": end,
            "hydrate": hydrate,
        },
        cache_path=cache_dir / "statsapi" / "schedule" / f"{start}_{end}_t{team_id}.json",
        force=force,
    )


def get_live_feed(game_pk: int, *, cache_dir: Path = DATA_RAW, force: bool = False) -> dict:
    """GUMBO live feed: full game state, play-by-play, boxscore."""
    return cached_get_json(
        f"{STATSAPI_V11}/game/{game_pk}/feed/live",
        cache_path=cache_dir / "statsapi" / "gumbo" / f"{game_pk}.json",
        force=force,
    )


def get_win_probability(
    game_pk: int, *, cache_dir: Path = DATA_RAW, force: bool = False
) -> list[dict]:
    """Per-at-bat win probability entries.

    Returns [] on failure instead of raising — win probability is an
    enhancement with a designed ranking fallback, the one permitted
    soft failure in the ingest layer.
    """
    try:
        data = cached_get_json(
            f"{STATSAPI_V1}/game/{game_pk}/winProbability",
            cache_path=cache_dir / "statsapi" / "wp" / f"{game_pk}.json",
            force=force,
        )
    except FetchError as err:
        logger.warning("winProbability unavailable for game %s: %s", game_pk, err)
        return []
    if isinstance(data, list):
        return data
    logger.warning("winProbability for game %s had unexpected shape %s", game_pk, type(data))
    return []


def final_games(schedule: dict) -> list[dict]:
    """Extract Final games from a schedule response, doubleheaders in order.

    Skips postponed, suspended, and in-progress games — they'll be picked
    up by a later run once they reach Final.
    """
    games = []
    for date_entry in schedule.get("dates", []):
        for game in date_entry.get("games", []):
            if game.get("status", {}).get("codedGameState") == "F":
                games.append(game)
    games.sort(key=lambda g: (g.get("officialDate", ""), g.get("gameNumber", 1)))
    return games

"""Live smoke tests against real MLB endpoints.

Excluded by default (addopts = -m "not live"). Run explicitly with:
    pytest -m live
These require network egress to statsapi.mlb.com and baseballsavant.mlb.com
(available on GitHub Actions runners; blocked in some sandboxes).
"""

import pytest

from baseball_lab.clean.games import parse_game_summary
from baseball_lab.io.statcast import get_statcast_game
from baseball_lab.io.statsapi import (
    final_games,
    get_live_feed,
    get_schedule,
    get_win_probability,
)

# A date the Royals played (and finished) a game: 2026-08-08 vs the Cubs.
KNOWN_GAME_DATE = "2026-08-08"

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def known_game(tmp_path_factory):
    cache = tmp_path_factory.mktemp("live_cache")
    schedule = get_schedule(KNOWN_GAME_DATE, cache_dir=cache)
    games = final_games(schedule)
    assert games, f"expected at least one final Royals game on {KNOWN_GAME_DATE}"
    return {"game_pk": games[0]["gamePk"], "cache": cache}


def test_gumbo_feed_parses(known_game):
    feed = get_live_feed(known_game["game_pk"], cache_dir=known_game["cache"])
    summary = parse_game_summary(feed)
    assert summary["date"] == KNOWN_GAME_DATE
    assert summary["score"]["royals"] >= 0


def test_win_probability_nonempty(known_game):
    entries = get_win_probability(known_game["game_pk"], cache_dir=known_game["cache"])
    assert entries, "winProbability endpoint returned no entries — check ranking fallback"
    assert "homeTeamWinProbabilityAdded" in entries[0]


def test_statcast_returns_rows(known_game):
    df = get_statcast_game(known_game["game_pk"], KNOWN_GAME_DATE, cache_dir=known_game["cache"])
    assert len(df) > 200
    assert "launch_speed" in df.columns

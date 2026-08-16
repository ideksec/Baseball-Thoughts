"""Tests for baseball_lab.metrics.rolling against the engineered game-log fixture.

The fixture's last 10 games mirror the real late-June 2026 stretch:
4-6 with a -18 run differential dominated by a single 1-22 blowout.
"""

import pandas as pd
import pytest

from baseball_lab.metrics.rolling import last_n_summary, season_summary, through_game


class TestLastNSummary:
    def test_last_10(self, gamelog_df):
        summary = last_n_summary(gamelog_df, 10)
        assert summary["wins"] == 4
        assert summary["losses"] == 6
        assert summary["runs_scored"] == 50
        assert summary["runs_allowed"] == 68
        assert summary["run_diff"] == -18
        # Excluding the 1-22 and 15-1 blowouts: 34 scored, 45 allowed
        assert summary["blowouts_excluded"] == 2
        assert summary["run_diff_excl_blowouts"] == -11
        assert summary["games_le_2_runs"] == 5
        assert summary["top_game_runs"] == 16
        assert summary["top_game_run_share"] == pytest.approx(0.32)

    def test_empty_gamelog(self):
        summary = last_n_summary(pd.DataFrame(columns=["date", "game_number", "result"]))
        assert summary["games"] == 0
        assert summary["top_game_run_share"] == 0.0


class TestSeasonSummary:
    def test_season(self, gamelog_df):
        summary = season_summary(gamelog_df)
        assert summary["wins"] == 5
        assert summary["losses"] == 7
        assert summary["run_diff"] == -19
        assert summary["games_played"] == 12
        assert summary["streak"] == "W3"
        assert summary["last10"] == "4-6"

    def test_empty(self):
        assert season_summary(pd.DataFrame(columns=["date", "game_number", "result"]))[
            "last10"
        ] == "0-0"


class TestThroughGame:
    """Regression: the nightly job upserts a multi-day lookback before building
    packs, so the log it passes routinely extends past the game being written
    up. Rolling numbers must describe that game, not the newest row."""

    def test_trims_later_games(self, gamelog_df):
        games = gamelog_df.sort_values(["date", "game_number"]).reset_index(drop=True)
        target = games.iloc[-3]
        trimmed = through_game(
            gamelog_df, date=target["date"], game_number=int(target["game_number"])
        )
        assert len(trimmed) == len(games) - 2
        assert trimmed.iloc[-1]["date"] == target["date"]

    def test_season_summary_matches_the_trimmed_game(self, gamelog_df):
        games = gamelog_df.sort_values(["date", "game_number"]).reset_index(drop=True)
        target = games.iloc[-3]
        trimmed = through_game(
            gamelog_df, date=target["date"], game_number=int(target["game_number"])
        )
        summary = season_summary(trimmed)
        assert summary["games_played"] == len(games) - 2
        assert summary["wins"] + summary["losses"] == summary["games_played"]

    def test_full_log_is_unchanged(self, gamelog_df):
        games = gamelog_df.sort_values(["date", "game_number"]).reset_index(drop=True)
        last = games.iloc[-1]
        trimmed = through_game(
            gamelog_df, date=last["date"], game_number=int(last["game_number"])
        )
        assert len(trimmed) == len(games)

    def test_empty_log(self):
        empty = pd.DataFrame(columns=["date", "game_number", "result"])
        assert through_game(empty, date="2026-08-07").empty

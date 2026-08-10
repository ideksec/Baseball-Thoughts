"""Tests for baseball_lab.io.statsapi (offline)."""

import copy

from baseball_lab.io import statsapi
from baseball_lab.io.cache import FetchError
from baseball_lab.io.statsapi import final_games, get_win_probability


class TestFinalGames:
    def test_single_game(self, schedule_gameday):
        games = final_games(schedule_gameday)
        assert [g["gamePk"] for g in games] == [777001]

    def test_doubleheader_sorted_by_game_number(self, schedule_doubleheader):
        games = final_games(schedule_doubleheader)
        assert [g["gamePk"] for g in games] == [777002, 777003]
        assert [g["gameNumber"] for g in games] == [1, 2]

    def test_empty_schedule(self, schedule_empty):
        assert final_games(schedule_empty) == []

    def test_skips_non_final_games(self, schedule_gameday):
        sched = copy.deepcopy(schedule_gameday)
        sched["dates"][0]["games"][0]["status"]["codedGameState"] = "I"
        assert final_games(sched) == []


class TestWinProbabilitySoftFailure:
    def test_fetch_error_returns_empty(self, monkeypatch, tmp_path):
        def boom(*args, **kwargs):
            raise FetchError("HTTP 404")

        monkeypatch.setattr(statsapi, "cached_get_json", boom)
        assert get_win_probability(777001, cache_dir=tmp_path) == []

    def test_unexpected_shape_returns_empty(self, monkeypatch, tmp_path):
        monkeypatch.setattr(statsapi, "cached_get_json", lambda *a, **kw: {"not": "a list"})
        assert get_win_probability(777001, cache_dir=tmp_path) == []

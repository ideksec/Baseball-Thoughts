"""Tests for baseball_lab.clean.games against the trimmed GUMBO fixture."""

import copy

import pytest

from baseball_lab.clean.games import (
    ParseError,
    parse_batting_highlights,
    parse_decisions,
    parse_game_summary,
    parse_linescore,
    parse_pitching_lines,
    parse_plays,
    rank_top_plays,
)


class TestParseGameSummary:
    def test_summary(self, gumbo_feed):
        summary = parse_game_summary(gumbo_feed)
        assert summary["game_pk"] == 777001
        assert summary["date"] == "2026-08-08"
        assert summary["home_away"] == "home"
        assert summary["opponent"]["abbrev"] == "CWS"
        assert summary["result"] == "W"
        assert summary["score"] == {"royals": 5, "opponent": 3}
        assert summary["innings"] == 9
        assert summary["walk_off"] is False
        assert summary["royals_record_after"] == {"wins": 56, "losses": 62}

    def test_missing_field_raises(self, gumbo_feed):
        broken = copy.deepcopy(gumbo_feed)
        del broken["gameData"]["venue"]
        with pytest.raises(ParseError, match="gameData.venue.name"):
            parse_game_summary(broken)

    def test_walk_off_detected(self, gumbo_feed):
        feed = copy.deepcopy(gumbo_feed)
        last = feed["liveData"]["plays"]["allPlays"][-1]
        last["about"]["halfInning"] = "bottom"
        last["about"]["isScoringPlay"] = True
        assert parse_game_summary(feed)["walk_off"] is True


class TestParseLinescore:
    def test_linescore(self, gumbo_feed):
        ls = parse_linescore(gumbo_feed)
        assert ls["away"]["runs_by_inning"] == [0, 0, 1, 0, 2, 0, 0, 0, 0]
        assert ls["home"]["runs_by_inning"] == [2, 0, 0, 0, 0, 3, 0, 0]  # home didn't bat 9th
        assert ls["home"] | {"runs_by_inning": None} == {
            "abbrev": "KC",
            "runs_by_inning": None,
            "runs": 5,
            "hits": 9,
            "errors": 0,
        }


class TestParseDecisions:
    def test_decisions(self, gumbo_feed):
        decisions = parse_decisions(gumbo_feed)
        assert decisions["winner"]["name"] == "Noah Cameron"
        assert decisions["loser"]["name"] == "Grant Taylor"
        assert decisions["save"]["name"] == "Carlos Estevez"

    def test_no_save_is_none(self, gumbo_feed):
        feed = copy.deepcopy(gumbo_feed)
        del feed["liveData"]["decisions"]["save"]
        assert parse_decisions(feed)["save"] is None


class TestRankTopPlays:
    def test_win_probability_basis(self, gumbo_feed, wp_entries):
        plays = parse_plays(gumbo_feed, wp_entries)
        top, basis = rank_top_plays(plays, royals_home=True)
        assert basis == "win_probability"
        assert top[0]["at_bat_index"] == 47  # Perez 3-run HR, |WPA| 28.4
        assert top[0]["wpa_royals"] == pytest.approx(0.284)
        assert top[0]["wp_royals_after"] == pytest.approx(0.78)
        assert top[0]["score_after"] == {"royals": 5, "opponent": 3}
        assert top[1]["at_bat_index"] == 33  # Vaughn go-ahead HR, |WPA| 22
        assert top[1]["wpa_royals"] == pytest.approx(-0.22)
        assert len(top) == 5

    def test_captivating_index_basis(self, gumbo_feed):
        plays = parse_plays(gumbo_feed, win_probability=None)
        top, basis = rank_top_plays(plays, royals_home=True)
        assert basis == "captivating_index"
        assert top[0]["at_bat_index"] == 47  # highest captivatingIndex (62)
        assert top[0]["wpa_royals"] is None

    def test_leverage_heuristic_basis(self, gumbo_feed):
        feed = copy.deepcopy(gumbo_feed)
        for play in feed["liveData"]["plays"]["allPlays"]:
            del play["about"]["captivatingIndex"]
        plays = parse_plays(feed, win_probability=None)
        top, basis = rank_top_plays(plays, royals_home=True)
        assert basis == "leverage_heuristic"
        # Go-ahead 3-run HR in the 6th outranks everything else
        assert top[0]["at_bat_index"] == 47


class TestParsePitchingLines:
    def test_lines(self, gumbo_feed):
        pitching = parse_pitching_lines(gumbo_feed)
        starter = pitching["royals_starter"]
        assert starter["name"] == "Noah Cameron"
        assert starter["ip"] == "6.1"
        assert starter["k"] == 7
        assert starter["pitches"] == 94
        assert [p["name"] for p in pitching["royals_bullpen"]] == [
            "Daniel Lynch IV",
            "Carlos Estevez",
        ]
        assert pitching["opponent_starter"]["name"] == "Grant Taylor"
        assert pitching["opponent_starter"]["er"] == 5


class TestParseBattingHighlights:
    def test_highlights(self, gumbo_feed):
        highlights = parse_batting_highlights(gumbo_feed)
        hr_names = {h["name"]: h["season_total"] for h in highlights["royals_home_runs"]}
        assert hr_names == {"Jac Caglianone": 21, "Salvador Perez": 18}
        assert highlights["royals_multi_hit"][0] == {
            "name": "Bobby Witt Jr.",
            "hits": 3,
            "ab": 4,
        }
        assert highlights["royals_top_line"] == {
            "name": "Bobby Witt Jr.",
            "line": "3-4, 2B, 2 R",
        }

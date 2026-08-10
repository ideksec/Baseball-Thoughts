"""Tests for baseball_lab.statpack."""

import copy
import json

import pytest

from baseball_lab.clean.gamelog import gamelog_row
from baseball_lab.statpack import (
    StatPackError,
    build_stat_pack,
    report_filename,
    stat_pack_path,
    validate_stat_pack,
    write_stat_pack,
)


@pytest.fixture
def full_gamelog(gamelog_df, gumbo_feed):
    import pandas as pd

    return pd.concat(
        [gamelog_df, pd.DataFrame([gamelog_row(gumbo_feed)])], ignore_index=True
    )


@pytest.fixture
def pack(gumbo_feed, wp_entries, statcast_df, full_gamelog):
    return build_stat_pack(
        feed=gumbo_feed,
        win_probability=wp_entries,
        statcast_df=statcast_df,
        gamelog=full_gamelog,
    )


class TestBuildStatPack:
    def test_valid_and_complete(self, pack):
        validate_stat_pack(pack)
        assert pack["sources"] == {
            "statsapi_gumbo": True,
            "win_probability_endpoint": True,
            "statcast": True,
            "statcast_error": None,
        }
        assert pack["top_plays_ranking_basis"] == "win_probability"
        assert pack["game"]["result"] == "W"
        # Rolling reflects the game just added (W after the fixture's W3 streak)
        assert pack["rolling"]["season"]["streak"] == "W4"
        assert pack["rolling"]["season"]["games_played"] == 13

    def test_statcast_unavailable_degrades(self, gumbo_feed, wp_entries, full_gamelog):
        pack = build_stat_pack(
            feed=gumbo_feed,
            win_probability=wp_entries,
            statcast_df=None,
            gamelog=full_gamelog,
            statcast_error="Savant returned no rows",
        )
        validate_stat_pack(pack)
        assert pack["statcast"] == {"available": False}
        assert pack["sources"]["statcast"] is False
        assert pack["sources"]["statcast_error"] == "Savant returned no rows"

    def test_no_wp_falls_back(self, gumbo_feed, statcast_df, full_gamelog):
        pack = build_stat_pack(
            feed=gumbo_feed,
            win_probability=[],
            statcast_df=statcast_df,
            gamelog=full_gamelog,
        )
        assert pack["sources"]["win_probability_endpoint"] is False
        assert pack["top_plays_ranking_basis"] == "captivating_index"


class TestWriteStatPack:
    def test_write_path_and_size(self, pack, tmp_path):
        path = write_stat_pack(pack, tmp_path)
        assert path == tmp_path / "processed" / "royals" / "statpacks" / "2026-08-08_777001.json"
        assert path.stat().st_size < 20_000
        assert json.loads(path.read_text())["game"]["game_pk"] == 777001

    def test_stat_pack_path(self, tmp_path):
        assert stat_pack_path(tmp_path, "2026-08-08", 777001).name == "2026-08-08_777001.json"


class TestValidate:
    def test_missing_key_raises(self, pack):
        broken = {k: v for k, v in pack.items() if k != "rolling"}
        with pytest.raises(StatPackError, match="rolling"):
            validate_stat_pack(broken)

    def test_wrong_version_raises(self, pack):
        broken = copy.deepcopy(pack)
        broken["schema_version"] = 99
        with pytest.raises(StatPackError, match="schema_version"):
            validate_stat_pack(broken)


class TestReportFilename:
    def test_home_game(self, pack):
        assert report_filename(pack) == "2026-08-08_vs-cws.md"

    def test_away_doubleheader(self, pack):
        away = copy.deepcopy(pack)
        away["game"]["home_away"] = "away"
        away["game"]["doubleheader"] = "Y"
        away["game"]["game_number"] = 2
        assert report_filename(away) == "2026-08-08_at-cws_gm2.md"

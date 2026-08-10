"""Tests for baseball_lab.clean.gamelog."""

from baseball_lab.clean.gamelog import (
    GAMELOG_COLUMNS,
    gamelog_row,
    gamelog_row_from_schedule_game,
    load_gamelog,
    upsert_gamelog,
)


class TestGamelogRow:
    def test_from_gumbo(self, gumbo_feed):
        row = gamelog_row(gumbo_feed, statpack="data/processed/royals/statpacks/x.json")
        assert row["game_pk"] == 777001
        assert row["result"] == "W"
        assert row["royals_runs"] == 5
        assert row["opponent_abbrev"] == "CWS"
        assert row["save_pitcher"] == "Carlos Estevez"
        assert row["royals_starter"] == "Noah Cameron"
        assert row["royals_starter_ip"] == "6.1"
        assert row["royals_wins_after"] == 56
        assert set(row) == set(GAMELOG_COLUMNS)

    def test_from_schedule_game(self, schedule_gameday):
        game = schedule_gameday["dates"][0]["games"][0]
        row = gamelog_row_from_schedule_game(game)
        assert row["game_pk"] == 777001
        assert row["result"] == "W"
        assert row["royals_runs"] == 5
        assert row["opponent_runs"] == 3
        assert row["royals_wins_after"] == 56
        assert set(row) == set(GAMELOG_COLUMNS)


class TestUpsert:
    def test_idempotent(self, tmp_path, gumbo_feed):
        path = tmp_path / "gamelog.csv"
        row = gamelog_row(gumbo_feed)
        upsert_gamelog(path, [row])
        result = upsert_gamelog(path, [row])
        assert len(result) == 1
        assert len(load_gamelog(path)) == 1

    def test_sorted_by_date_and_game_number(self, tmp_path, gumbo_feed):
        path = tmp_path / "gamelog.csv"
        row1 = gamelog_row(gumbo_feed)
        row2 = dict(row1, game_pk=777099, date="2026-08-07")
        row3 = dict(row1, game_pk=777098, date="2026-08-08", game_number=2, doubleheader="Y")
        upsert_gamelog(path, [row3, row1, row2])
        result = load_gamelog(path)
        assert result["game_pk"].tolist() == [777099, 777001, 777098]

    def test_dry_run_does_not_write(self, tmp_path, gumbo_feed):
        path = tmp_path / "gamelog.csv"
        result = upsert_gamelog(path, [gamelog_row(gumbo_feed)], write=False)
        assert len(result) == 1
        assert not path.exists()

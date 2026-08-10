"""Orchestration tests for scripts/nightly_royals.py with monkeypatched fetchers."""

import copy
import importlib.util
import json
from datetime import datetime
from pathlib import Path

import pytest

from baseball_lab.io.statcast import StatcastUnavailable

FIXTURES = Path(__file__).parent / "fixtures"


def load_json_fixture(name: str):
    return json.loads((FIXTURES / name).read_text())


SCRIPT = Path(__file__).parent.parent / "scripts" / "nightly_royals.py"
_spec = importlib.util.spec_from_file_location("nightly_royals", SCRIPT)
nightly = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nightly)


class _FrozenDatetime(datetime):
    """Pin 'now' to the day after the fixture game so retry-window logic is stable."""

    @classmethod
    def now(cls, tz=None):
        return cls(2026, 8, 9, 12, 0, tzinfo=tz)


@pytest.fixture
def wired(monkeypatch, statcast_df):
    """Wire the script's fetchers to fixtures; no network possible."""
    monkeypatch.setattr(nightly, "datetime", _FrozenDatetime)
    monkeypatch.setattr(
        nightly,
        "get_schedule",
        lambda date, **kw: (
            load_json_fixture("statsapi_schedule_gameday.json")
            if date == "2026-08-08"
            else load_json_fixture("statsapi_schedule_empty.json")
        ),
    )

    def fake_feed(game_pk, **kw):
        feed = copy.deepcopy(load_json_fixture("gumbo_feed_trimmed.json"))
        feed["gamePk"] = game_pk
        feed["gameData"]["game"]["pk"] = game_pk
        return feed

    monkeypatch.setattr(nightly, "get_live_feed", fake_feed)
    monkeypatch.setattr(
        nightly, "get_win_probability", lambda pk, **kw: load_json_fixture("win_probability.json")
    )
    monkeypatch.setattr(nightly, "get_statcast_game", lambda pk, date, **kw: statcast_df)
    return monkeypatch


class TestNoGameDay:
    def test_noop_and_exit_zero(self, wired, tmp_path, capsys):
        assert nightly.main(["--date", "2026-08-07", "--data-root", str(tmp_path)]) == 0
        assert "RESULT: no-games 2026-08-07" in capsys.readouterr().out
        assert not (tmp_path / "processed").exists()


class TestSingleGame:
    def test_writes_pack_and_gamelog(self, wired, tmp_path, capsys):
        assert nightly.main(["--date", "2026-08-08", "--data-root", str(tmp_path)]) == 0
        out = capsys.readouterr().out
        assert "RESULT: wrote 2026-08-08 game 777001 W 5-3 (with statcast)" in out
        pack_path = tmp_path / "processed" / "royals" / "statpacks" / "2026-08-08_777001.json"
        assert pack_path.exists()
        gamelog = (tmp_path / "processed" / "royals" / "gamelog_2026.csv").read_text()
        assert gamelog.count("\n") == 2  # header + one row

    def test_idempotent_second_run(self, wired, tmp_path, capsys):
        nightly.main(["--date", "2026-08-08", "--data-root", str(tmp_path)])
        capsys.readouterr()
        nightly.main(["--date", "2026-08-08", "--data-root", str(tmp_path)])
        assert "RESULT: exists 2026-08-08 game 777001" in capsys.readouterr().out

    def test_dry_run_writes_nothing(self, wired, tmp_path, capsys):
        assert (
            nightly.main(["--date", "2026-08-08", "--dry-run", "--data-root", str(tmp_path)])
            == 0
        )
        out = capsys.readouterr().out
        assert "RESULT: dry-run 2026-08-08 game 777001" in out
        assert '"schema_version": 1' in out  # pack JSON printed for inspection
        assert not (tmp_path / "processed").exists()


class TestStatcastRetry:
    def test_unavailable_then_retried(self, wired, tmp_path, capsys, statcast_df):
        def unavailable(pk, date, **kw):
            raise StatcastUnavailable("Savant returned no rows")

        wired.setattr(nightly, "get_statcast_game", unavailable)
        nightly.main(["--date", "2026-08-08", "--data-root", str(tmp_path)])
        pack_path = tmp_path / "processed" / "royals" / "statpacks" / "2026-08-08_777001.json"
        assert json.loads(pack_path.read_text())["sources"]["statcast"] is False
        assert "NO statcast" in capsys.readouterr().out

        # Next night's run (still inside the retry window) fills Statcast in.
        wired.setattr(nightly, "get_statcast_game", lambda pk, date, **kw: statcast_df)
        nightly.main(["--date", "2026-08-08", "--data-root", str(tmp_path)])
        assert json.loads(pack_path.read_text())["sources"]["statcast"] is True
        assert "with statcast" in capsys.readouterr().out


class TestDoubleheader:
    def test_two_packs_two_rows(self, wired, tmp_path, capsys):
        wired.setattr(
            nightly,
            "get_schedule",
            lambda date, **kw: load_json_fixture("statsapi_schedule_doubleheader.json"),
        )

        def fake_feed(game_pk, **kw):
            feed = copy.deepcopy(load_json_fixture("gumbo_feed_trimmed.json"))
            feed["gamePk"] = game_pk
            feed["gameData"]["game"]["pk"] = game_pk
            feed["gameData"]["game"]["doubleHeader"] = "Y"
            feed["gameData"]["game"]["gameNumber"] = 1 if game_pk == 777002 else 2
            feed["gameData"]["datetime"]["officialDate"] = "2026-08-15"
            return feed

        wired.setattr(nightly, "get_live_feed", fake_feed)
        assert nightly.main(["--date", "2026-08-15", "--data-root", str(tmp_path)]) == 0
        out = capsys.readouterr().out
        assert "game 777002" in out and "game 777003" in out
        packs = tmp_path / "processed" / "royals" / "statpacks"
        assert (packs / "2026-08-15_777002.json").exists()
        assert (packs / "2026-08-15_777003.json").exists()
        gamelog = (tmp_path / "processed" / "royals" / "gamelog_2026.csv").read_text()
        assert gamelog.count("\n") == 3  # header + two rows


class TestBackfill:
    def test_seeds_gamelog_without_packs(self, wired, tmp_path, capsys):
        wired.setattr(
            nightly,
            "get_schedule_range",
            lambda start, end, **kw: load_json_fixture("statsapi_schedule_gameday.json"),
        )
        code = nightly.main(
            ["--backfill", "2026-03-26:2026-08-08", "--data-root", str(tmp_path)]
        )
        assert code == 0
        assert "added 1 games" in capsys.readouterr().out
        assert (tmp_path / "processed" / "royals" / "gamelog_2026.csv").exists()
        assert not (tmp_path / "processed" / "royals" / "statpacks").exists()

    def test_backfill_never_overwrites_nightly_rows(self, wired, tmp_path, capsys):
        nightly.main(["--date", "2026-08-08", "--data-root", str(tmp_path)])
        wired.setattr(
            nightly,
            "get_schedule_range",
            lambda start, end, **kw: load_json_fixture("statsapi_schedule_gameday.json"),
        )
        nightly.main(["--backfill", "2026-03-26:2026-08-08", "--data-root", str(tmp_path)])
        out = capsys.readouterr().out
        assert "backfill-noop" in out
        gamelog = (tmp_path / "processed" / "royals" / "gamelog_2026.csv").read_text()
        assert "Noah Cameron" in gamelog  # rich nightly row kept

"""Tests for scripts/pipeline_health.py.

Each check is exercised against both a healthy pipeline and the specific
breakage it exists to catch — including a reconstruction of the August 2026
outage, where reports stopped reaching main and the site stopped deploying.
"""

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).parent.parent

SCRIPT = REPO_ROOT / "scripts" / "pipeline_health.py"
_spec = importlib.util.spec_from_file_location("pipeline_health", SCRIPT)
pipeline_health = importlib.util.module_from_spec(_spec)
# @dataclass resolves its module through sys.modules, so register before exec.
sys.modules["pipeline_health"] = pipeline_health
_spec.loader.exec_module(pipeline_health)


def make_pack(date_str: str, *, home_away: str = "home", opponent: str = "CWS") -> dict:
    """The minimum stat pack shape the health check reads."""
    return {
        "game": {
            "date": date_str,
            "game_pk": 824070,
            "home_away": home_away,
            "opponent": {"abbrev": opponent},
            "doubleheader": "N",
            "game_number": 1,
        }
    }


@pytest.fixture
def gamelog() -> pd.DataFrame:
    """Two pre-pipeline backfill rows, then two rows with stat packs."""
    return pd.DataFrame(
        [
            {"date": "2026-04-01", "game_pk": 1, "statpack": ""},
            {"date": "2026-04-02", "game_pk": 2, "statpack": ""},
            {"date": "2026-08-07", "game_pk": 3, "statpack": "packs/a.json"},
            {"date": "2026-08-08", "game_pk": 4, "statpack": "packs/b.json"},
        ]
    )


@pytest.fixture
def pack_root(tmp_path) -> Path:
    """A tree where every stat pack the game log references exists."""
    (tmp_path / "packs").mkdir()
    for name in ("a.json", "b.json"):
        (tmp_path / "packs" / name).write_text("{}")
    return tmp_path


# --- check 1: game log freshness -----------------------------------------


def test_fresh_gamelog_passes(gamelog):
    check = pipeline_health.check_gamelog_fresh(gamelog, date(2026, 8, 10))
    assert check.ok


def test_stale_gamelog_fails_in_season(gamelog):
    """Stage 1 dying is invisible otherwise: no pack is written, so every
    downstream check stays green while the season goes unrecorded."""
    check = pipeline_health.check_gamelog_fresh(gamelog, date(2026, 8, 20))
    assert not check.ok
    assert "2026-08-08" in check.failures[0]
    assert "stage 1" in check.failures[0]


def test_allstar_break_gap_does_not_fail(gamelog):
    """A four-day gap is the All-Star break, not a fault."""
    check = pipeline_health.check_gamelog_fresh(gamelog, date(2026, 8, 12))
    assert check.ok


def test_offseason_staleness_is_skipped(gamelog):
    check = pipeline_health.check_gamelog_fresh(gamelog, date(2027, 1, 15))
    assert check.ok
    assert check.skipped == "off-season"


def test_completed_season_is_skipped():
    """162 logged games means the season ended, not that ingest stalled."""
    full = pd.DataFrame(
        [{"date": "2026-09-27", "game_pk": i, "statpack": "p.json"} for i in range(162)]
    )
    check = pipeline_health.check_gamelog_fresh(full, date(2026, 11, 1))
    assert check.ok
    assert "season complete" in check.skipped


def test_missing_gamelog_fails():
    check = pipeline_health.check_gamelog_fresh(pd.DataFrame(), date(2026, 8, 10))
    assert not check.ok


# --- check 2: packs cover logged games ------------------------------------


def test_packs_cover_gamelog_passes(gamelog, pack_root):
    check = pipeline_health.check_packs_cover_gamelog(gamelog, root=pack_root)
    assert check.ok


def test_backfilled_rows_before_the_pipeline_are_exempt(gamelog, pack_root):
    """The 116 pre-2026-08-07 schedule rows legitimately have no packs."""
    check = pipeline_health.check_packs_cover_gamelog(gamelog, root=pack_root)
    assert check.ok
    assert "2026-04-01" not in check.render()


def test_gap_in_packs_after_pipeline_start_fails(gamelog, pack_root):
    gamelog.loc[gamelog["date"] == "2026-08-08", "statpack"] = ""
    check = pipeline_health.check_packs_cover_gamelog(gamelog, root=pack_root)
    assert not check.ok
    assert "2026-08-08" in check.failures[0]


def test_pack_referenced_but_deleted_fails(gamelog, pack_root):
    (pack_root / "packs" / "b.json").unlink()
    check = pipeline_health.check_packs_cover_gamelog(gamelog, root=pack_root)
    assert not check.ok
    assert "missing from disk" in check.failures[0]


# --- check 3: reports cover stat packs ------------------------------------


@pytest.fixture
def packs_and_reports(tmp_path):
    daily = tmp_path / "daily"
    daily.mkdir()
    packs = []
    for date_str, home_away, opp in [
        ("2026-08-07", "home", "CHC"),
        ("2026-08-08", "away", "LAD"),
    ]:
        pack = make_pack(date_str, home_away=home_away, opponent=opp)
        path = tmp_path / f"{date_str}.json"
        path.write_text(json.dumps(pack))
        packs.append((path, pack))
        prefix = "vs" if home_away == "home" else "at"
        (daily / f"{date_str}_{prefix}-{opp.lower()}.md").write_text("# Report\n")
    return packs, daily


def test_reports_cover_packs_passes(packs_and_reports):
    packs, daily = packs_and_reports
    assert pipeline_health.check_reports_cover_packs(packs, daily).ok


def test_missing_report_fails(packs_and_reports):
    """The August outage: packs kept landing, reports stopped reaching main."""
    packs, daily = packs_and_reports
    (daily / "2026-08-08_at-lad.md").unlink()
    check = pipeline_health.check_reports_cover_packs(packs, daily)
    assert not check.ok
    assert "2026-08-08_at-lad.md" in check.failures[0]


def test_report_filename_contract_is_shared_with_the_pipeline(tmp_path):
    """The check must use baseball_lab's filename contract, not its own copy,
    or a doubleheader would read as a missing report."""
    daily = tmp_path / "daily"
    daily.mkdir()
    pack = make_pack("2026-08-15", home_away="away", opponent="MIN")
    pack["game"]["doubleheader"] = "Y"
    pack["game"]["game_number"] = 2
    (daily / "2026-08-15_at-min_gm2.md").write_text("# Nightcap\n")
    check = pipeline_health.check_reports_cover_packs([(tmp_path / "p.json", pack)], daily)
    assert check.ok


# --- check 4: published site is current -----------------------------------


def test_site_current_passes(monkeypatch):
    packs = [(Path("p.json"), make_pack("2026-09-01", home_away="home", opponent="MIA"))]
    monkeypatch.setattr(
        pipeline_health.requests, "get", _fake_get('<a href="2026-09-01_vs-mia.html">')
    )
    assert pipeline_health.check_site_current(packs, url="http://example.test/").ok


def test_stale_site_fails(monkeypatch):
    """The Pages outage: the last good site stayed up while deploys 404'd."""
    packs = [(Path("p.json"), make_pack("2026-09-01", home_away="home", opponent="MIA"))]
    monkeypatch.setattr(
        pipeline_health.requests, "get", _fake_get('<a href="2026-08-14_at-laa.html">')
    )
    check = pipeline_health.check_site_current(packs, url="http://example.test/")
    assert not check.ok
    assert "2026-09-01_vs-mia" in check.failures[0]
    assert "stage 3" in check.failures[0]


def test_unreachable_site_fails(monkeypatch):
    packs = [(Path("p.json"), make_pack("2026-09-01"))]

    def boom(*args, **kwargs):
        raise pipeline_health.requests.RequestException("connection refused")

    monkeypatch.setattr(pipeline_health.requests, "get", boom)
    check = pipeline_health.check_site_current(packs, url="http://example.test/")
    assert not check.ok
    assert "could not fetch" in check.failures[0]


def _fake_get(body: str):
    class Response:
        text = body

        def raise_for_status(self):
            return None

    def get(*args, **kwargs):
        return Response()

    return get


# --- exit status ----------------------------------------------------------


def test_main_reports_healthy_repo_offline(capsys):
    """The committed repo itself passes every offline check."""
    assert pipeline_health.main(["--offline"]) == 0
    assert "pipeline healthy" in capsys.readouterr().out


def test_check_render_lists_every_failure():
    check = pipeline_health.Check("demo", failures=["one", "two"])
    rendered = check.render()
    assert rendered.startswith("FAIL demo")
    assert "- one" in rendered and "- two" in rendered

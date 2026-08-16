"""Tests for scripts/build_site.py, including the committed reports themselves."""

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).parent.parent
DAILY_DIR = REPO_ROOT / "reports" / "royals" / "daily"

SCRIPT = REPO_ROOT / "scripts" / "build_site.py"
_spec = importlib.util.spec_from_file_location("build_site", SCRIPT)
build_site = importlib.util.module_from_spec(_spec)
# @dataclass resolves its module through sys.modules, so register before exec.
sys.modules["build_site"] = build_site
_spec.loader.exec_module(build_site)


@pytest.fixture
def daily_dir(tmp_path):
    """A reports directory with two games, one of them a doubleheader nightcap."""
    d = tmp_path / "daily"
    d.mkdir()
    (d / "2026-08-07_vs-chc.md").write_text("# Cubs 6, Royals 4: a four-run second\n\nBody.\n")
    (d / "2026-08-15_at-min_gm2.md").write_text("# Royals 3, Twins 1: nightcap\n\nBody.\n")
    (d / "notes.txt").write_text("not a report")
    (d / "draft.md").write_text("# Does not match the filename contract\n")
    return d


@pytest.fixture
def gamelog_dir(tmp_path):
    d = tmp_path / "log"
    d.mkdir()
    pd.DataFrame(
        [
            {
                "date": "2026-08-07",
                "game_number": 1,
                "result": "L",
                "royals_runs": 4,
                "opponent_runs": 6,
                "royals_wins_after": 48,
                "royals_losses_after": 69,
            },
            {
                "date": "2026-08-15",
                "game_number": 2,
                "result": "W",
                "royals_runs": 3,
                "opponent_runs": 1,
                "royals_wins_after": 51,
                "royals_losses_after": 73,
            },
        ]
    ).to_csv(d / "gamelog_2026.csv", index=False)
    return d


class TestCollectReports:
    def test_newest_first(self, daily_dir):
        reports = build_site.collect_reports(daily_dir)
        assert [r.date for r in reports] == ["2026-08-15", "2026-08-07"]

    def test_parses_filename_contract(self, daily_dir):
        nightcap, opener = build_site.collect_reports(daily_dir)
        assert (nightcap.home_away, nightcap.opponent, nightcap.game_number) == ("at", "min", 2)
        assert (opener.home_away, opener.opponent, opener.game_number) == ("vs", "chc", 1)
        assert nightcap.matchup == "at MIN"
        assert opener.matchup == "vs CHC"

    def test_skips_files_outside_the_contract(self, daily_dir):
        slugs = {r.slug for r in build_site.collect_reports(daily_dir)}
        assert "draft" not in slugs and "notes" not in slugs

    def test_title_is_the_first_heading(self, daily_dir):
        assert build_site.collect_reports(daily_dir)[1].title.startswith("Cubs 6, Royals 4")


class TestRenderMarkdown:
    def test_tables_are_wrapped_for_narrow_screens(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |\n"
        html = build_site.render_markdown(md)
        assert '<div class="table-scroll"><table>' in html
        assert html.count("</table></div>") == 1

    def test_malformed_table_does_not_render(self):
        """python-markdown is stricter than GitHub: a delimiter row that does not
        match the header column count drops the table to raw text. This is the
        failure this module exists to surface, so pin the behaviour."""
        md = "| A | B |\n|---|---|---|\n| 1 | 2 |\n"
        assert "<table>" not in build_site.render_markdown(md)


class TestGameFacts:
    def test_matches_on_date_and_game_number(self, daily_dir, gamelog_dir):
        gamelog = build_site.load_gamelog(gamelog_dir)
        nightcap, opener = build_site.collect_reports(daily_dir)
        assert build_site.game_facts(gamelog, nightcap)["result"] == "W"
        assert build_site.game_facts(gamelog, opener)["royals_runs"] == 4

    def test_missing_row_is_not_an_error(self, daily_dir, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        report = build_site.collect_reports(daily_dir)[0]
        assert build_site.game_facts(build_site.load_gamelog(empty), report) is None


class TestBuild:
    def test_writes_a_page_per_report_plus_index(self, tmp_path, daily_dir, gamelog_dir):
        out = tmp_path / "site"
        count = build_site.build(out, daily_dir=daily_dir, gamelog_dir=gamelog_dir)
        assert count == 2
        assert (out / "index.html").exists()
        assert (out / ".nojekyll").exists()
        assert sorted(p.name for p in (out / "reports").glob("*.html")) == [
            "2026-08-07_vs-chc.html",
            "2026-08-15_at-min_gm2.html",
        ]

    def test_index_links_and_labels_each_game(self, tmp_path, daily_dir, gamelog_dir):
        out = tmp_path / "site"
        build_site.build(out, daily_dir=daily_dir, gamelog_dir=gamelog_dir)
        index = (out / "index.html").read_text()
        assert 'href="reports/2026-08-15_at-min_gm2.html"' in index
        assert '<span class="badge w">W</span>' in index
        assert "at MIN" in index

    def test_rebuild_clears_stale_pages(self, tmp_path, daily_dir, gamelog_dir):
        out = tmp_path / "site"
        build_site.build(out, daily_dir=daily_dir, gamelog_dir=gamelog_dir)
        stale = out / "reports" / "2020-01-01_vs-old.html"
        stale.write_text("stale")
        build_site.build(out, daily_dir=daily_dir, gamelog_dir=gamelog_dir)
        assert not stale.exists()

    def test_empty_reports_directory_still_builds(self, tmp_path, gamelog_dir):
        empty = tmp_path / "none"
        empty.mkdir()
        out = tmp_path / "site"
        assert build_site.build(out, daily_dir=empty, gamelog_dir=gamelog_dir) == 0
        assert (out / "index.html").exists()


class TestCommittedReports:
    """The committed reports are the site's only content, so they are part of
    what this build has to keep working."""

    def test_every_report_matches_the_filename_contract(self):
        on_disk = {p.name for p in DAILY_DIR.glob("*.md")}
        collected = {r.path.name for r in build_site.collect_reports(DAILY_DIR)}
        assert on_disk == collected

    @pytest.mark.parametrize("path", sorted(DAILY_DIR.glob("*.md")), ids=lambda p: p.stem)
    def test_linescore_table_renders(self, path):
        """Regression: every daily report carries a linescore table, and a
        delimiter row that is off by one silently drops it to raw pipes."""
        text = path.read_text()
        assert "| Team |" in text, "report has no linescore table"
        assert "<table>" in build_site.render_markdown(text)

    def test_site_builds_from_the_real_reports(self, tmp_path):
        count = build_site.build(tmp_path / "site", daily_dir=DAILY_DIR)
        assert count == len(list(DAILY_DIR.glob("*.md")))

"""Tests for baseball_lab.clean.statcast against the fixture CSV."""

import pytest

from baseball_lab.clean.statcast import statcast_highlights


@pytest.fixture
def player_names(gumbo_feed):
    return {
        p["id"]: p["fullName"] for p in gumbo_feed["gameData"]["players"].values()
    }


class TestStatcastHighlights:
    def test_hardest_hit(self, statcast_df, player_names):
        result = statcast_highlights(statcast_df, royals_home=True, player_names=player_names)
        velocities = [h["exit_velocity"] for h in result["hardest_hit"]]
        assert velocities == [111.2, 108.4, 107.1, 105.9, 103.5]
        top = result["hardest_hit"][0]
        assert top["batter"] == "Jac Caglianone"
        assert top["team"] == "KC"
        assert top["event"] == "home_run"
        assert top["distance"] == 448

    def test_most_improbable(self, statcast_df, player_names):
        result = statcast_highlights(statcast_df, royals_home=True, player_names=player_names)
        by_kind = {i["kind"]: i for i in result["most_improbable"]}
        assert by_kind["hit_below_xba"]["batter"] == "Carter Jensen"
        assert by_kind["hit_below_xba"]["xba"] == pytest.approx(0.06)
        assert by_kind["out_above_xba"]["batter"] == "Luis Robert Jr."
        assert by_kind["out_above_xba"]["xba"] == pytest.approx(0.81)
        assert len(result["most_improbable"]) == 2  # borderline candidates filtered out

    def test_royals_pitchers(self, statcast_df, player_names):
        result = statcast_highlights(statcast_df, royals_home=True, player_names=player_names)
        pitchers = {p["name"]: p for p in result["royals_pitchers"]}
        cameron = pitchers["Noah Cameron"]
        assert cameron["pitches"] == 12
        assert cameron["whiffs"] == 4
        assert cameron["csw_pct"] == pytest.approx(0.5)
        assert cameron["primary_pitch"] == "FF"
        assert cameron["max_velo"] == pytest.approx(94.8)
        assert cameron["primary_pitch_avg_velo"] == pytest.approx(93.9)
        # Appearance order preserved
        assert [p["name"] for p in result["royals_pitchers"]] == [
            "Noah Cameron",
            "Daniel Lynch IV",
            "Carlos Estevez",
        ]

    def test_royals_pitchers_resolves_ids_not_player_name(self, statcast_df, player_names):
        """Regression: live Savant exports put the batter in player_name, which
        filled royals_pitchers with the opposing lineup. Grouping must key off
        the pitcher id, so a scrambled player_name column changes nothing."""
        scrambled = statcast_df.copy()
        scrambled["player_name"] = "Wrong, Totally"
        result = statcast_highlights(scrambled, royals_home=True, player_names=player_names)
        assert [p["name"] for p in result["royals_pitchers"]] == [
            "Noah Cameron",
            "Daniel Lynch IV",
            "Carlos Estevez",
        ]

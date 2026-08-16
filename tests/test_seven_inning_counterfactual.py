"""Tests for scripts/seven_inning_counterfactual.py core logic."""

import importlib.util
import pathlib
import sys

SCRIPT = pathlib.Path(__file__).parent.parent / "scripts" / "seven_inning_counterfactual.py"
spec = importlib.util.spec_from_file_location("seven_inning_counterfactual", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules["seven_inning_counterfactual"] = mod
spec.loader.exec_module(mod)


def make_game(**overrides):
    defaults = dict(
        date="2026-04-01",
        opponent="CLE",
        home_away="H",
        result="W",
        kc_final=5,
        opp_final=4,
        kc_thru7=5,
        opp_thru7=4,
        after7="",
        extras="",
        confidence="HIGH",
        notes="",
    )
    defaults.update(overrides)
    return mod.Game(**defaults)


def test_after7_win():
    assert make_game().after7_result == "W"


def test_after7_loss_despite_actual_win():
    g = make_game(kc_thru7=2, opp_thru7=4, kc_final=5, opp_final=4)
    assert g.after7_result == "L"
    assert g.actual_win


def test_after7_tie():
    g = make_game(kc_thru7=3, opp_thru7=3)
    assert g.after7_result == "T"


def test_unknown_thru7():
    g = make_game(kc_thru7=None, opp_thru7=None)
    assert not g.has_thru7
    assert g.after7_result == "?"


def test_after7_override_used_when_scores_missing():
    g = make_game(kc_thru7=None, opp_thru7=None, after7="L")
    assert g.after7_result == "L"


def test_scores_win_over_after7_column():
    g = make_game(kc_thru7=2, opp_thru7=1, after7="L")
    assert g.after7_result == "W"


def test_parse_int():
    assert mod.parse_int("3") == 3
    assert mod.parse_int("") is None
    assert mod.parse_int("UNKNOWN") is None
    assert mod.parse_int(" 7 ") == 7


def test_sanity_check_flags_bad_rows():
    good = make_game()
    bad_result = make_game(result="L")  # says L but score is a KC win
    bad_thru7 = make_game(kc_thru7=9)  # thru-7 exceeds final
    bad_after7 = make_game(after7="L")  # says L but thru-7 scores say W
    problems = mod.sanity_check([good, bad_result, bad_thru7, bad_after7])
    assert len(problems) == 3

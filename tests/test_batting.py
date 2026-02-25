"""Tests for baseball_lab.metrics.batting."""

import pytest

from baseball_lab.metrics.batting import batting_avg, on_base_pct, ops, slugging_pct


class TestBattingAvg:
    def test_basic(self):
        assert batting_avg(3, 10) == pytest.approx(0.300)

    def test_perfect(self):
        assert batting_avg(4, 4) == pytest.approx(1.0)

    def test_zero_at_bats(self):
        assert batting_avg(0, 0) == 0.0


class TestSluggingPct:
    def test_all_singles(self):
        assert slugging_pct(10, 0, 0, 0, 40) == pytest.approx(0.250)

    def test_mixed(self):
        # 10 1B + 5 2B + 2 3B + 3 HR = 10 + 10 + 6 + 12 = 38 TB / 100 AB
        assert slugging_pct(10, 5, 2, 3, 100) == pytest.approx(0.380)

    def test_zero_at_bats(self):
        assert slugging_pct(0, 0, 0, 0, 0) == 0.0


class TestOnBasePct:
    def test_basic(self):
        # (50 + 20 + 5) / (200 + 20 + 5 + 3) = 75 / 228
        assert on_base_pct(50, 20, 5, 200, 3) == pytest.approx(75 / 228)

    def test_zero_denom(self):
        assert on_base_pct(0, 0, 0, 0, 0) == 0.0


class TestOPS:
    def test_basic(self):
        # Player: 30 1B, 10 2B, 2 3B, 8 HR in 200 AB, 25 BB, 3 HBP, 4 SF
        result = ops(30, 10, 2, 8, 25, 3, 200, 4)
        hits = 30 + 10 + 2 + 8  # 50
        expected_obp = (hits + 25 + 3) / (200 + 25 + 3 + 4)  # 78 / 232
        total_bases = 30 + 20 + 6 + 32  # 88
        expected_slg = total_bases / 200  # 0.44
        assert result == pytest.approx(expected_obp + expected_slg)

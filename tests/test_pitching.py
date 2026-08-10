"""Tests for baseball_lab.metrics.pitching."""

import pytest

from baseball_lab.metrics.pitching import (
    bb_per_9,
    era,
    fip,
    innings_from_notation,
    k_bb_ratio,
    k_per_9,
    whip,
)


class TestInningsFromNotation:
    def test_whole_innings(self):
        assert innings_from_notation(7.0) == pytest.approx(7.0)

    def test_one_out(self):
        assert innings_from_notation(6.1) == pytest.approx(6 + 1 / 3)

    def test_two_outs(self):
        assert innings_from_notation(6.2) == pytest.approx(6 + 2 / 3)

    def test_invalid_fraction(self):
        with pytest.raises(ValueError):
            innings_from_notation(6.4)


class TestEra:
    def test_basic(self):
        # 20 ER in 90 IP -> 2.00
        assert era(20, 90) == pytest.approx(2.0)

    def test_partial_innings(self):
        # 3 ER in 6.1 IP (6 1/3) -> 9 * 3 / (19/3)
        ip = innings_from_notation(6.1)
        assert era(3, ip) == pytest.approx(27 / (19 / 3))

    def test_zero_innings(self):
        assert era(5, 0) == 0.0


class TestWhip:
    def test_basic(self):
        # (30 BB + 120 H) / 150 IP -> 1.00
        assert whip(30, 120, 150) == pytest.approx(1.0)

    def test_zero_innings(self):
        assert whip(1, 1, 0) == 0.0


class TestRateStats:
    def test_k_per_9(self):
        # 200 K in 180 IP -> 10.0
        assert k_per_9(200, 180) == pytest.approx(10.0)

    def test_k_per_9_zero_innings(self):
        assert k_per_9(10, 0) == 0.0

    def test_bb_per_9(self):
        # 60 BB in 180 IP -> 3.0
        assert bb_per_9(60, 180) == pytest.approx(3.0)

    def test_bb_per_9_zero_innings(self):
        assert bb_per_9(10, 0) == 0.0

    def test_k_bb_ratio(self):
        assert k_bb_ratio(200, 50) == pytest.approx(4.0)

    def test_k_bb_ratio_zero_walks(self):
        assert k_bb_ratio(10, 0) == 0.0


class TestFip:
    def test_basic(self):
        # (13*20 + 3*(50+5) - 2*180) / 180 + 3.10 = (260 + 165 - 360) / 180 + 3.10
        expected = (13 * 20 + 3 * (50 + 5) - 2 * 180) / 180 + 3.10
        assert fip(20, 50, 5, 180, 180) == pytest.approx(expected)

    def test_custom_constant(self):
        expected = (13 * 20 + 3 * (50 + 5) - 2 * 180) / 180 + 3.20
        assert fip(20, 50, 5, 180, 180, constant=3.20) == pytest.approx(expected)

    def test_zero_innings(self):
        assert fip(1, 1, 1, 1, 0) == 0.0

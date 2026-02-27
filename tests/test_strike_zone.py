"""Tests for baseball_lab.viz.strike_zone."""

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")  # non-interactive backend for CI

from baseball_lab.viz.strike_zone import (
    pitch_scatter,
    strike_zone_grid,
    strike_zone_heatmap,
)


@pytest.fixture()
def sample_pitches() -> pd.DataFrame:
    """Synthetic Statcast-like pitch data."""
    rng = np.random.default_rng(42)
    n = 200
    return pd.DataFrame({
        "plate_x": rng.uniform(-1.5, 1.5, n),
        "plate_z": rng.uniform(0.5, 4.5, n),
        "pitch_type": rng.choice(["FF", "SL", "CH", "CU"], n),
        "stand": rng.choice(["L", "R"], n),
        "launch_speed": rng.uniform(60, 110, n),
    })


class TestPitchScatter:
    def test_returns_fig_and_axes(self, sample_pitches):
        fig, ax = pitch_scatter(sample_pitches, title="test")
        assert fig is not None
        assert ax is not None
        assert ax.get_title() == "test"

    def test_custom_palette(self, sample_pitches):
        palette = {"FF": "red", "SL": "blue", "CH": "green", "CU": "purple"}
        fig, ax = pitch_scatter(sample_pitches, palette=palette)
        assert len(ax.get_legend().get_texts()) == 4


class TestStrikeZoneHeatmap:
    def test_density_mode(self, sample_pitches):
        fig, ax = strike_zone_heatmap(sample_pitches, title="density")
        assert ax.get_title() == "density"

    def test_stat_mode(self, sample_pitches):
        fig, ax = strike_zone_heatmap(sample_pitches, stat="launch_speed")
        assert fig is not None

    def test_explicit_bounds(self, sample_pitches):
        fig, ax = strike_zone_heatmap(sample_pitches, vmin=0, vmax=50)
        assert fig is not None


class TestStrikeZoneGrid:
    def test_split_by_stand(self, sample_pitches):
        fig, axes = strike_zone_grid(sample_pitches, split_col="stand")
        assert len(axes) == 2

    def test_subset_split_vals(self, sample_pitches):
        fig, axes = strike_zone_grid(
            sample_pitches, split_col="pitch_type", split_vals=["FF", "SL"]
        )
        assert len(axes) == 2

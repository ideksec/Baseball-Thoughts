"""Strike zone visualization helpers.

Reusable functions for plotting pitch locations over the strike zone.
All functions accept Statcast-format DataFrames (plate_x, plate_z columns)
and return (fig, axes) tuples so callers can customize further.
"""

from __future__ import annotations

from typing import Sequence

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import Normalize
from matplotlib.figure import Figure

# ── Strike zone constants (in feet, from catcher's perspective) ──────────────
ZONE_LEFT = -17 / 24  # -0.708 ft  (plate is 17 inches wide)
ZONE_RIGHT = 17 / 24  # +0.708 ft
ZONE_BOT = 1.5  # approximate lower bound (varies by batter)
ZONE_TOP = 3.5  # approximate upper bound (varies by batter)


def _draw_zone(ax: plt.Axes) -> None:
    """Draw the strike zone rectangle and home plate on *ax*."""
    zone = patches.Rectangle(
        (ZONE_LEFT, ZONE_BOT),
        ZONE_RIGHT - ZONE_LEFT,
        ZONE_TOP - ZONE_BOT,
        linewidth=1.5,
        edgecolor="black",
        facecolor="none",
        zorder=3,
    )
    ax.add_patch(zone)

    # Home plate outline (pentagon, catcher's view)
    plate_vertices = np.array([
        [-17 / 24, 0.1],
        [17 / 24, 0.1],
        [17 / 24, 0.2],
        [0, 0.4],
        [-17 / 24, 0.2],
    ])
    plate = patches.Polygon(
        plate_vertices, closed=True,
        linewidth=1, edgecolor="black", facecolor="white", zorder=2,
    )
    ax.add_patch(plate)


def _configure_axes(ax: plt.Axes, title: str = "") -> None:
    """Set common axis limits, labels, and aspect ratio."""
    ax.set_xlim(-2.5, 2.5)
    ax.set_ylim(-0.5, 5.0)
    ax.set_aspect("equal")
    ax.set_xlabel("Horizontal location (ft)")
    ax.set_ylabel("Vertical location (ft)")
    if title:
        ax.set_title(title, fontsize=12, fontweight="bold")


def pitch_scatter(
    df: pd.DataFrame,
    hue_col: str = "pitch_type",
    title: str = "",
    ax: plt.Axes | None = None,
    palette: dict | str | None = None,
    alpha: float = 0.5,
    size: float = 20,
) -> tuple[Figure, plt.Axes]:
    """Scatter plot of pitch locations colored by *hue_col*.

    Parameters
    ----------
    df : DataFrame with ``plate_x`` and ``plate_z`` columns.
    hue_col : Column to color-code by (default ``"pitch_type"``).
    title : Plot title.
    ax : Optional existing Axes to draw on.
    palette : Mapping of hue values to colors, or a matplotlib colormap name.
    alpha : Marker transparency.
    size : Marker size.

    Returns
    -------
    (fig, ax) tuple.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 7))
    else:
        fig = ax.get_figure()

    groups = df.groupby(hue_col, observed=True)
    if isinstance(palette, dict):
        color_map = palette
    else:
        cmap = plt.get_cmap(palette or "tab10")
        color_map = {name: cmap(i % cmap.N) for i, name in enumerate(groups.groups.keys())}

    for name, group in groups:
        ax.scatter(
            group["plate_x"], group["plate_z"],
            label=name, color=color_map.get(name), alpha=alpha, s=size, edgecolors="none",
        )

    _draw_zone(ax)
    _configure_axes(ax, title)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.8)
    return fig, ax


def strike_zone_heatmap(
    df: pd.DataFrame,
    title: str = "",
    stat: str = "density",
    ax: plt.Axes | None = None,
    cmap: str = "YlOrRd",
    gridsize: int = 20,
    vmin: float | None = None,
    vmax: float | None = None,
) -> tuple[Figure, plt.Axes]:
    """Hexbin heatmap of pitch locations over the strike zone.

    Parameters
    ----------
    df : DataFrame with ``plate_x`` and ``plate_z`` columns.
    title : Plot title.
    stat : What the color encodes.  ``"density"`` (default) counts pitches
        per hex cell.  Any other column name in *df* computes the mean of
        that column per cell (e.g. ``"launch_speed"`` for exit velocity).
    ax : Optional existing Axes.
    cmap : Matplotlib colormap name.
    gridsize : Number of hexagons across the x-axis.
    vmin, vmax : Explicit color scale bounds.

    Returns
    -------
    (fig, ax) tuple.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 7))
    else:
        fig = ax.get_figure()

    x = df["plate_x"].values
    z = df["plate_z"].values

    if stat == "density":
        hb = ax.hexbin(
            x, z, gridsize=gridsize, cmap=cmap, mincnt=1,
            extent=(-2.5, 2.5, -0.5, 5.0),
            norm=Normalize(vmin=vmin, vmax=vmax) if vmin is not None else None,
        )
    else:
        c = df[stat].values
        hb = ax.hexbin(
            x, z, C=c, gridsize=gridsize, cmap=cmap, mincnt=1,
            reduce_C_function=np.nanmean,
            extent=(-2.5, 2.5, -0.5, 5.0),
            norm=Normalize(vmin=vmin, vmax=vmax) if vmin is not None else None,
        )

    cb = fig.colorbar(hb, ax=ax, shrink=0.7, pad=0.02)
    cb.set_label(stat.replace("_", " ").title() if stat != "density" else "Pitch count")

    _draw_zone(ax)
    _configure_axes(ax, title)
    return fig, ax


def strike_zone_grid(
    df: pd.DataFrame,
    split_col: str,
    split_vals: Sequence[str] | None = None,
    stat: str = "density",
    cmap: str = "YlOrRd",
    gridsize: int = 20,
    suptitle: str = "",
    figwidth: float = 6.0,
    vmin: float | None = None,
    vmax: float | None = None,
) -> tuple[Figure, list[plt.Axes]]:
    """Side-by-side heatmaps split by a categorical column.

    Useful for comparing pitch locations vs LHH / RHH, by pitch type, etc.

    Parameters
    ----------
    df : Statcast DataFrame.
    split_col : Column to split on (e.g. ``"stand"``).
    split_vals : Subset of values to show.  ``None`` = all unique values.
    stat : ``"density"`` or a numeric column name for mean-per-cell.
    cmap, gridsize : Passed through to :func:`strike_zone_heatmap`.
    suptitle : Figure super-title.
    figwidth : Width of *each* panel in inches.
    vmin, vmax : Shared color scale bounds across all panels.

    Returns
    -------
    (fig, axes_list) tuple.
    """
    if split_vals is None:
        split_vals = sorted(df[split_col].dropna().unique())

    n = len(split_vals)
    fig, axes = plt.subplots(1, n, figsize=(figwidth * n, figwidth * 7 / 6))
    if n == 1:
        axes = [axes]

    for ax, val in zip(axes, split_vals):
        subset = df[df[split_col] == val]
        strike_zone_heatmap(
            subset, title=f"{split_col} = {val} (n={len(subset):,})",
            stat=stat, ax=ax, cmap=cmap, gridsize=gridsize,
            vmin=vmin, vmax=vmax,
        )

    if suptitle:
        fig.suptitle(suptitle, fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    return fig, list(axes)

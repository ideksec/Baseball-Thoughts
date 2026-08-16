#!/usr/bin/env python3
"""Generate figures for the 2026 seven-inning counterfactual report.

Reads the after-7 game log CSV and writes PNGs to reports/royals/figures/.

Usage:
    python scripts/plot_seven_inning.py \
        data/processed/2026_royals_after7_gamelog.csv reports/royals/figures
"""

from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# Headless: pin the non-interactive backend before any figure is created.
matplotlib.use("Agg")

# Palette (validated reference instance, light mode)
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
BLUE = "#2a78d6"   # categorical slot 1 — the counterfactual
ORANGE = "#eb6834"  # categorical slot 2 — the actual season
RED = "#e34948"    # diverging warm pole — blown after-7 leads
GRAY_DE = "#c3c2b7"  # de-emphasis

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "axes.edgecolor": BASELINE,
    "axes.labelcolor": INK_2,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "text.color": INK,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.axisbelow": True,
    "svg.fonttype": "none",
})


def title_block(fig, ax, title, subtitle):
    """Left-aligned title with a subtitle below it, clear of the axes."""
    fig.suptitle(title, x=0.02, y=0.99, ha="left", va="top",
                 fontsize=14, fontweight="bold", color=INK)
    ax.set_title(subtitle, loc="left", fontsize=9, color=INK_2, pad=10)


def parse_int(v: str):
    v = v.strip()
    return int(v) if v and v.upper() != "UNKNOWN" else None


def load(path):
    games = []
    for row in csv.DictReader(open(path, newline="")):
        g = dict(row)
        g["kc_final"] = int(row["kc_final"])
        g["opp_final"] = int(row["opp_final"])
        g["kc_thru7"] = parse_int(row["kc_thru7"])
        g["opp_thru7"] = parse_int(row["opp_thru7"])
        y, m, d = map(int, row["date"].split("-"))
        g["dt"] = date(y, m, d)
        k7, o7 = g["kc_thru7"], g["opp_thru7"]
        if k7 is not None and o7 is not None:
            g["a7"] = "W" if k7 > o7 else ("L" if k7 < o7 else "T")
        else:
            g["a7"] = row.get("after7", "").strip().upper() or "?"
        games.append(g)
    return games


def fig_walk(games, outdir):
    """Cumulative games above .500: actual vs after-7 (T and unresolved = 0)."""
    xs = list(range(1, len(games) + 1))
    act, cf = [], []
    a = c = 0.0
    for g in games:
        a += 1 if g["kc_final"] > g["opp_final"] else -1
        c += {"W": 1, "L": -1}.get(g["a7"], 0)
        act.append(a)
        cf.append(c)

    fig, ax = plt.subplots(figsize=(9.6, 5.4), dpi=200)
    ax.axhline(0, color=BASELINE, linewidth=1, zorder=1)
    ax.plot(xs, act, color=ORANGE, linewidth=2, zorder=3)
    ax.plot(xs, cf, color=BLUE, linewidth=2, zorder=3)
    ax.annotate("Actual\n(9 innings)", (xs[-1], act[-1]), xytext=(10, -6),
                textcoords="offset points", color=ORANGE, fontsize=10,
                fontweight="bold", va="top")
    ax.annotate("If games ended\nafter 7 innings", (xs[-1], cf[-1]),
                xytext=(10, 6), textcoords="offset points", color=BLUE,
                fontsize=10, fontweight="bold", va="bottom")
    # Month ticks at each month's first game, skipping any that would collide
    seen, ticks, labels = set(), [], []
    for i, g in enumerate(games, 1):
        key = g["dt"].strftime("%b")
        if key not in seen:
            seen.add(key)
            if ticks and i - ticks[-1] < 8:
                ticks[-1], labels[-1] = i, key  # replace a cramped neighbor
            else:
                ticks.append(i)
                labels.append(key)
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels)
    ax.set_xlim(1, len(games) + 18)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Games above / below .500")
    title_block(fig, ax, "The Royals' season, with and without innings 8+",
                f"Cumulative wins minus losses, 2026 games 1–{len(games)}. "
                "Ties through 7 count as level.")
    gap = cf[-1] - act[-1]
    arrow_x = len(games) + 15
    ax.annotate("", xy=(arrow_x, cf[-1]), xytext=(arrow_x, act[-1]),
                arrowprops=dict(arrowstyle="<->", color=MUTED, linewidth=1))
    ax.annotate(f"{gap:+.0f}", (arrow_x, (cf[-1] + act[-1]) / 2), xytext=(-4, 0),
                textcoords="offset points", color=INK_2, fontsize=10,
                fontweight="bold", ha="right", va="center")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(Path(outdir) / "walk_actual_vs_after7.png", bbox_inches="tight")
    plt.close(fig)


def fig_flips(games, outdir):
    """Margin through 7 vs final margin, flips highlighted."""
    full = [g for g in games if g["kc_thru7"] is not None and g["opp_thru7"] is not None]
    fig, ax = plt.subplots(figsize=(8.4, 7.2), dpi=200)
    lim = 12
    ax.axhline(0, color=BASELINE, linewidth=1, zorder=1)
    ax.axvline(0, color=BASELINE, linewidth=1, zorder=1)
    # Quadrant shading for the flip zones
    ax.fill_between([0.0, lim], 0, -lim, color=RED, alpha=0.06, zorder=0)
    ax.fill_between([-lim, 0.0], 0, lim, color=BLUE, alpha=0.06, zorder=0)

    n_blown = sum(1 for g in full
                  if g["kc_thru7"] > g["opp_thru7"] and g["kc_final"] < g["opp_final"])
    n_comeback = sum(1 for g in full
                     if g["kc_thru7"] < g["opp_thru7"] and g["kc_final"] > g["opp_final"])
    seen_xy = {}
    for g in full:
        x = g["kc_thru7"] - g["opp_thru7"]
        y = g["kc_final"] - g["opp_final"]
        x = max(-lim, min(lim, x))
        y = max(-lim, min(lim, y))
        n = seen_xy.get((x, y), 0)
        seen_xy[(x, y)] = n + 1
        # offset duplicates slightly so every game stays visible
        dx = (n % 3) * 0.22 - 0.22 if n else 0
        dy = (n // 3) * 0.22 if n else 0
        blown = x > 0 and y < 0
        comeback = x < 0 and y > 0
        color = RED if blown else (BLUE if comeback else GRAY_DE)
        z = 4 if (blown or comeback) else 2
        size = 62 if (blown or comeback) else 38
        ax.scatter(x + dx, y + dy, s=size, color=color, edgecolors=SURFACE,
                   linewidths=1.4, zorder=z)

    ax.text(lim - 0.3, -lim + 0.4, f"Led thru 7, lost\n({n_blown} games)", color=RED,
            fontsize=10, fontweight="bold", ha="right", va="bottom")
    ax.text(-lim + 0.3, lim - 0.4, f"Trailed thru 7, won\n({n_comeback} games)",
            color=BLUE, fontsize=10, fontweight="bold", ha="left", va="top")
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_xlabel("Royals margin at the end of the 7th inning")
    ax.set_ylabel("Final margin")
    title_block(fig, ax, "Where the games flipped",
                "Each dot is a 2026 game with a verified line score. Shaded "
                "quadrants = the outcome changed after the 7th.")
    ax.grid(linewidth=0.6)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(Path(outdir) / "flip_scatter.png", bbox_inches="tight")
    plt.close(fig)


def fig_late_runs(games, outdir):
    """Run differential: innings 1-7 vs innings 8+ (games with full lines)."""
    full = [g for g in games if g["kc_thru7"] is not None and g["opp_thru7"] is not None]
    rs7 = sum(g["kc_thru7"] for g in full)
    ra7 = sum(g["opp_thru7"] for g in full)
    rs8 = sum(g["kc_final"] - g["kc_thru7"] for g in full)
    ra8 = sum(g["opp_final"] - g["opp_thru7"] for g in full)

    fig, ax = plt.subplots(figsize=(9.6, 4.6), dpi=200)
    cats = ["Innings 1–7", "Innings 8+"]
    scored = [rs7, rs8]
    allowed = [ra7, ra8]
    ypos = [1, 0]
    bar_h = 0.32
    for y, s, a in zip(ypos, scored, allowed):
        ax.barh(y + 0.18, s, height=bar_h, color=BLUE, zorder=3)
        ax.barh(y - 0.18, a, height=bar_h, color=ORANGE, zorder=3)
        ax.annotate(f"{s} scored", (s, y + 0.18), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=10,
                    color=INK_2)
        ax.annotate(f"{a} allowed", (a, y - 0.18), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=10,
                    color=INK_2)
        diff = s - a
        ax.annotate(f"net {diff:+d}", (max(scored + allowed) + 12, y),
                    ha="left", va="center", fontsize=15, fontweight="bold",
                    color=(BLUE if diff >= 0 else RED), annotation_clip=False)
    ax.set_yticks(ypos)
    ax.set_yticklabels(cats, fontsize=11, color=INK)
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, max(scored + allowed) + 46)
    ax.set_xlabel("Runs")
    net7, net8 = rs7 - ra7, rs8 - ra8
    title_block(fig, ax, "Two innings do most of the damage",
                f"Runs scored and allowed across the {len(full)} games with "
                f"verified line scores. Innings 8+ are ~2 of 9 innings but "
                f"account for {net8} of the {net7 + net8} run differential.")
    legend = [Line2D([0], [0], color=BLUE, lw=6, label="Royals scored"),
              Line2D([0], [0], color=ORANGE, lw=6, label="Opponents scored")]
    ax.legend(handles=legend, loc="lower right", frameon=False, fontsize=9,
              labelcolor=INK_2)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(Path(outdir) / "late_inning_runs.png", bbox_inches="tight")
    plt.close(fig)


def main(csv_path: str, outdir: str) -> None:
    Path(outdir).mkdir(parents=True, exist_ok=True)
    games = load(csv_path)
    fig_walk(games, outdir)
    fig_flips(games, outdir)
    fig_late_runs(games, outdir)
    print(f"Wrote 3 figures to {outdir}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"usage: {sys.argv[0]} <gamelog.csv> <output-dir>")
    main(sys.argv[1], sys.argv[2])

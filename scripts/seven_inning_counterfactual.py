#!/usr/bin/env python3
"""Compute a "games end after 7 innings" counterfactual season from a game log.

Reads a CSV game log with per-game final scores and scores through 7 innings,
and prints the actual vs. counterfactual record, flips, ties, and run
differentials.

Usage:
    python scripts/seven_inning_counterfactual.py data/processed/2026_royals_after7_gamelog.csv

Expected CSV columns:
    date, opponent, home_away, result, kc_final, opp_final,
    kc_thru7, opp_thru7, after7, extras, confidence, notes

- kc_thru7 / opp_thru7 may be blank when the exact line score is unknown.
- after7 (W/L/T) may be given directly for games where the after-7 outcome
  is certain even without exact thru-7 scores (e.g. blowouts). When both
  scores and after7 are present they must agree.
- Games with neither scores nor an after7 call are "unresolved" and are
  reported separately, excluded from the counterfactual tally.
- A tie through 7 counts as "T" (no extra innings exist in this thought
  experiment); ties are reported as-is and also split 50/50 in an adjusted
  record for comparison.
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass


@dataclass
class Game:
    date: str
    opponent: str
    home_away: str
    result: str
    kc_final: int
    opp_final: int
    kc_thru7: int | None
    opp_thru7: int | None
    after7: str
    extras: str
    confidence: str
    notes: str

    @property
    def has_thru7(self) -> bool:
        return self.kc_thru7 is not None and self.opp_thru7 is not None

    @property
    def actual_win(self) -> bool:
        return self.kc_final > self.opp_final

    @property
    def after7_result(self) -> str:
        """W/L/T from thru-7 scores when available, else the stated call, else '?'."""
        if self.has_thru7:
            if self.kc_thru7 > self.opp_thru7:
                return "W"
            if self.kc_thru7 < self.opp_thru7:
                return "L"
            return "T"
        return self.after7 if self.after7 in ("W", "L", "T") else "?"


def parse_int(value: str) -> int | None:
    value = value.strip()
    if not value or value.upper() == "UNKNOWN":
        return None
    return int(value)


def load_games(path: str) -> list[Game]:
    games = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            games.append(
                Game(
                    date=row["date"].strip(),
                    opponent=row["opponent"].strip(),
                    home_away=row["home_away"].strip(),
                    result=row["result"].strip().upper(),
                    kc_final=int(row["kc_final"]),
                    opp_final=int(row["opp_final"]),
                    kc_thru7=parse_int(row["kc_thru7"]),
                    opp_thru7=parse_int(row["opp_thru7"]),
                    after7=row.get("after7", "").strip().upper(),
                    extras=row.get("extras", "").strip(),
                    confidence=row.get("confidence", "").strip(),
                    notes=row.get("notes", "").strip(),
                )
            )
    return games


def sanity_check(games: list[Game]) -> list[str]:
    problems = []
    for g in games:
        stated_win = g.result == "W"
        if stated_win != g.actual_win:
            problems.append(f"{g.date} vs {g.opponent}: result column '{g.result}' "
                            f"disagrees with score {g.kc_final}-{g.opp_final}")
        if g.has_thru7:
            if g.kc_thru7 > g.kc_final or g.opp_thru7 > g.opp_final:
                problems.append(f"{g.date} vs {g.opponent}: thru-7 score exceeds final")
            if g.after7 in ("W", "L", "T") and g.after7 != g.after7_result:
                problems.append(f"{g.date} vs {g.opponent}: stated after7 '{g.after7}' "
                                f"disagrees with thru-7 scores "
                                f"{g.kc_thru7}-{g.opp_thru7}")
    return problems


def record_line(w: int, losses: int, t: int = 0) -> str:
    games = w + losses + t
    pct = (w + t / 2) / games if games else 0.0
    tie_part = f"-{t}" if t else ""
    return f"{w}-{losses}{tie_part} ({pct:.3f} counting ties as half)"


def main(path: str) -> None:
    games = load_games(path)
    problems = sanity_check(games)
    if problems:
        print("DATA PROBLEMS:")
        for p in problems:
            print(f"  - {p}")
        print()

    actual_w = sum(1 for g in games if g.actual_win)
    actual_l = len(games) - actual_w
    print(f"Games loaded: {len(games)}")
    print(f"Actual record: {actual_w}-{actual_l} ({actual_w / len(games):.3f})")

    resolved = [g for g in games if g.after7_result in ("W", "L", "T")]
    unresolved = [g for g in games if g.after7_result == "?"]
    c_w = sum(1 for g in resolved if g.after7_result == "W")
    c_l = sum(1 for g in resolved if g.after7_result == "L")
    c_t = sum(1 for g in resolved if g.after7_result == "T")
    print(f"\nCounterfactual (game ends after 7), over {len(resolved)} resolved games:")
    print(f"  After-7 record: {record_line(c_w, c_l, c_t)}")

    actual_w_resolved = sum(1 for g in resolved if g.actual_win)
    actual_l_resolved = len(resolved) - actual_w_resolved
    print(f"  Actual record in those same games: "
          f"{record_line(actual_w_resolved, actual_l_resolved)}")
    delta = (c_w + c_t / 2) - actual_w_resolved
    print(f"  Net change: {delta:+.1f} wins of value across {len(resolved)} games")

    complete = [g for g in resolved if g.has_thru7]
    rd_actual = sum(g.kc_final - g.opp_final for g in complete)
    rd_7 = sum(g.kc_thru7 - g.opp_thru7 for g in complete)
    print(f"\nRun differential over the {len(complete)} games with full thru-7 "
          f"line scores:")
    print(f"  Actual {rd_actual:+d}, through 7 innings {rd_7:+d}")
    rs_8plus = sum(g.kc_final - g.kc_thru7 for g in complete)
    ra_8plus = sum(g.opp_final - g.opp_thru7 for g in complete)
    print(f"  Innings 8+ only: KC scored {rs_8plus}, allowed {ra_8plus} "
          f"({rs_8plus - ra_8plus:+d})")

    print("\nGames the Royals were WINNING after 7 but lost (blown late):")
    for g in resolved:
        if g.after7_result == "W" and not g.actual_win:
            lead = f"led {g.kc_thru7}-{g.opp_thru7}" if g.has_thru7 else "led"
            print(f"  {g.date} {g.home_away} {g.opponent}: {lead} thru 7, "
                  f"lost {g.kc_final}-{g.opp_final}. {g.notes}")

    print("\nGames the Royals were LOSING after 7 but won (late comeback):")
    for g in resolved:
        if g.after7_result == "L" and g.actual_win:
            trail = f"trailed {g.kc_thru7}-{g.opp_thru7}" if g.has_thru7 else "trailed"
            print(f"  {g.date} {g.home_away} {g.opponent}: {trail} thru 7, "
                  f"won {g.kc_final}-{g.opp_final}. {g.notes}")

    print("\nGames TIED after 7 (would end as ties):")
    for g in resolved:
        if g.after7_result == "T":
            res = "won" if g.actual_win else "lost"
            print(f"  {g.date} {g.home_away} {g.opponent}: tied {g.kc_thru7}-{g.opp_thru7} "
                  f"thru 7, {res} {g.kc_final}-{g.opp_final}. {g.notes}")

    extras = [g for g in games if g.extras]
    if extras:
        ew = sum(1 for g in extras if g.actual_win)
        print(f"\nExtra-inning games: {len(extras)} (actual record {ew}-{len(extras) - ew})")

    if unresolved:
        print(f"\nGames excluded (after-7 outcome unresolved): {len(unresolved)}")
        for g in unresolved:
            res = "W" if g.actual_win else "L"
            print(f"  {g.date} {g.home_away} {g.opponent}: {res} "
                  f"{g.kc_final}-{g.opp_final}. {g.notes}")

    low_conf = [g for g in resolved
                if g.confidence.upper() not in ("HIGH", "MEDIUM-HIGH", "")]
    if low_conf:
        print(f"\nResolved games with reduced confidence: {len(low_conf)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"usage: {sys.argv[0]} <gamelog.csv>")
    main(sys.argv[1])

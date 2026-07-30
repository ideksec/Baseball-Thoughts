#!/usr/bin/env python3
"""Compute a "games end after 7 innings" counterfactual season from a game log.

Reads a CSV game log with per-game final scores and scores through 7 innings,
and prints the actual vs. counterfactual record, flips, ties, and run
differentials.

Usage:
    python scripts/seven_inning_counterfactual.py data/processed/2026_royals_after7_gamelog.csv

Expected CSV columns:
    date, opponent, home_away, result, kc_final, opp_final,
    kc_thru7, opp_thru7, extras, confidence, notes

- kc_thru7 / opp_thru7 may be blank when unknown; those games are reported
  separately and excluded from the counterfactual tally.
- A tie through 7 counts as "T" in the counterfactual record (no extra
  innings exist in this thought experiment; ties are reported as-is and
  also allocated 50/50 in an adjusted record for comparison).
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
        if not self.has_thru7:
            return "?"
        if self.kc_thru7 > self.opp_thru7:
            return "W"
        if self.kc_thru7 < self.opp_thru7:
            return "L"
        return "T"


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
    return problems


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
    print(f"Actual record: {actual_w}-{actual_l} "
          f"({actual_w / len(games):.3f})")

    known = [g for g in games if g.has_thru7]
    unknown = [g for g in games if not g.has_thru7]
    c_w = sum(1 for g in known if g.after7_result == "W")
    c_l = sum(1 for g in known if g.after7_result == "L")
    c_t = sum(1 for g in known if g.after7_result == "T")
    print(f"\nCounterfactual (game ends after 7), over {len(known)} games with data:")
    print(f"  Record: {c_w}-{c_l}-{c_t}")
    adj_w = c_w + c_t / 2
    adj_l = c_l + c_t / 2
    print(f"  Ties split 50/50: {adj_w:.1f}-{adj_l:.1f} "
          f"({adj_w / len(known):.3f})")

    actual_w_known = sum(1 for g in known if g.actual_win)
    print(f"  Actual record in those same games: "
          f"{actual_w_known}-{len(known) - actual_w_known}")

    rd_actual = sum(g.kc_final - g.opp_final for g in known)
    rd_7 = sum(g.kc_thru7 - g.opp_thru7 for g in known)
    print(f"\nRun differential (games with data): actual {rd_actual:+d}, "
          f"through 7 innings {rd_7:+d}")
    rs_8plus = sum(g.kc_final - g.kc_thru7 for g in known)
    ra_8plus = sum(g.opp_final - g.opp_thru7 for g in known)
    print(f"Innings 8+ only: KC scored {rs_8plus}, allowed {ra_8plus} "
          f"({rs_8plus - ra_8plus:+d})")

    print("\nGames the Royals were WINNING after 7 but lost (blown late):")
    for g in known:
        if g.after7_result == "W" and not g.actual_win:
            print(f"  {g.date} {g.home_away} {g.opponent}: led {g.kc_thru7}-{g.opp_thru7} "
                  f"thru 7, lost {g.kc_final}-{g.opp_final}. {g.notes}")

    print("\nGames the Royals were LOSING after 7 but won (late comeback):")
    for g in known:
        if g.after7_result == "L" and g.actual_win:
            print(f"  {g.date} {g.home_away} {g.opponent}: trailed {g.kc_thru7}-{g.opp_thru7} "
                  f"thru 7, won {g.kc_final}-{g.opp_final}. {g.notes}")

    print("\nGames TIED after 7 (would end as ties):")
    for g in known:
        if g.after7_result == "T":
            res = "won" if g.actual_win else "lost"
            print(f"  {g.date} {g.home_away} {g.opponent}: tied {g.kc_thru7}-{g.opp_thru7} "
                  f"thru 7, {res} {g.kc_final}-{g.opp_final}. {g.notes}")

    if unknown:
        print(f"\nGames excluded (no thru-7 data): {len(unknown)}")
        for g in unknown:
            res = "W" if g.actual_win else "L"
            print(f"  {g.date} {g.home_away} {g.opponent}: {res} {g.kc_final}-{g.opp_final}")

    low_conf = [g for g in known if g.confidence.upper() not in ("HIGH", "")]
    if low_conf:
        print(f"\nGames with reduced confidence in thru-7 score: {len(low_conf)}")
        for g in low_conf:
            print(f"  {g.date} {g.home_away} {g.opponent} ({g.confidence}): {g.notes}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"usage: {sys.argv[0]} <gamelog.csv>")
    main(sys.argv[1])

"""Statcast (Baseball Savant) frame -> highlight structures.

Savant's CSV identifies both batter and pitcher by MLBAM id, so callers pass
a player_names mapping (built from the GUMBO feed's gameData.players) to
label them. The player_name column is deliberately unused: live exports have
been observed labelling the batter there, not the pitcher, which silently
filled royals_pitchers with the opposing lineup. Resolve ids, not names.
"""

import pandas as pd

HIT_EVENTS = {"single", "double", "triple", "home_run"}
OUT_EVENTS = {
    "field_out",
    "force_out",
    "grounded_into_double_play",
    "double_play",
    "sac_fly",
    "fielders_choice_out",
}


def _batting_team(row: pd.Series) -> str:
    return row["away_team"] if row["inning_topbot"] == "Top" else row["home_team"]


def _batter_name(row: pd.Series, player_names: dict[int, str]) -> str:
    return player_names.get(int(row["batter"]), f"MLBAM:{int(row['batter'])}")


def statcast_highlights(
    df: pd.DataFrame,
    *,
    royals_home: bool,
    player_names: dict[int, str],
    top_n: int = 5,
) -> dict:
    """Hardest-hit balls, most improbable outcomes by xBA, Royals pitcher lines."""
    batted = df[df["launch_speed"].notna()].copy()
    batted["team"] = batted.apply(_batting_team, axis=1)
    batted["batter_name"] = batted.apply(_batter_name, axis=1, player_names=player_names)

    hardest = [
        {
            "batter": row["batter_name"],
            "team": row["team"],
            "exit_velocity": float(row["launch_speed"]),
            "launch_angle": float(row["launch_angle"]) if pd.notna(row["launch_angle"]) else None,
            "distance": int(row["hit_distance_sc"]) if pd.notna(row["hit_distance_sc"]) else None,
            "event": row["events"] if pd.notna(row["events"]) else None,
            "inning": int(row["inning"]),
            "xba": (
                float(row["estimated_ba_using_speedangle"])
                if pd.notna(row["estimated_ba_using_speedangle"])
                else None
            ),
        }
        for _, row in batted.nlargest(top_n, "launch_speed").iterrows()
    ]

    resolved = batted[batted["events"].notna() & batted["estimated_ba_using_speedangle"].notna()]
    improbable = []
    lucky_hits = resolved[resolved["events"].isin(HIT_EVENTS)].nsmallest(
        2, "estimated_ba_using_speedangle"
    )
    robbed_outs = resolved[resolved["events"].isin(OUT_EVENTS)].nlargest(
        2, "estimated_ba_using_speedangle"
    )
    for kind, threshold, subset in (
        ("hit_below_xba", 0.15, lucky_hits),
        ("out_above_xba", 0.70, robbed_outs),
    ):
        for _, row in subset.iterrows():
            xba = float(row["estimated_ba_using_speedangle"])
            if (kind == "hit_below_xba" and xba <= threshold) or (
                kind == "out_above_xba" and xba >= threshold
            ):
                improbable.append(
                    {
                        "kind": kind,
                        "batter": row["batter_name"],
                        "team": row["team"],
                        "event": row["events"],
                        "xba": xba,
                        "exit_velocity": float(row["launch_speed"]),
                        "description": row["des"] if pd.notna(row.get("des")) else None,
                    }
                )

    royals_half = "Top" if royals_home else "Bot"  # Royals pitch while the opponent bats
    royals_pitching = df[df["inning_topbot"] == royals_half]
    pitchers = []
    for pitcher_id, group in royals_pitching.groupby("pitcher", sort=False):
        name = player_names.get(int(pitcher_id), f"MLBAM:{int(pitcher_id)}")
        whiffs = group["description"].str.startswith("swinging_strike").sum()
        called = (group["description"] == "called_strike").sum()
        primary = group["pitch_type"].mode()
        primary_pitch = primary.iloc[0] if not primary.empty else None
        primary_rows = group[group["pitch_type"] == primary_pitch]
        pitchers.append(
            {
                "name": name,
                "pitches": int(len(group)),
                "whiffs": int(whiffs),
                "csw_pct": round(float(whiffs + called) / len(group), 3),
                "max_velo": (
                    float(group["release_speed"].max())
                    if group["release_speed"].notna().any()
                    else None
                ),
                "primary_pitch": primary_pitch,
                "primary_pitch_avg_velo": (
                    round(float(primary_rows["release_speed"].mean()), 1)
                    if primary_rows["release_speed"].notna().any()
                    else None
                ),
            }
        )

    return {
        "available": True,
        "hardest_hit": hardest,
        "most_improbable": improbable,
        "royals_pitchers": pitchers,
    }

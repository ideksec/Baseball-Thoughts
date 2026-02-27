"""Generate realistic synthetic Statcast data for Seth Lugo's 2024 season.

Used as a fallback when real data cannot be fetched (e.g., no network access).
Pitch profiles are based on Lugo's publicly reported 2024 arsenal:
  - Four-seam fastball (FF): ~34%, 92–95 mph
  - Sinker (SI): ~24%, 91–94 mph
  - Sweeper (ST): ~20%, 80–84 mph
  - Slider (SL): ~11%, 84–88 mph
  - Changeup (CH): ~6%, 85–88 mph
  - Curveball (CU): ~5%, 77–81 mph

Location profiles approximate real tendencies vs LHH and RHH.
This is NOT real data — use pybaseball.statcast_pitcher() for real analysis.
"""

from pathlib import Path

import numpy as np
import pandas as pd


def generate_lugo_2024(n_pitches: int = 3000, seed: int = 42) -> pd.DataFrame:
    """Return a synthetic DataFrame mimicking Lugo's 2024 Statcast output."""
    rng = np.random.default_rng(seed)

    # ── Pitch type distribution ──────────────────────────────────────────
    pitch_types = ["FF", "SI", "ST", "SL", "CH", "CU"]
    pitch_probs = [0.34, 0.24, 0.20, 0.11, 0.06, 0.05]
    types = rng.choice(pitch_types, size=n_pitches, p=pitch_probs)

    # ── Batter handedness ────────────────────────────────────────────────
    stand = rng.choice(["R", "L"], size=n_pitches, p=[0.55, 0.45])

    # ── Per-pitch-type profiles (mean, std for velo; location shifts by hand) ──
    profiles = {
        #            velo_mu, velo_sd, px_mu_R, px_mu_L, pz_mu, pz_sd, px_sd
        "FF": (93.5, 1.2, -0.15, 0.20, 2.8, 0.55, 0.40),
        "SI": (92.5, 1.1, -0.30, 0.10, 2.2, 0.50, 0.45),
        "ST": (82.0, 1.5, 0.50, -0.20, 2.0, 0.55, 0.55),
        "SL": (86.0, 1.3, 0.30, -0.10, 2.3, 0.55, 0.45),
        "CH": (86.5, 1.2, -0.10, 0.15, 1.9, 0.50, 0.40),
        "CU": (79.0, 1.4, 0.05, 0.05, 1.7, 0.65, 0.40),
    }

    release_speed = np.empty(n_pitches)
    plate_x = np.empty(n_pitches)
    plate_z = np.empty(n_pitches)

    for i in range(n_pitches):
        pt = types[i]
        velo_mu, velo_sd, px_R, px_L, pz_mu, pz_sd, px_sd = profiles[pt]

        release_speed[i] = rng.normal(velo_mu, velo_sd)
        px_center = px_R if stand[i] == "R" else px_L
        plate_x[i] = rng.normal(px_center, px_sd)
        plate_z[i] = rng.normal(pz_mu, pz_sd)

    # ── Pitch outcome (simplified) ───────────────────────────────────────
    # Whether the pitch was in the zone (approximate)
    in_zone = (
        (plate_x > -17 / 24) & (plate_x < 17 / 24)
        & (plate_z > 1.5) & (plate_z < 3.5)
    )

    # Simplified description: called_strike, swinging_strike, ball, foul, hit_into_play
    description = []
    for iz in in_zone:
        if iz:
            description.append(rng.choice(
                ["called_strike", "swinging_strike", "foul", "hit_into_play"],
                p=[0.25, 0.15, 0.35, 0.25],
            ))
        else:
            description.append(rng.choice(
                ["ball", "called_strike", "swinging_strike", "foul", "hit_into_play"],
                p=[0.55, 0.05, 0.10, 0.20, 0.10],
            ))

    # ── Batted ball data (only for hit_into_play) ────────────────────────
    desc_arr = np.array(description)
    launch_speed = np.where(
        desc_arr == "hit_into_play",
        rng.normal(88, 12, n_pitches).clip(40, 120),
        np.nan,
    )
    launch_angle = np.where(
        desc_arr == "hit_into_play",
        rng.normal(12, 18, n_pitches).clip(-60, 70),
        np.nan,
    )

    # ── Game context ─────────────────────────────────────────────────────
    game_dates = pd.date_range("2024-03-28", "2024-09-29", periods=n_pitches)

    df = pd.DataFrame({
        "game_date": game_dates,
        "pitcher": 607625,
        "player_name": "Lugo, Seth",
        "pitch_type": types,
        "release_speed": np.round(release_speed, 1),
        "plate_x": np.round(plate_x, 3),
        "plate_z": np.round(plate_z, 3),
        "stand": stand,
        "description": description,
        "zone": np.where(in_zone, rng.integers(1, 10, n_pitches), rng.integers(11, 15, n_pitches)),
        "launch_speed": np.round(launch_speed, 1),
        "launch_angle": np.round(launch_angle, 1),
    })

    return df


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "data" / "raw" / "lugo_2024_statcast.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df = generate_lugo_2024()
    df.to_parquet(out, index=False)
    print(f"Wrote {len(df):,} rows to {out}")

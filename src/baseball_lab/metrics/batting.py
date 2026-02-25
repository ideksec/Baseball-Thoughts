"""Core batting metrics.

All functions accept raw counting stats and return floats.
Division-by-zero cases return 0.0.
"""


def batting_avg(hits: int, at_bats: int) -> float:
    """Batting average: H / AB."""
    if at_bats == 0:
        return 0.0
    return hits / at_bats


def slugging_pct(
    singles: int,
    doubles: int,
    triples: int,
    home_runs: int,
    at_bats: int,
) -> float:
    """Slugging percentage: total bases / AB."""
    if at_bats == 0:
        return 0.0
    total_bases = singles + 2 * doubles + 3 * triples + 4 * home_runs
    return total_bases / at_bats


def on_base_pct(
    hits: int,
    walks: int,
    hbp: int,
    at_bats: int,
    sacrifice_flies: int,
) -> float:
    """On-base percentage: (H + BB + HBP) / (AB + BB + HBP + SF)."""
    denom = at_bats + walks + hbp + sacrifice_flies
    if denom == 0:
        return 0.0
    return (hits + walks + hbp) / denom


def ops(
    singles: int,
    doubles: int,
    triples: int,
    home_runs: int,
    walks: int,
    hbp: int,
    at_bats: int,
    sacrifice_flies: int,
) -> float:
    """OPS: on-base percentage + slugging percentage."""
    hits = singles + doubles + triples + home_runs
    return on_base_pct(hits, walks, hbp, at_bats, sacrifice_flies) + slugging_pct(
        singles, doubles, triples, home_runs, at_bats
    )

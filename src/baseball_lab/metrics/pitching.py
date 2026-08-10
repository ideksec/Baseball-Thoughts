"""Core pitching metrics.

All functions accept raw counting stats and return floats.
Division-by-zero cases return 0.0.

Innings pitched is expected as true fractional innings (e.g. 6 1/3 innings
is 6.3333...). Use `innings_from_notation` to convert the conventional
box-score notation (6.1 = 6 innings plus one out) first.
"""

# League-average FIP constant varies by season; ~3.10-3.20 in recent years.
DEFAULT_FIP_CONSTANT = 3.10


def innings_from_notation(ip: float) -> float:
    """Convert box-score innings notation to true fractional innings.

    In box scores, 6.1 means 6 innings and one out, 6.2 means 6 innings
    and two outs. Raises ValueError for a fractional part other than
    .0, .1, or .2.
    """
    whole = int(ip)
    outs = round((ip - whole) * 10)
    if outs not in (0, 1, 2):
        raise ValueError(f"Invalid innings notation: {ip} (fraction must be .0, .1, or .2)")
    return whole + outs / 3


def era(earned_runs: int, innings_pitched: float) -> float:
    """Earned run average: 9 * ER / IP."""
    if innings_pitched == 0:
        return 0.0
    return 9 * earned_runs / innings_pitched


def whip(walks: int, hits: int, innings_pitched: float) -> float:
    """Walks plus hits per inning pitched: (BB + H) / IP."""
    if innings_pitched == 0:
        return 0.0
    return (walks + hits) / innings_pitched


def k_per_9(strikeouts: int, innings_pitched: float) -> float:
    """Strikeouts per nine innings: 9 * K / IP."""
    if innings_pitched == 0:
        return 0.0
    return 9 * strikeouts / innings_pitched


def bb_per_9(walks: int, innings_pitched: float) -> float:
    """Walks per nine innings: 9 * BB / IP."""
    if innings_pitched == 0:
        return 0.0
    return 9 * walks / innings_pitched


def k_bb_ratio(strikeouts: int, walks: int) -> float:
    """Strikeout-to-walk ratio: K / BB."""
    if walks == 0:
        return 0.0
    return strikeouts / walks


def fip(
    home_runs: int,
    walks: int,
    hbp: int,
    strikeouts: int,
    innings_pitched: float,
    constant: float = DEFAULT_FIP_CONSTANT,
) -> float:
    """Fielding independent pitching: (13*HR + 3*(BB+HBP) - 2*K) / IP + constant.

    The constant is set each season so league-average FIP matches
    league-average ERA; pass the season's value for precise work.
    """
    if innings_pitched == 0:
        return 0.0
    return (13 * home_runs + 3 * (walks + hbp) - 2 * strikeouts) / innings_pitched + constant

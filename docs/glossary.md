# Metrics Glossary

Definitions for every metric implemented in `baseball_lab.metrics`, with the exact formula the code uses. All functions return `0.0` when the denominator is zero.

## Batting (`baseball_lab.metrics.batting`)

| Metric | Function | Formula | Notes |
|--------|----------|---------|-------|
| Batting average | `batting_avg` | H / AB | Hits per at-bat |
| On-base percentage | `on_base_pct` | (H + BB + HBP) / (AB + BB + HBP + SF) | How often a batter reaches base |
| Slugging percentage | `slugging_pct` | (1B + 2×2B + 3×3B + 4×HR) / AB | Total bases per at-bat |
| OPS | `ops` | OBP + SLG | Quick overall-offense summary |
| Isolated power | `iso` | SLG − AVG | Extra bases per at-bat; pure power measure |
| BABIP | `babip` | (H − HR) / (AB − K − HR + SF) | Batting average on balls in play; useful for spotting luck-driven streaks |

## Pitching (`baseball_lab.metrics.pitching`)

| Metric | Function | Formula | Notes |
|--------|----------|---------|-------|
| Earned run average | `era` | 9 × ER / IP | Earned runs per nine innings |
| WHIP | `whip` | (BB + H) / IP | Baserunners allowed per inning |
| Strikeouts per nine | `k_per_9` | 9 × K / IP | |
| Walks per nine | `bb_per_9` | 9 × BB / IP | |
| Strikeout-to-walk ratio | `k_bb_ratio` | K / BB | |
| FIP | `fip` | (13×HR + 3×(BB+HBP) − 2×K) / IP + constant | Fielding independent pitching. The constant is season-specific (defaults to 3.10); pass the season's value for precise work |

### Innings pitched notation

Box scores record partial innings in thirds: `6.1` means 6 innings plus one out, `6.2` means 6 innings plus two outs. All pitching functions expect **true fractional innings** (6.1 → 6.333…). Convert with:

```python
from baseball_lab.metrics.pitching import innings_from_notation

innings_from_notation(6.1)  # 6.333...
```

# What if every Royals game ended after 7 innings? A 2026 counterfactual

> Date: 2026-07-30
> Author: Baseball-Thoughts (compiled with Claude)

## Question

The Royals keep throwing away their leads. What would the 2026 season look like if every game simply ended after 7 innings — no 8th, no 9th, no extras?

## Hypothesis

If the "blown leads" impression is real, the Royals' after-7 record should be meaningfully better than their actual record: more standings value lost in innings 8+ than gained, driven by late bullpen failures rather than a lack of late offense.

## Data

- Source(s): Per-game recaps and partial line scores from ESPN, MLB.com, AP wire stories (via Washington Post, FOX Sports, ABC News, and regional outlets), CBS Sports, and team SB Nation sites (Royals Review, Amazin' Avenue, South Side Sox, Twinkie Town, Lone Star Ball, Redleg Nation, The Good Phight, Camden Chat, Athletics Nation), gathered via web search on 2026-07-30. Sources for pivotal games are cited inline and in the game log.
- Time window: 2026-03-27 (Opening Day) through 2026-07-30 — 110 regular-season games.
- Filters / scope: Kansas City Royals regular-season games only.
- Known limitations: The MLB Stats API and all direct page fetches were blocked by this environment's network policy (same constraint as the 2026-07-08 report), so line scores were reconstructed from recap narratives rather than pulled from a structured API. Confidence is graded per game in the data file; 4 of 110 games could not be resolved through 7 innings and are excluded from the counterfactual tally.

## Method

For each game, the score at the completion of the 7th inning was reconstructed from recap narratives (e.g., "tied it in the 8th," "walk-off in the 9th," "all the scoring came by the 5th"), cross-checked against season-record checkpoints (35-51 entering July 1; 43-62 after July 24). Each game gets an after-7 result: W, L, or T (tied through 7 — in this thought experiment, ties stand). Games where the exact through-7 line score is unknown but the after-7 leader is arithmetically certain (e.g., the 22-1 loss) are counted in the record but excluded from run-differential math.

Data: [`data/processed/2026_royals_after7_gamelog.csv`](../../data/processed/2026_royals_after7_gamelog.csv) (110 rows, per-game confidence grades and notes).
Analysis: [`scripts/seven_inning_counterfactual.py`](../../scripts/seven_inning_counterfactual.py) — rerun with `python scripts/seven_inning_counterfactual.py data/processed/2026_royals_after7_gamelog.csv`.

## Results

### The headline

| | Record | Win % |
|---|---|---|
| **Actual season (110 games)** | 46-64 | .418 |
| **Actual, over the 106 resolved games** | 45-61 | .425 |
| **If games ended after 7 (106 resolved games)** | **45-47-14** | **.491** (ties as half) |

The 7-inning Royals are a nearly .500 team. The 9-inning Royals are on a 68-win pace. Innings 8 and beyond have cost Kansas City **about 7 wins of standings value through July 30** — roughly an 11-win swing over a full season.

### It's not the offense, and it's not the starters

Over the 72 games with fully reconstructed line scores, the Royals **outscored opponents by 22 runs through 7 innings** — and finished those same games with a **−12 run differential**. From the 8th inning on they were outscored **93 to 59 (−34)**. The first seven innings of Royals baseball this season have been played by a solidly positive team; the last two have been played by one of the worst late-game teams imaginable.

### Ten blown games: led after 7, lost anyway

The Royals led at the end of the 7th in **ten games they went on to lose**. Only **three times** did they trail after 7 and come back to win (Apr 26 vs LAA, May 8 vs DET, Jul 26 at DET). A 10-to-3 imbalance:

| Date | Opp | Led thru 7 | Final | How it died |
|---|---|---|---|---|
| Mar 28 | @ ATL | 1-0 | L 2-6 | Up 2-0 with two out in the 9th; Dominic Smith walk-off grand slam capped a 6-run 9th |
| Apr 14 | @ DET | 1-0 | L 1-2 | Tigers scored twice in the 8th on a passed ball and a double |
| Apr 16 | @ DET | 8-6 | L 9-10 | Led 9-7 in the 9th; Greene 2-run double, Keith walk-off single |
| Apr 20 | vs BAL | 1-0 | L 5-7 (12) | One strike from a 1-0 win; Basallo tying single in the 9th, Taveras grand slam in the 12th |
| May 30 | @ TEX | 4-3 | L 6-7 | Up 6-4 in the 9th; five straight hits off closer Lucas Erceg, walk-off single |
| Jun 2 | @ CIN | 3-1 | L 3-4 (10) | Cameron's one-hitter through 7 wasted; Benson tying HR off Erceg in the 9th, walk-off in the 10th |
| Jun 10 | vs TEX | 4-3 | L 4-6 (10) | Walk-walk-HBP loaded the bases in the 8th, tying sac fly; bases-loaded walk lost it in the 10th |
| Jun 13 | vs HOU | 7-5 | L 7-8 | Altuve tying HR in the 8th; winning run scored on a botched double-play throw in the 9th |
| Jul 8 | @ NYM | 2-1 | L 2-6 | Five-run 8th off Lange/Cuas: bases-loaded HBP, two-run single, wild pitch |
| Jul 28 | @ MIN | 2-1 | L 2-3 | Two out in the 9th; Royce Lewis two-run walk-off triple |

Seven of the ten ended as walk-off losses. In a 7-inning world, all ten go in the win column.

### Fourteen ties — and the Royals actually win the late innings of tied games

Fourteen games were tied through 7 (13% of the season). Here the Royals broke even-plus: they won 7 of the 14 in real life (including Salvador Perez's record-breaking 318th-HR game on Jul 25 and the Jensen walk-off against San Diego on Jul 17) and lost 7 (four of them walk-offs: Rocchio, Pozo, Gonzalez, plus Basallo's 8th-inning homer). The disaster is specifically **protecting leads**, not playing from even.

### Month by month

| Month | Actual | After 7 innings | Swing |
|---|---|---|---|
| March | 2-2 | 3-1 | +1 |
| April | 10-17 | 11-13-3 | +2.5 |
| May | 10-18 | 8-15-4 | ±0 |
| June | 13-14 | 13-10-4 | +2 |
| July (thru 7/30) | 11-13 | 10-8-3 | +0.5 |

May is the honest month: the Royals were simply bad for nine innings (they even stole a couple of games late — the Isbel walk-off on May 8 was a real comeback). Every other month, the last two innings took wins off the board. April alone turned a would-be .500-ish month (11-13-3) into 10-17.

### The culprits have names

The blown games cluster around the same arms: **Lucas Erceg** (blown 9th innings May 25, May 30, Jun 2), **Matt Strahm** (decisive 8th-inning homers allowed May 12, Jun 6, Jul 10), and the **Lange/Cuas** five-run 8th on Jul 8. The Jun 10 loss featured a walk-walk-HBP meltdown; Jun 13 and the Jul 28 near-miss ended on defensive mistakes. This is a late-inning run-prevention problem across the board — the offense actually added runs late (59 scored in innings 8+), just nowhere near the 93 allowed.

## Limitations

- Line scores were reconstructed from recap narratives, not an API. 72 of 110 games have fully verified through-7 scores; 34 more have a certain after-7 winner but partially unknown exact scores; 4 games (May 2, Jul 11, Jul 12, Jul 30) are unresolved and excluded. Three of the four unresolved games were actual losses that were very probably also after-7 losses — including them would nudge the counterfactual toward 45-50-14 (.477), still ~5 wins better than actual.
- Ties are counted as half-wins, which flatters no one; MLB has no ties, so the counterfactual record is an accounting convention, not a simulation.
- The counterfactual is descriptive, not causal: in a real 7-inning league, managers would deploy bullpens completely differently, so this measures *where the 2026 Royals lost their games*, not what a 7-inning league would produce.
- 35 resolved games carry MEDIUM confidence on the exact through-7 score (the after-7 winner is certain in each); a structured API pull could tighten every number here.

## Takeaway

The impression is correct, and it's quantifiable: through July 30 the Royals are a .491 team through seven innings and a .418 team at final. They led after 7 in ten games they lost — seven by walk-off — against only three late comeback wins, and were outscored 93-59 from the 8th inning on despite a +22 run differential through 7. End every game after seven innings and this is a fringe-.500 club (45-47-14) instead of one 18 games under. The roughly 7 wins burned in the late innings trace mostly to the high-leverage bullpen (Erceg's three blown 9ths, Strahm's three decisive 8th-inning homers, the Jul 8 Lange/Cuas implosion) rather than to a lineup that goes quiet late.

## Next iteration

- Re-pull the whole season from the MLB Stats API linescore endpoint from a network-permitted environment to upgrade all MEDIUM rows to verified and resolve the 4 unknowns.
- Compare against league: is a −34 innings-8+ run differential actually extreme, or does every bad team look like this? (Compute the same counterfactual for all 30 teams.)
- Slice by reliever: innings-8+ runs allowed by pitcher, and win-probability-added lost in innings 8+, to separate the Erceg/Strahm effect from general bullpen depth.
- Revisit after the trade deadline: if the late-inning arms change, does the actual-vs-after-7 gap close?

## Sources

Pivotal-game sources (full per-game citations in the CSV notes and the four research passes behind it):

- [ESPN: Braves 6-2 Royals, Mar 28 — walk-off grand slam](https://www.espn.com/mlb/recap/_/gameId/401814710) · [AJC](https://www.ajc.com/sports/2026/03/dominic-smith-hits-walk-off-grand-slam-as-braves-beat-royals-6-2/)
- [ESPN: Tigers 2-1 Royals, Apr 14](https://www.espn.com/mlb/recap/_/gameId/401814934) · [ESPN: Tigers 10-9 Royals, Apr 16](https://www.espn.com/mlb/recap?gameId=401814963)
- [ESPN: Orioles 7-5 Royals (12), Apr 20](https://www.espn.com/mlb/recap?gameId=401815021)
- [MLB.com: Rangers walk off Royals, May 30](https://www.mlb.com/news/carter-jensen-royals-rally-before-walk-off-loss-to-rangers)
- [Redleg Nation: Benson ties it in 9th, Dunn wins it in 10th, Jun 2](https://www.redlegnation.com/2026/06/02/will-benson-ties-it-in-9th-blake-dunn-wins-it-in-10th/)
- [NBC DFW: Rangers 6-4 in 10, Jun 10](https://www.nbcdfw.com/mlb/diaz-and-burger-lead-the-rangers-to-a-6-4-win-over-the-royals-in-10-innings/4035150/) · [MLB.com: Astros' three unanswered, Jun 13](https://www.mlb.com/video/astros-score-three-unanswered-runs-to-defeat-royals)
- [Amazin' Avenue: Five-run eighth propels Mets, Jul 8](https://www.amazinavenue.com/new-york-mets-scores/97401/mets-recap-final-scores-five-run-eighth-propels-victory-over-royals-kansas-city-new-york-baseball-mlb)
- [Baltimore Banner: Basallo's 8th-inning homer, Jul 10](https://www.thebanner.com/sports/orioles-mlb/orioles-royals-samuel-basallo-winning-home-run-RENZGVWL2JCGFBJB2BPRYPP7XU/)
- [CBS Minnesota/AP: Lewis walk-off triple, Jul 28](https://www.cbsnews.com/minnesota/news/twins-vs-royals-game-july-28-2026/)
- [Times Gazette/AP: Perez's record 318th HR, Jul 25](https://www.timesgazette.com/2026/07/25/nick-loftin-and-salvador-perez-hit-late-inning-home-runs-as-royals-rally-to-beat-tigers-3-2/)
- [NBC Sports/AP: Jensen caps 4-run 10th, Jul 17](https://www.nbcsports.com/mlb/news/carter-jensens-2-run-single-caps-4-run-10th-inning-as-royals-rally-for-7-6-win-over-padres)

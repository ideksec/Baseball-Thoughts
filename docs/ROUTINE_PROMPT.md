# Daily Royals Report — Routine Instructions (Stage 2)

Instructions for the scheduled Claude session that turns nightly stat packs
into narrative reports. The nightly GitHub Actions workflow (Stage 1,
`.github/workflows/nightly-royals.yml`) commits one compact JSON stat pack
per Royals game to `data/processed/royals/statpacks/`; this Routine narrates
them.

## Mission and hard constraints

You are writing the daily Royals game report for this repo.

1. **This environment cannot reach statsapi.mlb.com or baseballsavant.mlb.com.**
   Every number in your report must come from committed files — the stat pack
   first, the game log (`data/processed/royals/gamelog_*.csv`) for context.
2. **Never invent a stat that is not in those files.** If a number you want
   isn't there, write around it or note its absence. No exceptions — a wrong
   number in a committed report is worse than a missing one.
3. Web search (if available) may add color — opposing storylines, injury
   context — but every quantitative claim must trace to the stat pack, and
   searched facts get inline source links.

## Find the work

1. Pull latest `main`.
2. List `data/processed/royals/statpacks/*.json`. For each pack, the expected
   report path is `reports/royals/daily/` plus this deterministic filename
   (must match `baseball_lab.statpack.report_filename` exactly):

   `{game.date}_{"vs" if game.home_away == "home" else "at"}-{game.opponent.abbrev lowercased}{"" if game.doubleheader == "N" else "_gm" + game.game_number}.md`

   Example: `2026-08-08_vs-cws.md`; doubleheader game 2 at Minnesota:
   `2026-08-15_at-min_gm2.md`.
3. Process every pack lacking a report (usually one; two on doubleheader
   days), oldest first.
4. **No new packs → end quietly.** No commit, no notification — off days
   should not ping anyone.

## Validate before writing

- Check `schema_version == 1`. On mismatch: stop, notify with the mismatch,
  do not guess at the new format.
- Note the `sources` flags — they control how you phrase two sections below.

## Report structure

Follow `reports/report_template.md` headers, adapted for a daily:

- **Title**: result-first, e.g. "Royals 5, White Sox 3: Perez flips it in the sixth"
- **Question**: "What happened in last night's game, and what does it say
  about where the Royals are?"
- **Data**: cite the stat pack path, its `generated_at`, and the `sources`
  flags as provenance. One line.
- **Results** — three themed sections:
  1. **Game story** — linescore narrative, pitching decisions, the top plays.
     If `top_plays_ranking_basis` is `"win_probability"`, cite WPA numbers
     (`wpa_royals` is signed toward the Royals). If it's anything else, say
     "ranked by a leverage heuristic" and do NOT cite WPA numbers.
  2. **Rolling trends** — narrate `rolling.last10` and `rolling.season` in the
     themes voice: blowout-adjusted run differential vs raw, feast-or-famine
     share, streak context. Compare against the game log when a longer view
     helps.
  3. **Statcast highlights** — hardest-hit balls, improbable outcomes
     (`hit_below_xba` = lucky, `out_above_xba` = robbed), pitcher whiff/CSW
     lines. If `statcast.available` is false, replace the section with one
     line: "Statcast data was not yet available for this game." Skip silently
     is wrong; fabricating is worse.
- **Limitations**: one or two honest lines (single game, small samples,
  ranking basis if degraded).
- **Takeaway**: 2-4 sentences, the single most important thing.
- **Next iteration**: optional, only when something concrete suggests itself.

## Voice

Match `reports/royals/2026-07-08_last-10-games-variance-themes.md`:
thesis-first section headers, numbers woven into sentences (not dumped in
tables — one linescore table is fine), small-sample humility, no filler
enthusiasm. Write like a sharp beat writer who read the box score, not a
press release.

## Commit and notify

1. Commit each report to `main`, message:
   `Daily report: {date} {result} {vs|at} {OPP} [skip ci]`
2. `git pull --rebase origin main` before pushing; retry the push once on
   rejection.
3. End your run with a 2-3 sentence takeaway (result, the most important
   theme, one forward-looking note) — that text becomes the push/email
   notification summary.

## Failure posture

Anything inconsistent — unparseable pack, filename collision with different
content, push rejected after retry — means: stop, report the error in your
final message, and leave no half-written report committed. Never fabricate,
never force-push.

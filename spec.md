# spec.md — Baseball Analytics Lab Repo (Framework Only)

## Purpose
A private, long-lived "lab" repo for learning baseball + Python through:
- analysis (notebooks + write-ups)
- reusable Python modules
- scripts / CLIs
- small apps (dashboards / APIs)
- experiments and prototypes

This repo is intentionally framework-first: concrete artifacts are added incrementally.

Non-goals:
- perfect engineering from day one
- committing large datasets to git
- scraping that violates terms of service
- storing secrets or tokens in the repo

---

## Operating principles
1. One question → one primary artifact (notebook, report, or app).
2. Reproducible by default: results must be recreatable from code + documented data steps.
3. Separation of concerns: data, code, analysis, and outputs are clearly separated.
4. Private-first posture: everything should be clean enough to publish later if desired.
5. Messy is allowed, but contained: experiments live in scratch and are promoted or removed.

---

## Canonical repository structure (framework only)

```
baseball-lab/
├── README.md
├── spec.md
├── docs/                  # durable notes: glossary, methodology, sources, conventions
├── data/
│   ├── raw/               # local-only pulls; gitignored
│   ├── interim/           # optional staging; gitignored
│   └── processed/         # small reproducible derivatives only
├── notebooks/
│   ├── templates/
│   ├── exploration/
│   ├── analysis/
│   ├── modeling/
│   └── viz/
├── reports/
│   ├── royals/
│   ├── league/
│   └── publishable/
├── src/
│   └── baseball_lab/      # python package root
│       ├── io/
│       ├── clean/
│       ├── metrics/
│       ├── models/
│       ├── viz/
│       └── utils/
├── scripts/               # small executable utilities
├── apps/
│   ├── dashboards/
│   └── services/
├── tests/
└── scratch/
    └── _archive/
```

Notes:
- Keep the repo root quiet; most churn should be below it.
- `docs` contains stable knowledge you intend to reuse.
- `scratch` is explicitly temporary.

---

## Notebook standards
Each notebook should include, at minimum:
- **Header:** question, datasets used, time window, assumptions
- **Method:** what was done (not every attempt)
- **Results:** minimal charts or tables that answer the question
- **Conclusion:** 5–10 sentences, limitations, next step

Naming:
- Include a date prefix and a short question identifier.
- Avoid ambiguous names like `final.ipynb`.
- Version explicitly if needed.

Rule:
- If logic becomes reusable, extract it into `src` and keep notebooks narrative.

---

## Reports standards
Reports are the durable "answers" worth keeping.

Recommended structure:
- Question
- Hypothesis
- Data
- Method
- Results
- Limitations
- Takeaway
- Next iteration

Reports should be concise and defensible.

---

## Data policy
- Never commit large raw datasets.
- Treat `raw` and `interim` data as local cache only.
- Processed data may be committed only if:
  - it is small and reproducible
  - it does not violate licensing or ToS
  - it will not bloat repository history

All data sources should be documented in `docs`:
- origin
- access method
- refresh cadence
- licensing / ToS considerations
- what is local-only vs committed

---

## Quality and hygiene
Even as a learning repo:
- Use consistent formatting and linting
- Add basic tests for core metrics and transforms
- Prefer deterministic runs where possible
- Avoid silent failures

Security hygiene:
- Never commit secrets
- Use environment variables locally
- Keep example env files to variable names only
- Assume history may be made public later

---

## Claude-first workflow
Claude accelerates implementation; you own correctness and judgment.

Every request to Claude should specify:
- goal
- repo area / folder
- inputs and outputs
- constraints (no secrets, no large data, etc.)
- acceptance criteria

Review every output for:
- secret leakage
- uncontrolled network calls
- licensing or scraping risk
- silent exceptions
- modeling leakage
- unlabeled plots
- unnecessary dependencies

---

## Promotion rules
`scratch` is temporary by design.

Every item must be:
- promoted into `notebooks` / `reports` / `src`
- archived
- or deleted

Timebox resolution to avoid entropy.

---

## Project units
Each unit of work should have:
- one primary artifact (notebook, report, or app)
- supporting reusable code
- optional scripts
- a short written summary if worth keeping

This keeps learning structured rather than fragmented.

---

## Public-ready posture (future)
Assume eventual publication:
- write clearly and defensibly
- avoid personal notes in the repo
- keep data handling explicit

If publishing later:
- add a license
- scrub history for secrets or large files
- document setup and reproducibility

---

## Acceptance criteria
This framework is in place when:
- the folder structure exists
- data cache directories are gitignored
- at least one analysis artifact follows these standards
- at least one reusable function has been extracted into `src`

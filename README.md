# P22 — synthetic-only multimodal routing workspace

Faithfulness-tested two-view routing for identifying and validating regulatory
mechanisms. **Condition-specific data work is blocked** until Professor Fang
approves a dataset, target, and protocol.

Current data mode: `synthetic` (plus read-only legacy Tasic evidence).

## What this repository is

Reusable package code under `src/p22`, synthetic fixtures, donor-held-out
splits, train-only transforms, six baselines, five-seed reporting, routing
interventions, and a local verification command. Meeting-linked notebooks live
under `notebooks/implementation/`; the larger scale gate lives under
`notebooks/scale/`.

## What this repository is not

- Not approved real-data training
- Not a claim that Tasic proxy-view results are independent two-modality evidence
- Not a claim that routing weights explain biology
- Not translational or eligibility evidence

## Local setup

```bash
cd /Users/anuragdani/Github/niw-eb1a/P22
uv sync --python /opt/homebrew/bin/python3.11 --extra dev
source .venv-p22/bin/activate
```

Python 3.11 is required. CPU is the supported default.

## Commands

| Command | Purpose |
|---|---|
| `make plan-status` | Plan steps, approval state, next action |
| `make verify-fast` | Lint + fast tests + plan status |
| `make verify` | Fast checks, all tests, notebooks, repository verifier |
| `make notebook-check` | Execute synthetic notebooks into ignored outputs |
| `make scale-check` | Execute larger synthetic full-pipeline and stress notebook |
| `make live-check` | Execute one all-in-one live local synthetic notebook |
| `make live` | Open the all-in-one notebook in local JupyterLab |
| `python scripts/verify_repository.py` | PASS / INCONCLUSIVE / BLOCKED report |
| `python scripts/verify_repository.py --execute-notebooks` | Notebook execution with a 300s kernel startup budget |
| `python scripts/run_toy_pilot.py` | Five-seed synthetic benchmark from `configs/toy_pilot.json` |

Generated files go under `reports/generated/` (gitignored). Source notebooks are
never overwritten by verification.

The larger scale result is recorded in `docs/scale_benchmark.md`. The one-notebook
live walkthrough is `notebooks/live/P22_live_local.ipynb`. Both measure local
engineering capacity only; neither replaces real-cohort preflight.

Open live notebook locally with:

```bash
make live
```

## Donor-first evaluation order

1. Split by donor, never by cell when donor IDs exist
2. Fit transforms on training cells only
3. Select on validation only
4. Read the test split once
5. Report five seeds with across-seed spread
6. Run held-out interventions before calling a routing weight dependence evidence

## Evidence labels

Use exactly these labels in reports and docs: `verified`, `experimental result`,
`proposed`, `inference`, `unknown`.

## Approval blocker

Next decision owner: **Professor Fang**.
Next action: `awaiting_professor_approval`.
See `HANDOFF.md` and `docs/interim_methods_protocol.md`.

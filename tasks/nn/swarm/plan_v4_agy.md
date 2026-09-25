# Implementation Plan v4: audit, verified rerun, results and paper (Gemini via agy)

2026-09-25. Driver `gnhf/agy_swarm.py` with `AGY_CONFIG=tasks/nn/swarm/agy_lanes_v4.json`.
Science, assumptions A1–A16, frozen protocol (N9) and decision tree are unchanged.

## Why v4

The v3 run completed every stage, but its evidence is not trustworthy:

| Finding | Evidence |
|---|---|
| Ladder pipeline bug | Model-free donor chr21 share: AUROC **1.0** (DS/CON 1.58). Ladder `chr21_dosage` arm: AUROC **0.345**; most arms below chance |
| Wrong model sizes | Fold R3_ca 98,874 parameters vs frozen 384,250 (all neural arms ≈ 4× smaller); no amendment |
| Summary CI bug | `ladder_summary.json` CI [0, 0]; independent donor bootstrap ≈ [−0.083, +0.085] |
| Evidence overwritten | Later lanes rewrote the ladder docs with 4-fold runs |
| Weak gates | S4/S5 passed on stale files (the old results doc and draft) |
| Wasted calls | Gemini tried shell commands; headless agy auto-denied them ("no output produced") |

Everything derived from the first ladder is archived in `docs/nn_v2/superseded_buggy_ladder/`
and `paper/superseded_buggy_ladder/`. N10 and downstream tasks are TODO again.

## Driver changes (done, tested)

- `gnhf/verify_ladder.py` (driver-owned): recomputes every arm and the primary contrast from raw
  fold files, compares with the summary, checks 5×30 donor coverage, frozen parameter counts
  (or a named width amendment), and chr21 AUROC ≥ 0.85 against `gnhf/chr21_sanity.py` ground truth.
- `gnhf/check_evidence.py --in`: the verified CI numbers (3 dp) must appear in the results doc
  and the draft, so stale documents cannot pass.
- Stale evidence archived, so existence checks fail until regenerated.
- Gemini may run read-only commands and `python -m pytest` (smoke-tested); other commands are
  denied, detected, and reported back as a wasted call.
- Run outputs that land outside a lane's owned files are discarded after every run.
- Gate evidence is committed in the main checkout, so later stages can read it.

## Stages, goals, tasks, verification

### S6 — Ladder audit and verified rerun (HARD gate; critical A1–A5)
| Task | Goal | Driver check |
|---|---|---|
| A1 | Fix the label/row/probability misalignment (failing test first) | `pytest tests/test_nn_audit_alignment.py` |
| A2 | Build every arm with frozen widths | `pytest tests/test_nn_conformance.py` |
| A3 | Correct summary CI (repeated_primary_contrast semantics) | `pytest tests/test_nn_summary.py` |
| A4 | AUROC/log-loss/Brier, pooled-BA artefact, `AUDIT.md` | `AUDIT.md` has "Root cause" |
| A5 | Full rerun → `ladder_v2`, summary, LADDER.md | `verify_ladder.py --run ladder_v2 --write` exit 0 |
Gate: `verify_ladder.py --run reports/generated/nn_20260923/ladder_v2 --write`. Roll-up: N10 = DONE.
IF the gate fails 3 rounds → driver stops (exit 6); nothing downstream runs on bad evidence.

### S7 — Robustness, faithfulness, export, gene-aligned on ladder_v2 (soft gate, parallel)
robust N11 N12 · faith N13 N14 · export N15 · geneact N21 (optional; BLOCKED allowed).
Checks: each evidence JSON regenerated (archived copies no longer satisfy them).

### S8 — Interpretation and results (HARD gate; critical N22 N23)
N16 spectrum, N17 attention readout, N22 results doc + unsent professor note, N23 full `pytest -q`.
Gate: verified primary CI numbers appear in `NN_V2_RESULTS_2026-09-23.md`.

### S9 — Draft paper on verified results (HARD gate)
N24 framing by rule, N25 figures, N27 Results + claims ledger, N29 Discussion/Limitations,
N30 Abstract/title, N31 checker, N32 self-review, N33 vault copy (driver), N34 final.
Gate: `paper/check_paper.py` passes, draft label present, verified CI numbers appear in `paper/draft.md`.

## Decision rules (IF/ELSE) the driver enforces

- IF a DONE task's check fails → status back to TODO with the failure text in the next prompt.
- IF a critical task is marked BLOCKED/NOT_NEEDED → refused, back to TODO.
- IF a lane is idle 8 calls or hits its call cap → non-critical tasks BLOCKED; critical tasks stay open;
  the hard gate reruns the stage (up to 3 rounds), then exit 6.
- IF Gemini quota/rate limit → switch to Gemini 3.8 Flash; after both, wait 15 min; repeat forever.
- IF a merge conflicts → bounded agy repair of conflict markers; still conflicted → exit 5.
- IF post-merge tests fail → bounded agy repair limited to that stage's changed files.
- IF the verified primary contrast is null → valid result; framing by the N24 rule table.

## Risks

| Risk | Mitigation |
|---|---|
| Root cause not found by Gemini | Failing alignment test + chr21 ground truth give a precise target; exit 6 with logs, no bad evidence written |
| Rerun takes hours | Background run; driver waits; `--resume` only inside ladder_v2 |
| Signal is chr21 dosage only | N11 chr21-excluded result decides the paper framing; reported plainly |
| Antigravity quota | model fallback and indefinite 15-min waits |

## Monitor
`tail -f reports/generated/nn_agy/latest/swarm.log` · `grep -H . tasks/nn/status/*` ·
`python3 gnhf/verify_ladder.py --run reports/generated/nn_20260923/ladder_v2`

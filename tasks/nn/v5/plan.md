# P22-NN v5 — validity of the null, then complete professor guidance (GNHF prompt, Cursor auto)

2026-09-28. This file is the GNHF prompt. Branch `codex/p22-nn-finish-base`, worktree
`/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-base`. Execute code; a plan or summary
alone is not progress. **Completion = `python3 gnhf/v5_gate.py` prints `V5_GATE PASS`.**

## 0. State at handoff (verified by Claude, 2026-09-28)

- Canonical run `reports/generated/nn_20260923/ladder_v2` passes `gnhf/verify_ladder.py`:
  primary R3_ca − R3_tc donor BA = −0.0067, 95% CI [−0.053, +0.035] → `B_NULL`.
- chr21_dosage arm AUROC 0.998 (model-free ground truth 1.0, `docs/nn_v2/chr21_sanity.json`).
- **Open validity question (the reason for v5):** pooled donor AUROC of the learned arms is
  BELOW chance — R3_ca 0.369, R3_tc 0.346, logreg_rna 0.409, majority BA 0.353 — while one chr21
  feature reaches 0.998. Either (a) pooling fold-specific scores across stratified folds creates
  an artefact, or (b) the ≥2,000-feature pipeline is still mis-specified (for example chr21
  genes dropped by HVG selection, inverted orientation, scaler/IDF leakage, aggregation bug).
  The paper currently states the numbers without explaining them. No claim may go to the
  professor until this is resolved.
- Paper `paper/draft.md` is `DRAFT_V1_COMPLETE` (F4 framing), check_paper 5/5, 1,192 tests pass.

## 1. Rules (binding)

1. Science, assumptions A1–A16, the frozen protocol and honesty rules in `tasks/nn/plan.md`
   §0–§4 and §7 still apply. Null results are valid; never tune toward a win.
2. Never edit anything under `gnhf/`, `configs/nn_protocol_v2_2026-09-23.json`,
   `docs/nn_v2/chr21_sanity.json`, `docs/nn_v2/ladder_verification.json`, or any
   `docs/nn_v2/superseded_buggy_ladder/` file. Never delete a ladder run directory.
3. Status: one line in `tasks/nn/status/<ID>` (TODO / DONE:<evidence> / BLOCKED:<reason>:<evidence>
   / NOT_NEEDED:<evidence>). Log one line per iteration in `tasks/nn/lanes/v5.md`.
4. Python: `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python` with
   `PYTHONPATH=src:scripts PYTHONDONTWRITEBYTECODE=1`. At most 14 worker processes, 1 torch thread each.
5. Runs longer than 10 minutes: start with `nohup … > <log> 2>&1 &`, record the PID in the
   status line as `RUNNING:<pid>:<log>`, end the iteration, and check the log next iteration.
   Never start a duplicate (`pgrep -fl run_nn_v2`).
6. One coherent step per iteration; run the task's check before marking DONE; GNHF commits.
7. New code gets a focused test under `tests/test_nn_v5_*.py`. Keep files ≤ 300 lines.
8. Cite only `paper/refs_frozen.bib`. Every number in prose must come from a JSON under `docs/nn_v2/`.
9. No new packages, no network, no pushes, no merges, no messages to anyone.

## 2. Tasks (in order; IF/ELSE branches are mandatory)

### V1 — Per-fold metrics (no pooling)
Write `scripts/nn_v5_per_fold_metrics.py` + `tests/test_nn_v5_per_fold.py`. From every fold file in
the canonical run compute per fold: donor AUROC, donor BA at 0.5, log-loss, n donors per class;
per arm: mean and SD over the 25 folds, and the pooled values for comparison. Write
`docs/nn_v2/v5/per_fold_metrics.json` (`per_arm.<arm>.per_fold_auroc_mean`, `..._sd`,
`pooled_auroc`, `per_fold`) and `docs/nn_v2/v5/CANONICAL_LADDER.txt` containing exactly
`reports/generated/nn_20260923/ladder_v2`.
**Check:** the test passes; the JSON has 18 arms; majority per-fold BA is exactly 0.5 in every fold
(a constant predictor) — if not, the metric code is wrong: fix it first.

### V2 — Positive control through the full pipeline
Write `scripts/nn_v5_positive_control.py` (+ test). Run the SAME fold preparation, training loop and
donor aggregation as the ladder (import them; do not re-implement) for one logistic arm and one
R3_tc arm, with the feature set forced to include every chr21 gene (union with the HVGs), on
repeat 0 (5 folds). Write `docs/nn_v2/v5/positive_control.json` with `donor_auroc` (pooled over the
5 folds), `per_fold_auroc`, `chr21_genes_in_hvg_default` (how many chr21 genes the default HVG
selection kept), `orientation_check` (Spearman of predicted DS probability vs donor chr21 share
from `docs/nn_v2/chr21_sanity.json`).
- IF `donor_auroc` ≥ 0.9 → the pipeline can learn the known signal; go to V3.
- ELSE → pipeline bug. Write a failing test reproducing it, find the root cause in the shared path
  (label/probability orientation, row alignment, scaler/IDF fit, aggregation), fix it, rerun V2.
  Do not continue past V2 until `donor_auroc` ≥ 0.9 or 6 iterations are spent; then set V2
  BLOCKED with the evidence and continue with V3 marked "UNRESOLVED".

### V3 — Diagnose the below-chance learned arms
Using V1 and V2, write `docs/nn_v2/v5/below_chance_diagnosis.json` with `verdict` ∈
{`POOLING_ARTEFACT`, `PIPELINE_BUG_FIXED`, `REAL_ANTI_SIGNAL_EXPLAINED`} and the evidence, plus
`docs/nn_v2/v5/BELOW_CHANCE.md` (≤ 60 lines).
- IF per-fold mean AUROC of the learned arms is ≈ 0.5 (|x − 0.5| ≤ 0.1) while pooled < 0.45, and V2
  passed without code changes → `POOLING_ARTEFACT`; the primary BA contrast stands; report
  per-fold AUROC alongside pooled metrics everywhere.
- ELSE IF V2 required a fix in the shared path → `PIPELINE_BUG_FIXED`; go to V4.
- ELSE (per-fold AUROC also clearly < 0.5 and V2 passes) → investigate donor-level confounding
  (age `dev_PCW`, batch, sex vs label within folds) and document the mechanism →
  `REAL_ANTI_SIGNAL_EXPLAINED`. Never flip predictions to make them look better.

### V4 — Rerun if the pipeline changed
- IF V3 verdict is `PIPELINE_BUG_FIXED` → rerun the full ladder into
  `reports/generated/nn_20260923/ladder_v3` (background, `--resume` only inside v3), regenerate the
  summary, write `ladder_v3` into `CANONICAL_LADDER.txt`, and run
  `python3 gnhf/verify_ladder.py --run reports/generated/nn_20260923/ladder_v3 --write` until it
  passes. Then rerun V1 on v3.
- ELSE → `NOT_NEEDED:<verdict>`.
**Check:** `python3 gnhf/verify_ladder.py --run $(cat docs/nn_v2/v5/CANONICAL_LADDER.txt)` exits 0.

### P1 — Downstream consistency
IF the canonical ladder changed in V4 → rerun N11 (chr21-excluded), N12 (seeds), N13/N14
(faithfulness, nuisance probe), N15/N16 (export, spectrum) and N17 on the new run, each into a new
`_v3` output path, and update their docs JSON. ELSE → `NOT_NEEDED:canonical unchanged` after
confirming each JSON names the canonical run.

### P2 — Professor direction D3: finer tokens, with the right controls
The gene-activity rerun (N21) was `GA_B_NULL`. Add one planted-signal regime to
`scripts/run_nn_planted_benchmark.py` where the signal is a gene-level RNA×ATAC interaction on
matched genes (the case gene-aligned cross-attention is designed for), and run gene-aligned CA vs
matched token-concat vs MLP on it (δ = 0.5, 1.0; 5 folds). Record whether any regime now
favours cross-attention (`CA_FAVOURED` label rule from decision tree N4) in
`docs/nn_v2/v5/planted_gene_aligned.json`. A null is acceptable.

### P3 — Professor direction D2: dosage-aware cell-state spectrum
Because the result is `DOSAGE_DOMINATED`, repeat the N16 spectrum analysis on per-cell scores from
the chr21-EXCLUDED models (N11 outputs), per author cell type, donor unit, Holm across eligible
types. Write `docs/nn_v2/v5/spectrum_chr21_excluded.json` and a ≤ 40-line reading. Label
`SPECTRUM_LOCALIZED:<types>` or `SPECTRUM_NULL`; no mechanism language.

### P4 — Results document
Add a "Per-fold metrics and validity" section to `docs/nn_v2/NN_V2_RESULTS_2026-09-23.md` (V1–V4
verdicts, positive control, below-chance explanation) and sections for P2 and P3. Update
`docs/nn_v2/PROFESSOR_NOTE_UNSENT.md` accordingly.

### P5 — Professor update with full coverage table
Write `docs/nn_v2/v5/PROFESSOR_UPDATE_v5.md` (≤ 600 words + table): plain-language result first;
then a table with one row for EACH direction D1–D13 from `tasks/nn/plan.md` §1: status
(DONE/PARTIAL/NOT DONE), evidence file, one-line finding. Unsent. No immigration language.

### P6 — Paper revision
Update `paper/draft.md`: add per-fold AUROC (phrase "per-fold AUROC" must appear) and the
positive control to Methods/Results, the below-chance explanation to Results/Limitations, P2 and
P3 findings, revised Abstract; update `paper/claims.csv`, figures via `paper/make_figures.py`
(add a per-fold AUROC figure), `paper/self_review.md`. Keep `DRAFT_V1_COMPLETE` → change to
`DRAFT_V2_COMPLETE` header label. Run `paper/check_paper.py` until it passes. Copy the updated
draft, figures, claims and self-review to
`/Users/anuragdani/Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/paper-nn/`
(overwrite those files only).

## 3. Final verification (every iteration once P6 is DONE)

Run `python3 gnhf/v5_gate.py`. IF it prints `V5_GATE PASS` → stop (`should_fully_stop=true`).
ELSE fix the first FAIL line (never by editing gnhf/ or the verifier inputs) and continue.
If a FAIL cannot be fixed after 3 iterations, set the owning task BLOCKED with evidence; the gate
accepts BLOCKED tasks, but the science checks (verify_ladder, positive control, paper checker)
must still pass for completion.

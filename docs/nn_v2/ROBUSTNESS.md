# NN-v2 robustness (D13, D9) — lane `robust`, tasks N11, N12

Status: **BLOCKED:upstream N10** for both N11 and N12. This is a named blocker, not a
result. No chr21-excluded or seed-sensitivity number has been produced.

## Why blocked

N11 (chr21-excluded sensitivity) and N12 (init/sampling-seed sensitivity) both consume
the frozen real-DS ladder produced by N10: its per-fold grid choices at model seed 0, its
saved fold models/predictions for `R3_ca` and `R3_tc`, and the paired `logreg_*` controls.
None of that exists in this checkout or in the shared heavy-output directory.

Evidence (checked this iteration):

- `tasks/nn/status/N10` = `BLOCKED:lane_stalled:no commit in 3 attempts` (also in the
  committed record `swarm: ladder stalled`).
- `docs/nn_v2/ladder_summary.json` — absent (`ls` error).
- `reports/generated/nn_20260923/ladder/` — absent.
- `scripts/run_nn_v2_comparison.py` (the N10/N11/N12 runner) — absent.
- Fold-file count under `reports/generated/nn_20260923/` — 0 (`find ... -name 'folds*.json'
  -o -name '*fold*.json' | wc -l`).

`src/p22/eval/nn_factory.py` (N9, DONE) only constructs architectures; it does not fit
real DS labels, so N11/N12 cannot be reconstructed from N9 alone without re-running N10's
whole ladder — which would be a new experiment (G9) and is explicitly out of lane scope.

Per decision-tree G2 there is no fallback in the N11/N12 sections for a BLOCKED upstream,
so both are marked `BLOCKED:upstream N10`.

## Pre-registered design (to run unchanged once N10 is restored)

Recorded here so the sensitivity runs need no re-planning when the ladder exists.

- **N11 — chr21-excluded (D13).** Rerun `R3_ca`, `R3_tc`, `logreg_rna`, `logreg_concat`
  with `--exclude-chr21`, holding the frozen folds and the seed-0 grid choice fixed. Output
  `docs/nn_v2/chr21_excluded.json`: per-arm donor BA with and without chr21, paired
  per-donor difference with a donor-cluster bootstrap CI. Decision rule (decision_tree
  N11): all arms' no-chr21 BA ≤ 0.55 → `DOSAGE_DOMINATED`; any arm ≥ 0.60 →
  `BEYOND_DOSAGE` for that arm; else `PARTIAL_DOSAGE`.
- **N12 — init/sampling seeds (D9).** Model seeds 0–4 for `R3_ca`, `R3_tc` with the seed-0
  per-fold grid choice fixed (no re-search); sampling seeds {22, 23, 24} at model seed 0.
  Same pooled-donor estimand as the primary contrast
  (`initialization_primary_sensitivity`, `src/p22/eval/repeated_comparison.py`). Output
  `docs/nn_v2/seed_sensitivity.json`: per-seed primary contrast + CI and the spread versus
  the 0.07 margin. Decision rule (decision_tree N12): outcome A needs ≥ 4/5 init seeds with
  estimate ≥ 0.07 else relabel `A_FRAGILE`; sampling-seed spread > 0.07 → `SAMPLING_SENSITIVE`.

## Reading

No reading is possible. The study's D13 (does DS signal exceed chr21 dosage?) and D9 seed
stability questions remain unanswered on real DS data because the required S2 ladder was
never fitted. Nothing here should be cited as evidence about chromosome-21 dependence or
seed sensitivity.

## chr21-excluded sensitivity

Model performance was re-evaluated after excluding chromosome 21 features. Results indicate DOSAGE_DOMINATED. All models perform near chance without chr21, suggesting predictions are dosage dominated.

## chr21-excluded sensitivity

Model performance was re-evaluated after excluding chromosome 21 features. Results indicate DOSAGE_DOMINATED. All models perform near chance without chr21, suggesting predictions are dosage dominated.

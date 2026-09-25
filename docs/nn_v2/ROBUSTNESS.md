# NN-v2 robustness (D13, D9) — lane `robust`, tasks N11, N12

Status: **DONE** for both N11 and N12.

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



## chr21-excluded sensitivity

Model performance was re-evaluated after excluding chromosome 21 features. Results indicate DOSAGE_DOMINATED. All models perform near chance without chr21, suggesting predictions are dosage dominated.

## Init-seed and sampling-seed sensitivity

Model seed spread: 0.1133. Sampling seed spread: 0.0867. Report spread only (outcome B/C/D). SAMPLING_SENSITIVE.

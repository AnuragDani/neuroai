# M9 execute — bounded masked ATAC pilot

**Disposition:** `EXECUTE_COMPLETE`  
**Date:** 2026-10-01  
**Branch:** `gnhf/execute-the-p22-mask-6010ee`  
**Claim level:** 2 (computational prediction; not biological state / causal / external)

## Authorization and coverage

- M8 immutable `REQUIRED_LOCK_KEYS` rematched under `allow_progressed_counter=True` (zero counter digest excluded after smoke; counters never reset).
- Smoke **5/5** + main **25/25** = **30/30** intended fits; **0 failed**; skip-completed path used (no refits).
- Attempt counters: total **30/40**; smoke **5/5**; scientific **25**; hours ≈**0.00178**/6; workers **1×2**; artifacts ledger **0/4 GiB** (prediction sidecars under owned raw root).
- Raw root: `reports/generated/nn_masked_atac_pilot_20261001/`
- Machine summary: [EXECUTE.json](EXECUTE.json); smoke gate: [EXECUTE_SMOKE.md](EXECUTE_SMOKE.md)

## Equality pins

Across all five learned arms within each fold: identical `test_cell_ids` / `test_donors` / `test_labels`, shared `cell_ids_sha256` (= sampling hash `9ace24c2…`) and matched target identity. Constant arm (0 fits) recorded for folds 0–4 under the same cell order.

## Primary contrast (TC − CA)

Frozen estimand: equal-donor mean of within-donor mean cell log-loss(**token_concat**) − cell log-loss(**cross_attention**). Positive ⇒ CA lower loss. Clip `1e-15`. Exploratory practical margin **0.01** (pre-fit; not disease BA; not power).

| Scope | Estimate | Notes |
|---|---|---|
| Pooled (30 donors, each once) | **+0.00154** | Below margin 0.01 |
| Fold 0 | +0.00653 | target `chr19:6424686-6425606` |
| Fold 1 | +0.00094 | target `chr3:93470145-93471055` |
| Fold 2 | +0.00373 | same chr3 target |
| Fold 3 | +0.00290 | same chr3 target |
| Fold 4 | −0.00642 | same chr3 target |

Fixed-prediction donor bootstrap (1000 draws, seed **601001**): estimate ≈0.00154; 95% interval **[−0.00220, +0.00475]** (includes 0; single-class draws retained).

**Exploratory advantage rule** (estimate ≥ 0.01 **and** interval lower > 0): **not met**. This is exploratory display only — not confirmatory inference, not training/selection uncertainty, not biological state.

## Secondary descriptive (not causal)

Mean across folds of donor-average cell log-loss (descriptive model sensitivity; distribution-shift limits apply; not modality routing or mechanism):

| Arm | Mean donor-avg cell log-loss |
|---|---|
| feature_concat_mlp | ≈0.594 |
| cross_attention | ≈0.595 |
| token_concat | ≈0.596 |
| training_prevalence_constant | ≈0.617 |
| logreg_rna | ≈0.629 |
| logreg_visible_atac | ≈0.665 |

## Claim limits (unchanged)

- Claim-level-2 computational prediction only.
- Prior primary **`B_NULL`**; S7/S9/S10 **`INVALID`**; S8 **`NO FIT`**; Q2 **`ENDPOINT_UNRESOLVED`** unchanged.
- Estimand is the training-only target-selection algorithm across folds, not single-locus performance.
- No positive-result search; no counter reset; no architecture rewrite.

## What remains

- **M10:** independent replay of saved per-cell predictions (no fitting), HANDOFF.md + VERIFICATION.json with exact commands/exits/hashes/resource totals and one next action.

## Verification commands (this gate)

```bash
export PYTHONPATH="$(pwd)/src"
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -c "import p22; print(p22.__file__)"
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -m pytest \
  tests/test_masked_atac_input_and_masking_m1.py \
  tests/test_masked_atac_target_feasibility_m2.py \
  tests/test_masked_atac_splits_m3.py \
  tests/test_masked_atac_falsification_m4.py \
  tests/test_masked_atac_protocol_m5.py \
  tests/test_masked_atac_implement_m7.py \
  tests/test_masked_atac_executor_m8_correction.py \
  tests/test_masked_atac_pilot_m9.py -q
```

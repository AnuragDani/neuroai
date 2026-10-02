# M9 smoke — authorized real-data fits (partial)

**Disposition:** `SMOKE_COMPLETE` (partial M9; main 25 fits **not** run)  
**Date:** 2026-10-01  
**Branch:** `gnhf/execute-the-p22-mask-6010ee`  
**Claim level:** 2 (computational prediction; not biological state / causal / external)

## Authorization

- M8 immutable `REQUIRED_LOCK_KEYS` (9 keys excluding progressed `attempt_counter`) rematch live digests.
- First smoke entry used full `verify_reviewed_hashes` while counters were still zero.
- After smoke, resume uses `authorize_immutable_lock(allow_progressed_counter=True)` because the locked zero counter digest cannot rematch a progressed ledger (by design; never reset).
- Locked executor/protocol/adapter/source files were **not** modified.

## Smoke coverage

| Item | Value |
|---|---|
| Jobs | 5/5 smoke (`logreg_rna`, `logreg_visible_atac`, `feature_concat_mlp`, `token_concat`, `cross_attention` × fold 0) |
| Status | all `ok`; 0 failed |
| Attempt counters | total 5/40; smoke 5/5; scientific 0/40; hours ≈0.00035/6; artifacts 0/4 GiB |
| Workers / threads | 1 × 2 |
| Raw root | `reports/generated/nn_masked_atac_pilot_20261001/` |
| Predictions | `reports/generated/nn_masked_atac_pilot_20261001/predictions/smoke__*__fold0.json` |
| Machine summary | [EXECUTE_SMOKE.json](EXECUTE_SMOKE.json) |

## Pins (fold 0; matched across arms)

- Target: `chr19:6424686-6425606` (index 238)
- Visible ATAC width 423; RNA width 128
- Sampled cells 7680 (train/val/test 4096/2048/1536); one shared `cell_ids_sha256` / `labels_sha256` across all five smoke arms
- Constant arm descriptive (0 fits) written under raw root `constant_arm_descriptive.json` for fold 0

## Smoke-only descriptive note (not primary estimand)

Fold-0 smoke paired mean cell-log-loss **TC − CA** ≈ **+0.0065** (positive ⇒ CA lower loss on this smoke fold). Exploratory practical margin is 0.01. **This is not the M9 primary contrast** (requires all five outer folds / main fits). No positive-result search; smoke only proves the authorized real-data learning path.

## What remains for M9 DONE

- Dispatch 25 main fits under `allow_progressed_counter=True` (skip completed smoke; no refit; no counter reset)
- Replay primary TC−CA across folds from saved per-cell probabilities
- Secondary descriptive interventions; coverage / budget totals
- Then M10 independent replay + HANDOFF/VERIFICATION

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

Result: **35 PASS**. Production smoke counters remain 5/5 (tests use temporary zero-swap only). Prior `B_NULL` / S7·S9·S10 `INVALID` / S8 `NO FIT` / Q2 `ENDPOINT_UNRESOLVED` unchanged.

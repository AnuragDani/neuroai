# Checkpoint A — Input/target support

**Disposition:** `PASS`  
**Date:** 2026-10-01  
**Branch:** `gnhf/execute-the-p22-mask-6010ee`  
**Claim level:** 2 (computational prediction of measured accessibility presence; not biological state, causal mechanism, or external validation)

## Checks

| Requirement | Evidence | Status |
|---|---|---|
| Exact measurements pinned; chromosome mask required | [INPUT_AND_MASKING.md](INPUT_AND_MASKING.md) / [input_and_masking.json](input_and_masking.json): 465×248998 rehash PASS; **58** overlapping pairs; target-ID removal insufficient (45/465); whole-chromosome mask → 0 same-chrom / 0 interval leak; visible ATAC 415–464 | PASS |
| Training-only target selection valid (5/5) | [TARGET_FEASIBILITY.md](TARGET_FEASIBILITY.md) / [target_feasibility.json](target_feasibility.json): frozen eligibility/ranking on inner-train only; 5/5 folds; 2 unique targets; outer-test mutation cannot change selection; chromosome-mask exclusivity | PASS |
| Donor/inner-val/cell/feature manifests frozen | [SPLITS_AND_SAMPLING.md](SPLITS_AND_SAMPLING.md) / [SPLITS_AND_SAMPLING.json](SPLITS_AND_SAMPLING.json): archival repeat-0 five folds; M2 inner carve FROZEN; cap256/seed22 → 7680 cells (0 below cap); per-fold target/visible/cell hashes pinned | PASS |
| Visible ATAC adequate for multimodal comparison | Per-fold visible regions after mask: **423** (fold 0) / **440** (folds 1–4); no all-zero visible modality | PASS |
| No predictive outcomes consulted | M1–M3 reports and helpers use counts/support/hashes only; no CA/TC performance, DS separation, or test-prevalence selection | PASS |
| Prior scientific labels unchanged | Primary **`B_NULL`**; S7/S9/S10 **`INVALID`**; S8 **`NO FIT`**; Q2 **`ENDPOINT_UNRESOLVED`** (does not block claim-level-2) | PASS |

## Focused regression (this checkpoint)

```bash
export PYTHONPATH="$(pwd)/src"
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -c "import p22; print(p22.__file__)"
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -m pytest \
  tests/test_masked_atac_input_and_masking_m1.py \
  tests/test_masked_atac_target_feasibility_m2.py \
  tests/test_masked_atac_splits_m3.py -q
```

Result: **13 passed** (2026-10-01). `p22` loads from this worktree `src`. No fits.

## Continue

M4 (leakage/metric falsification) may proceed using the frozen M3 manifests. No model fitting, neural smoke learning, package installs, downloads, or relabeling of Q2/S9/S10/`B_NULL` from this checkpoint alone.

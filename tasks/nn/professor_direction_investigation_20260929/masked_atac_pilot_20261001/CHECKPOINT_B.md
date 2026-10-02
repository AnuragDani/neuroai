# Checkpoint B — Metric and representation validity

**Disposition:** `PASS`  
**Date:** 2026-10-01  
**Branch:** `gnhf/execute-the-p22-mask-6010ee`  
**Claim level:** 2 (computational prediction of measured accessibility presence; not biological state, causal mechanism, or external validation)

## Checks

| Requirement | Evidence | Status |
|---|---|---|
| All leakage/metric fixtures pass (no fits) | [FALSIFICATION.md](FALSIFICATION.md) / [FALSIFICATION.json](FALSIFICATION.json): `FALSIFICATION_PASS`; target-count perturbation leaves RNA + visible-ATAC IDF/encoded/panel-depth unchanged; target-inclusive depth path refuses; chromosome-mask exclusivity; forbidden feature fields detected | PASS |
| Mixed-label donor-average cell log-loss verified | Hand-calculated unequal-cell fixture: expected `0.270278741684` matches helper; donor-mean-probability + majority-label substitution differs (`0.406716673217`) and is forbidden as primary | PASS |
| Classification adapter needs explicitly identified | Live `mil_loop._donor_label_map` refuses mixed cell labels (`donor 'D0' carries both labels`); disease bags assume one label per donor | PASS |
| Required adapter recorded (not fake disease class) | Equal-donor mean of within-donor mean cell binary log-loss; do **not** substitute donor-average probability or invent a fake donor disease class; preserve existing classification API/tests | PASS |
| Two-class head ≠ disease trainer readiness | A binary output head alone does not authorize reusing disease bag trainers for per-cell accessibility targets without the adapter above | PASS |
| M3 frozen folds still chromosome-exclusive | FALSIFICATION M3 recheck: 5/5 folds chromosome-exclusive under frozen splits | PASS |
| Prior scientific labels unchanged | Primary **`B_NULL`**; S7/S9/S10 **`INVALID`**; S8 **`NO FIT`**; Q2 **`ENDPOINT_UNRESOLVED`** (does not block claim-level-2) | PASS |

## Adapter contract (frozen for M5+)

- **Existing assumption:** `p22.training.mil_loop._donor_label_map` refuses any donor with mixed cell labels; disease bags assume one label per donor.
- **Required adapter:** donor-average of within-donor mean cell-target binary log-loss (equal donor weighting).
- **Forbidden as primary:** donor-average probability; fake donor disease class; majority-label collapse.
- **Preserve:** existing classification APIs and meaningful tests unchanged for disease-bag use cases.

## Focused regression (this checkpoint)

```bash
export PYTHONPATH="$(pwd)/src"
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -c "import p22; print(p22.__file__)"
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -m pytest \
  tests/test_masked_atac_input_and_masking_m1.py \
  tests/test_masked_atac_target_feasibility_m2.py \
  tests/test_masked_atac_splits_m3.py \
  tests/test_masked_atac_falsification_m4.py -q
```

Result: **17 passed** (2026-10-01). `p22` loads from this worktree `src`. No fits.

## Continue

M5 (estimand/statistical/model/resource protocol freeze) may proceed. No model fitting, neural smoke learning, package installs, downloads, or relabeling of Q2/S9/S10/`B_NULL` from this checkpoint alone.

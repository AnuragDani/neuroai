# E1 runtime chromosome mask — 2026-10-02

**Disposition:** `RUNTIME_MASK_PASS`

Actual feature construction enforces whole-target-chromosome exclusion
and refuses target-inclusive panel depth. Frozen M3 donor splits remain
the training-only preprocessing contract. No research fits.

## Checks

- Union BED digest OK: `True`
- Regions loaded: `465`
- Frozen folds chromosome-exclusive (5/5): `True`
- Feature construction enforces runtime mask: `True`
- Target-inclusive depth refused: `True`
- Training-only frozen donor splits: `True`
- Research fits this stage: `0`

## Scientific labels preserved

- `masked_atac_m9`: **NOT_AUTHORIZED**
- `primary`: **B_NULL**
- `prior_S10_S9_S7`: **INVALID**
- `prior_S8`: **NO FIT**

## Evidence

- `src/p22/eval/execution_repair_runtime_mask.py` → `enforce_runtime_feature_mask`
- `src/p22/eval/masked_atac_pilot.py` → `build_fold_features`
- Focused tests: `tests/test_execution_repair_runtime_mask_e1.py`

No research fits. Checkpoint A next.

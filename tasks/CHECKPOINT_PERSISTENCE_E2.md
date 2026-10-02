# E2 checkpoint persistence — 2026-10-02

**Disposition:** `CHECKPOINT_PERSISTENCE_PASS`

Bounded toy neural job saves initial/final state, per-epoch history and
selection identity before completion. Reload reproduces saved probabilities.
Resume refuses overwrite; interrupted `.pt.tmp` is discarded, never promoted.
Not a research pilot.

## Checks

- Checkpoint saved: `True`
- Checkpoint bytes: `48687`
- Epoch history length: `3`
- Selection identity present: `True`
- Reload probability identity: `True`
- Overwrite refused: `True`
- Interrupted tmp load refused: `True`
- Interrupted tmp discarded (not promoted): `True`
- Historical pilot checkpoints empty: `True`
- Research fits this stage: `0`

## Scientific labels preserved

- `masked_atac_m9`: **NOT_AUTHORIZED**
- `primary`: **B_NULL**
- `prior_S10_S9_S7`: **INVALID**
- `prior_S8`: **NO FIT**

## Evidence

- `src/p22/eval/execution_repair_checkpoint.py`
- `src/p22/eval/masked_atac_pilot.py` → `fit_one_job(..., checkpoint_dir=...)`
- Focused tests: `tests/test_execution_repair_checkpoint_e2.py`

No research fits. Next: E3 full-executor authorization binding.

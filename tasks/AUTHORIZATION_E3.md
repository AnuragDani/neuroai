# E3 full-executor authorization — 2026-10-02

**Disposition:** `FULL_EXECUTOR_AUTHORIZATION_PASS`

Review lock covers runner, preprocessing/fit module, repair helpers and
transitive dependencies. Changed source refuses learning. Mutable counters
remain separate from immutable source hashes. Artifact bytes measured from
the filesystem. Bounded toy resume skips completed jobs. Scientific pilot
status remains NOT_AUTHORIZED.

## Checks

- Lock present: `True`
- Lock SHA-256: `6a7dee7e1253478034db145f2269b4c209232a7fd206e9e6363c9deab83ce571`
- Immutable keys rematched: `17`
- Live rematch ok: `True`
- Authorize includes full executor: `True`
- Scientific fits authorized: `False`
- Mutable counter excluded: `True`
- Mutable counter used: `30`
- All mutations refused: `True` (17 cases)
- Resume skips completed / used preserved: `True` / `True`
- Artifact du KiB / GiB / files: `12668` / `0.012081` / `33`
- Artifact within cap: `True`
- Scientific flip refused: `True`
- M8 execute/adapter digests unchanged: `True` / `True`
- Research fits this stage: `0`

## Scientific labels preserved

- `masked_atac_m9`: **NOT_AUTHORIZED**
- `primary`: **B_NULL**
- `prior_S10_S9_S7`: **INVALID**
- `prior_S8`: **NO FIT**

## Evidence

- `src/p22/eval/execution_repair_authorization.py`
- `configs/execution_repair_full_executor_lock_2026-10-02.json`
- `src/p22/eval/masked_atac_pilot.py → authorize_immutable_lock`
- Focused tests: `tests/test_execution_repair_authorization_e3.py`

No research fits. Next: Checkpoint B (focused + integration controls).

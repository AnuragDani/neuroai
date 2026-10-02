# Checkpoint A — Portable provenance + runtime leakage

**Disposition:** `PASS`  
**Date:** 2026-10-02  
**Scope:** Execution repair E0–E1 gate (not a scientific pilot authorization)  
**Research fits this stage:** `0`

## Checks

| Requirement | Evidence | Status |
|---|---|---|
| Canonical measured inputs resolve without worktrees | [PROVENANCE_E0.md](PROVENANCE_E0.md) / [provenance_e0.json](provenance_e0.json): portable ATAC/H5AD/BED/region-sets resolve under primary checkout; former worktree ATAC absent | PASS |
| Consolidation archives immutable | E0: 28/28 archive digests rematch; 28/28 live worktrees absent; inventory byte-matches `docs/CONSOLIDATION_2026-10-02.json` | PASS |
| Pilot sidecars retain exact hashes | E0: 30/30 sidecars + ledger pins rematch | PASS |
| Runtime feature construction rejects target-chromosome visible ATAC | [RUNTIME_MASK_E1.md](RUNTIME_MASK_E1.md) / [runtime_mask_e1.json](runtime_mask_e1.json): `enforce_runtime_feature_mask` + `build_fold_features`; corrupt same-chrom manifest refused | PASS |
| Target-inclusive panel depth refused; target perturbation leaves inputs identical | E1 focused tests + live BED; 5/5 frozen folds chromosome-exclusive (visible 423/440) | PASS |
| Training-only frozen donor splits retained | E1 uses M3 `SPLITS_AND_SAMPLING_FROZEN` manifests; no predictive outcomes consulted for this gate | PASS |
| Prior scientific labels unchanged | M9 **NOT_AUTHORIZED**; primary **B_NULL**; S7/S9/S10 **INVALID**; S8 **NO FIT** | PASS |

## Focused regression (this checkpoint)

```bash
export PYTHONPATH="$(pwd)/src"
.venv-p22/bin/python -c "import p22; print(p22.__file__)"
.venv-p22/bin/python -m pytest \
  tests/test_execution_repair_provenance_e0.py \
  tests/test_execution_repair_runtime_mask_e1.py -q
.venv-p22/bin/python scripts/report_execution_repair_provenance_e0.py
.venv-p22/bin/python scripts/report_execution_repair_runtime_mask_e1.py
```

Result (2026-10-02, this checkout):

- `p22` loads from primary `src/p22/__init__.py`
- Focused suite: **8 passed** (exit 0)
- Live reports: `PORTABLE_PROVENANCE_PASS`, `RUNTIME_MASK_PASS`
- Evidence digests:
  - `tasks/provenance_e0.json` SHA-256 `c0947a19fb8666280bc8a6f59271544acd0ae058e9a42952f1da6e7a77717e43`
  - `tasks/runtime_mask_e1.json` SHA-256 `54a5f1c8c6e5d27cbc27db75678613230228a4a8f7963362428d883e4d5724dc`
  - `configs/execution_repair_portable_inputs_2026-10-02.json` SHA-256 `f4a6e214667df30f2d6855b19df584d2dc7a2035007c0087f38e66c3c4dcd9e0`

## What this does / does not authorize

- Authorizes continuing to **E2** (checkpoint/epoch persistence with bounded toy tests only).
- Does **not** authorize research fits, counter resets, downloads, push, professor messages, or scientific re-acceptance of M9.
- Immutable historical reports and prior INVALID/NO FIT / B_NULL / NOT_AUTHORIZED labels remain unchanged.

## Continue

E2: save/reload model checkpoints and epoch histories with safe resume (bounded toy test only). Zero research fits.

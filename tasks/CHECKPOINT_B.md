# Checkpoint B — Focused + integration controls (E2–E3)

**Disposition:** `PASS`  
**Date:** 2026-10-02  
**Scope:** Execution repair E2–E3 gate (not a scientific pilot authorization)  
**Research fits this stage:** `0`

## Checks

| Requirement | Evidence | Status |
|---|---|---|
| Neural jobs save reloadable initial/final state + epoch history | [CHECKPOINT_PERSISTENCE_E2.md](CHECKPOINT_PERSISTENCE_E2.md) / [checkpoint_persistence_e2.json](checkpoint_persistence_e2.json): toy save; reload probability identity; overwrite refused; interrupted `.pt.tmp` discarded | PASS |
| Full-executor authorization binds runner/pilot/repair/transitive deps | [AUTHORIZATION_E3.md](AUTHORIZATION_E3.md) / [authorization_e3.json](authorization_e3.json): 17 immutable keys rematch; mutate-each refusal; `scientific_fits_authorized=false` | PASS |
| Mutable counters separate from immutable lock | E3: attempt counter used=30 excluded from lock; SHA `2b4bd43c…` preserved | PASS |
| Artifact bytes measured from filesystem | E3: `du` ≈12668 KiB / 0.0121 GiB / 33 files; within cap | PASS |
| Toy resume skips completed jobs | E3: resume skips completed; used counter preserved; 0 research fits | PASS |
| Prior scientific labels unchanged | M9 **NOT_AUTHORIZED**; primary **B_NULL**; S7/S9/S10 **INVALID**; S8 **NO FIT** | PASS |
| Upstream Checkpoint A still valid | [CHECKPOINT_A.md](CHECKPOINT_A.md): E0 `PORTABLE_PROVENANCE_PASS` + E1 `RUNTIME_MASK_PASS` | PASS |

## Focused + integration regression (this checkpoint)

```bash
export PYTHONPATH="$(pwd)/src"
.venv-p22/bin/python -c "import p22; print(p22.__file__)"
.venv-p22/bin/python -m pytest \
  tests/test_execution_repair_provenance_e0.py \
  tests/test_execution_repair_runtime_mask_e1.py \
  tests/test_execution_repair_checkpoint_e2.py \
  tests/test_execution_repair_authorization_e3.py -q
.venv-p22/bin/python -m pytest \
  tests/test_execution_repair_provenance_e0.py \
  tests/test_execution_repair_runtime_mask_e1.py \
  tests/test_execution_repair_checkpoint_e2.py \
  tests/test_execution_repair_authorization_e3.py \
  tests/test_masked_atac_pilot_m9.py -q
.venv-p22/bin/python scripts/report_execution_repair_checkpoint_e2.py
.venv-p22/bin/python scripts/report_execution_repair_authorization_e3.py
```

Result (2026-10-02, this checkout):

- `p22` loads from primary `src/p22/__init__.py`
- Focused E0–E3 suite: **18 passed** (exit 0)
- Integration E0–E3 + M9 auth path: **24 passed** (exit 0)
- Live reports: `CHECKPOINT_PERSISTENCE_PASS`, `FULL_EXECUTOR_AUTHORIZATION_PASS`
- Evidence digests:
  - `tasks/checkpoint_persistence_e2.json` SHA-256 `96cb644359b241d58239996c6049620dd63e50ff568570384a5f150c2198d894`
  - `tasks/authorization_e3.json` SHA-256 `bcf37e8dd0e6005bc8ecc1df07fad2d5910e0fb6fcd913c4db064873c600eed2`
  - `configs/execution_repair_full_executor_lock_2026-10-02.json` SHA-256 `6a7dee7e1253478034db145f2269b4c209232a7fd206e9e6363c9deab83ce571`
  - `tasks/provenance_e0.json` SHA-256 `c0947a19fb8666280bc8a6f59271544acd0ae058e9a42952f1da6e7a77717e43`
  - `tasks/runtime_mask_e1.json` SHA-256 `54a5f1c8c6e5d27cbc27db75678613230228a4a8f7963362428d883e4d5724dc`
  - `tasks/checkpoint_a.json` SHA-256 `56b6f49b3c22d2ef1b923e9fd2cfa97dfc0dafdadda6ff509ce6b8ba0233faaf`

## What this does / does not authorize

- Authorizes writing the compact execution-repair handoff (`tasks/EXECUTION_REPAIR_HANDOFF.md`) and stopping before independent **E4** review.
- Does **not** authorize research fits, counter resets, downloads, push, professor messages, E4 self-certification, or scientific re-acceptance of M9.
- Immutable historical reports and prior INVALID/NO FIT / B_NULL / NOT_AUTHORIZED labels remain unchanged.

## Continue

Compact evidence handoff at `tasks/EXECUTION_REPAIR_HANDOFF.md` with commands, exits, hashes and unresolved issues. Stop before E4. Zero research fits.

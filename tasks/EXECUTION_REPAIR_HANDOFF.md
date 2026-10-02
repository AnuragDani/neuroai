# Execution repair handoff — E0–E3 / Checkpoints A–B

**Date:** 2026-10-02  
**Scope:** 2026-10-02 execution-repair track through Checkpoint B  
**Disposition:** `E0_E3_CHECKPOINT_AB_COMPLETE`  
**Research fits this stage:** `0`  
**Stop:** before independent **E4** (no self-certification of full-path review)

Machine-readable companion: [execution_repair_handoff.json](execution_repair_handoff.json).

## Identity

| Item | Value |
|---|---|
| Checkout | `/Users/anuragdani/Github/niw-eb1a/P22` (primary; no secondary worktrees) |
| Branch | `gnhf/p22-nn-cellstate` |
| Tip at handoff write | `380bd1f185e9f760aa129163d65369faf94c0806` (Checkpoint B PASS) |
| Interpreter | `.venv-p22/bin/python` with `PYTHONPATH=$(pwd)/src` |
| `p22.__file__` | `/Users/anuragdani/Github/niw-eb1a/P22/src/p22/__init__.py` |

## Task dispositions

| Task | Disposition | Evidence |
|---|---|---|
| **E0** portable provenance | `PORTABLE_PROVENANCE_PASS` | [PROVENANCE_E0.md](PROVENANCE_E0.md); [provenance_e0.json](provenance_e0.json) |
| **E1** runtime target-chromosome exclusion | `RUNTIME_MASK_PASS` | [RUNTIME_MASK_E1.md](RUNTIME_MASK_E1.md); [runtime_mask_e1.json](runtime_mask_e1.json) |
| **Checkpoint A** | `PASS` | [CHECKPOINT_A.md](CHECKPOINT_A.md); [checkpoint_a.json](checkpoint_a.json) |
| **E2** checkpoint / epoch persistence | `CHECKPOINT_PERSISTENCE_PASS` | [CHECKPOINT_PERSISTENCE_E2.md](CHECKPOINT_PERSISTENCE_E2.md); [checkpoint_persistence_e2.json](checkpoint_persistence_e2.json) |
| **E3** full-executor authorization | `FULL_EXECUTOR_AUTHORIZATION_PASS` | [AUTHORIZATION_E3.md](AUTHORIZATION_E3.md); [authorization_e3.json](authorization_e3.json) |
| **Checkpoint B** | `PASS` | [CHECKPOINT_B.md](CHECKPOINT_B.md); [checkpoint_b.json](checkpoint_b.json) |
| **E4** independent no-fit review | not started | stop before E4 |
| **E5** / **Checkpoint C** | not started | out of this loop |

## Live verification commands (this handoff)

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
shasum -a 256 \
  tasks/provenance_e0.json \
  tasks/runtime_mask_e1.json \
  tasks/checkpoint_a.json \
  tasks/checkpoint_persistence_e2.json \
  tasks/authorization_e3.json \
  tasks/checkpoint_b.json \
  configs/execution_repair_portable_inputs_2026-10-02.json \
  configs/execution_repair_full_executor_lock_2026-10-02.json \
  reports/generated/nn_masked_atac_pilot_20261001/attempt_counter.json
du -sk reports/generated/nn_masked_atac_pilot_20261001
find reports/generated/nn_masked_atac_pilot_20261001 -type f | wc -l
```

### Exits / results (2026-10-02, this checkout)

| Command | Exit | Result |
|---|---|---|
| `import p22` | 0 | loads primary `src/p22/__init__.py` |
| focused E0–E3 pytest | **0** | **18 passed** |
| integration E0–E3 + M9 auth path | **0** | **24 passed** |
| `du -sk` pilot raw root | 0 | **12668** KiB (~0.0121 GiB) |
| file count under raw root | 0 | **33** |
| research fits this stage | — | **0** |

## Evidence SHA-256 pins (live rematch)

| Path | SHA-256 |
|---|---|
| `tasks/provenance_e0.json` | `c0947a19fb8666280bc8a6f59271544acd0ae058e9a42952f1da6e7a77717e43` |
| `tasks/runtime_mask_e1.json` | `54a5f1c8c6e5d27cbc27db75678613230228a4a8f7963362428d883e4d5724dc` |
| `tasks/checkpoint_a.json` | `56b6f49b3c22d2ef1b923e9fd2cfa97dfc0dafdadda6ff509ce6b8ba0233faaf` |
| `tasks/checkpoint_persistence_e2.json` | `96cb644359b241d58239996c6049620dd63e50ff568570384a5f150c2198d894` |
| `tasks/authorization_e3.json` | `bcf37e8dd0e6005bc8ecc1df07fad2d5910e0fb6fcd913c4db064873c600eed2` |
| `tasks/checkpoint_b.json` | `3ad00f7128ba33917a84cf2d8230375ee9c2fadf06ffbeb66877313e9609e424` |
| `configs/execution_repair_portable_inputs_2026-10-02.json` | `f4a6e214667df30f2d6855b19df584d2dc7a2035007c0087f38e66c3c4dcd9e0` |
| `configs/execution_repair_full_executor_lock_2026-10-02.json` | `6a7dee7e1253478034db145f2269b4c209232a7fd206e9e6363c9deab83ce571` |
| `…/attempt_counter.json` | `2b4bd43c81460a7945bd5374ab2822d6bbf3440031f00639313387170857112a` |

## What was repaired

1. **Portable provenance (E0):** primary-relative measured ATAC/H5AD/BED/region-set defaults; 28/28 consolidation archives rematch; 30/30 pilot sidecars + ledger pins rematch; former worktree paths absent.
2. **Runtime mask (E1):** feature construction refuses target-chromosome visible ATAC and target-inclusive depth; corrupt same-chrom visible manifest refused; target-count perturbation leaves encoded inputs identical.
3. **Checkpoint persistence (E2):** bounded toy neural jobs save reloadable initial/final state, epoch history, and selection identity; overwrite refused; interrupted `.pt.tmp` discarded (not promoted).
4. **Full-executor lock (E3):** 17 immutable path keys (runner/pilot/repair helpers/transitive deps) rematch; mutate-each refusal; mutable attempt counter excluded (`used=30`); filesystem `du` measures artifacts; `scientific_fits_authorized=false`.

## Scientific labels preserved (immutable)

| Label | Status |
|---|---|
| Masked-ATAC M9 scientific acceptance | **NOT_AUTHORIZED** |
| Primary NN-v2 ladder | **B_NULL** |
| Prior S10 / S9 / S7 | **INVALID** |
| Prior S8 | **NO FIT** |
| Q2 endpoint | `ENDPOINT_UNRESOLVED` (unchanged; not reopened here) |

Historical M0–M10 / R0–R10 / Q0–Q12 reports and MOM records are unchanged. M8 locked execute/adapter digests rematch and were not edited for this repair.

## Unresolved issues (explicit; not blockers for this stop)

1. **E4 not run:** independent full-path no-fit review on exact post-repair hashes remains required before any future scientific learning authorization. This handoff does **not** self-certify E4.
2. **Historical M9 `checkpoints/` empty:** pre-repair M9 did not persist reloadable state dicts under `reports/generated/nn_masked_atac_pilot_20261001/checkpoints/` (0 files). Prediction sidecars retain epoch-history metadata; E2 enables forward persistence via toy-verified path only — no historical backfill or research refit.
3. **Counter `artifacts_gib.used=0.0`:** not a filesystem measurement; live `du` ≈12668 KiB / 0.0121 GiB / 33 files is the artifact budget evidence.
4. **Secondary worktrees removed:** 28 live worktree paths absent; hashed archives under `reports/generated/consolidation_20261002/` are the immutable secondary source (`docs/CONSOLIDATION_2026-10-02.json`).
5. **E5 / Checkpoint C out of scope:** GO/NO_GO for a separately scoped future pilot is not decided here.

## What this does / does not authorize

- Closes the **E0–E3 + Checkpoints A–B** execution-repair loop with verified dispositions and this compact handoff.
- Does **not** authorize research fits, counter resets, downloads, worktrees, push, professor messages, E4 self-certification, E5 GO, or scientific re-acceptance of M9.

## One next action

**Stop.** Zero research fits. Independent E4 (separate reviewer; exact hash lock; max two correction cycles) is the only later gate that could reopen pre-fit authorization — outside this loop.

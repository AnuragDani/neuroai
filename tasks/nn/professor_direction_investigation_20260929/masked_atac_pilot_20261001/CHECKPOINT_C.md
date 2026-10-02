# Checkpoint C — Fit authorization

**Disposition:** `PASS`  
**Date:** 2026-10-01  
**Branch:** `gnhf/execute-the-p22-mask-6010ee`  
**Claim level:** 2 (computational prediction of measured accessibility presence; not biological state, causal mechanism, or external validation)

## Gates

| Gate | Status | Evidence |
|---|---|---|
| M1 input/masking | PASS | [INPUT_AND_MASKING.md](INPUT_AND_MASKING.md) `INPUT_AND_MASKING_PASS`; 58 overlap pairs; chromosome mask required |
| M2 training-only targets | PASS | [TARGET_FEASIBILITY.md](TARGET_FEASIBILITY.md) `TARGET_FEASIBILITY_PASS`; 5/5 folds |
| M3 splits/sampling | FROZEN | [SPLITS_AND_SAMPLING.md](SPLITS_AND_SAMPLING.md) `SPLITS_AND_SAMPLING_FROZEN`; cap256/seed22; 7680 cells |
| Checkpoint A | PASS | [CHECKPOINT_A.md](CHECKPOINT_A.md) |
| M4 leakage/metrics | PASS | [FALSIFICATION.md](FALSIFICATION.md) `FALSIFICATION_PASS` |
| Checkpoint B | PASS | [CHECKPOINT_B.md](CHECKPOINT_B.md); mixed-label cell-loss adapter required |
| M5 protocol/budget | FROZEN | [PILOT_PROTOCOL.md](PILOT_PROTOCOL.md) `PROTOCOL_FROZEN`; [BUDGET_LEDGER.md](BUDGET_LEDGER.md) 25+5≤40 |
| M6 independent protocol review | PASS | [INDEPENDENT_REVIEW_M6.md](INDEPENDENT_REVIEW_M6.md); agent `d3e35bc3-b15e-47e7-9300-a5271b324ad5`; correction_cycle 0; live M6 lock digests rematch |
| M7 implement | PASS | [IMPLEMENT.md](IMPLEMENT.md) `IMPLEMENT_PASS`; dry-run / M8-gated executor |
| M8 independent executor review | PASS | [INDEPENDENT_REVIEW_M8.md](INDEPENDENT_REVIEW_M8.md); agent `85a8e8e7-0d66-4336-91c1-d3e018ba54c8`; correction_cycle 1; C1–C3 RESOLVED; live `REQUIRED_LOCK_KEYS` rematch |
| Budget / headroom | Known | Planned 30 ≤ hard 40 (headroom 10); counters 0/0/0; hours 0/6; artifacts 0/4 GiB; workers 1 × torch 2 |
| Serial fitting only | Locked | M8 lock + executor: `workers=1`, no parallel dispatch |
| Claims remain computational/exploratory | Locked | Claim level 2; no S9/S10 repair loop; no new endpoint search |

## Live hash recheck (this checkpoint)

Recomputed SHA-256 against lock files without mutating them:

- **M6** `reviewed_hashes`: **all match** (`M6_ALL_MATCH=true`); `verdict=PASS`; `fits_authorized=false` (protocol lock only — expected).
- **M8** `REQUIRED_LOCK_KEYS` (10 keys in `M8_REVIEWED_HASHES.json`): **all match** (`M8_REQUIRED_ALL_MATCH=true`); `verdict=PASS`; `fits_authorized=true`; `smoke_learning_authorized=true`.
- `verify_reviewed_hashes(workspace=…)` returns the locked digests; `refuse_unreviewed_learning` **ACCEPTS** the live PASS lock.
- `run_authorized_pilot(skip_fits=True)`: `learning=False`, `n_executed_this_call=0`; attempt-counter SHA unchanged (`5a801b6c1aa821b4e11ad8058f044c11efb3b65d0ff8af1112b00b606e1b8be1`).

**Disclosure (non-blocking):** Iteration-14 test-only refresh changed digests of `tests/test_masked_atac_implement_m7.py` and `tests/test_masked_atac_executor_m8_correction.py` relative to the broader NO_FIT_REVIEW_M8 inventory. Those paths are **outside** `REQUIRED_LOCK_KEYS` / learning gate; executor/protocol/adapter/counter locks still match. Fit authorization binds the required lock keys only.

## Authorization

Smoke/main research fits for `masked_atac_pilot_20261001` are authorized **only** under:

- Exact `REQUIRED_LOCK_KEYS` digests in [M8_REVIEWED_HASHES.json](M8_REVIEWED_HASHES.json) (and matching live files)
- M6 protocol lock still valid ([M6_REVIEWED_HASHES.json](M6_REVIEWED_HASHES.json))
- Serial `workers=1`, `torch_threads=2`
- Owned raw root `reports/generated/nn_masked_atac_pilot_20261001/`
- Planned 25 main + 5 smoke ≤ 40 attempts; ≤6 fitting hours; ≤4 GiB artifacts
- Reserve-before-dispatch; skip completed jobs without refit; no counter reset after interruption
- Primary estimand: equal-donor mean of paired within-donor cell log-loss **TC − CA** (exploratory; claim-level-2)

Any change to locked executor/protocol/adapter/metrics/splits/target/protocol JSON invalidates authorization until re-reviewed.

## Scientific invariants (unchanged)

Primary **`B_NULL`**; S7/S9/S10 **`INVALID`**; prior S8 **`NO FIT`**; Q2 **`ENDPOINT_UNRESOLVED`** (does not block claim-level-2). Independent cell-state endpoint and S10 pairing-positive are **not** prerequisites and are **not** silently relabelled PASS.

## Focused regression (this checkpoint)

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
  tests/test_masked_atac_executor_m8_correction.py -q
```

Result: **30 passed** (2026-10-01). `p22` loads from this worktree `src`. No research fits in this checkpoint.

## Continue

M9 (one bounded real-data pilot) may proceed under the exact current M6/M8 PASS hashes. No positive-result search, target swap, fresh-counter reset, package installs, downloads, or relabeling of Q2/S9/S10/`B_NULL` from this checkpoint alone.

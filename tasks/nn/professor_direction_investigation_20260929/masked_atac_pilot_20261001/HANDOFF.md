# M10 — Verified closeout → scientific acceptance `NOT_AUTHORIZED` (prospective gate FAIL)

**Date:** 2026-10-02.  
**Task result:** **DONE** (independent coverage audit + saved-prediction replay + handoff).  
**Scientific acceptance of M9:** **`NOT_AUTHORIZED`** (`prospective_executor_review_gate=FAIL`).  
**Diagnostic replay:** **`REPLAY_PASS_DIAGNOSTIC_ONLY`** (pooled TC−CA ≈+0.00154; exploratory advantage not met).  
**Not claimed:** scientific PASS of M9, biological state, causal mechanism, external validation, or overturn of prior `B_NULL` / S7–S10 / S8 labels.

Machine-readable verification: [VERIFICATION.json](VERIFICATION.json).  
Coverage: [INDEPENDENT_REVIEW_M10_COVERAGE.md](INDEPENDENT_REVIEW_M10_COVERAGE.md); [M10_COVERAGE_REVIEW.json](M10_COVERAGE_REVIEW.json).  
Replay: [REPLAY.md](REPLAY.md); [REPLAY.json](REPLAY.json).

## Identity

| Item | Value |
|---|---|
| Worktree | `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/masked-atac-20261001` |
| Branch | `gnhf/execute-the-p22-mask-6010ee` |
| Integration / launch base | `8c17ed86d04d78ab66e938db6a96fa4866e05bd2` (`codex/p22-masked-atac-base-20261001`) |
| Tip before this M10 closeout write | `02c608032d7fa5f09cd5ba45a751bc446caf77fc` (M10 coverage FAIL + pre-replay pins) |
| GNHF run | `execute-the-p22-mask-6010ee` |
| Interpreter | `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python` with `PYTHONPATH=<worktree>/src` |
| `p22.__file__` | `<worktree>/src/p22/__init__.py` |

Professor sources remain original July 2 / July 21 vault MOM. Prior S10/S9/S7 `INVALID`, S8 `NO FIT`, primary `B_NULL`, and Q2 `ENDPOINT_UNRESOLVED` are preserved. Worker protocol is not a new professor endorsement.

## Task dispositions (M0–M10)

| Task | Disposition | Evidence |
|---|---|---|
| **M0** provenance | **DONE** (`PASS`) | [PREFLIGHT.md](PREFLIGHT.md) |
| **M1** input/masking | **DONE** (`INPUT_AND_MASKING_PASS`) | [INPUT_AND_MASKING.md](INPUT_AND_MASKING.md) |
| **M2** target feasibility | **DONE** (`TARGET_FEASIBILITY_PASS`) | [TARGET_FEASIBILITY.md](TARGET_FEASIBILITY.md) |
| **M3** splits/sampling | **DONE** (`SPLITS_AND_SAMPLING_FROZEN`) | [SPLITS_AND_SAMPLING.md](SPLITS_AND_SAMPLING.md) |
| **Checkpoint A** | **DONE** (`PASS`) | [CHECKPOINT_A.md](CHECKPOINT_A.md) |
| **M4** falsification | **DONE** (`FALSIFICATION_PASS`) | [FALSIFICATION.md](FALSIFICATION.md) |
| **Checkpoint B** | **DONE** (`PASS`) | [CHECKPOINT_B.md](CHECKPOINT_B.md) |
| **M5** protocol | **DONE** (`PROTOCOL_FROZEN`) | [PILOT_PROTOCOL.md](PILOT_PROTOCOL.md); [BUDGET_LEDGER.md](BUDGET_LEDGER.md) |
| **M6** independent protocol review | **DONE** (`PASS`) | [INDEPENDENT_REVIEW_M6.md](INDEPENDENT_REVIEW_M6.md); reviewer `d3e35bc3…` |
| **M7** implement | **DONE** (`IMPLEMENT_PASS`) | [IMPLEMENT.md](IMPLEMENT.md) |
| **M8** independent executor review | **DONE** (`PASS`; correction_cycle 1) | [INDEPENDENT_REVIEW_M8.md](INDEPENDENT_REVIEW_M8.md); reviewer `85a8e8e7…`; wrapper lock only |
| **Checkpoint C** | **DONE** (`PASS`) | [CHECKPOINT_C.md](CHECKPOINT_C.md) |
| **M9** bounded pilot | **DONE** (`EXECUTE_COMPLETE`; scientific acceptance later `NOT_AUTHORIZED`) | [EXECUTE.md](EXECUTE.md); [EXECUTE.json](EXECUTE.json); 5 smoke + 25 main |
| **M10** coverage + replay + handoff | **DONE** | Coverage FAIL; diagnostic REPLAY_PASS; this file + [VERIFICATION.json](VERIFICATION.json) |
| **Checkpoint D** | **DONE** | stop condition met |

## Prospective review gap (explicitly FAILED)

Independent M10 coverage reviewer `68919dae-61a9-4c39-80f7-5ad0845bbc03` (~2.98 min; no self-cert) found:

- `src/p22/eval/masked_atac_pilot.py` and `scripts/run_masked_atac_m9.py` were **absent** at M8 PASS `ff0f770` and Checkpoint C `2c3e85e`.
- Both were introduced and used for smoke learning in the **same** commit `315d6a9`.
- Neither file is in M8 `REQUIRED_LOCK_KEYS`. Live M8 wrapper digests still rematch; rematch does **not** authorize the new path.
- No M6/M8 independent-reviewer transcript covered the new files.

Therefore:

- `prospective_executor_review_gate` = **FAIL**
- `retrospective_path_inspection` = **PARTIAL** (cannot retroactively satisfy the prospective gate)
- `scientific_acceptance_of_M9` = **NOT_AUTHORIZED**

Historical M8 PASS for the locked wrapper/adapter/protocol helpers is preserved and not rewritten.

## Diagnostic numerical replay (no fitting)

Commands (worktree `PYTHONPATH`; exits 0):

```text
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python scripts/run_masked_atac_m10_replay.py
# → disposition REPLAY_PASS_DIAGNOSTIC_ONLY; counters preserved
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -m pytest -q \
  tests/test_masked_atac_*.py tests/test_masked_atac_m10_replay.py
# → 41 passed
```

Results:

- Pre-replay pins rematch (30 sidecars + ledger/counter); post-replay counter SHA unchanged `2b4bd43c…`.
- Independently recomputed donor-average cell log-loss matches stored sidecar values for 25 main + 5 smoke.
- Cross-arm cell/donor/label/target equality PASS on all five folds.
- Pooled TC−CA ≈ **+0.00154** (30 donors); fixed-prediction bootstrap 95% CI **[−0.00220, +0.00475]** (seed 601001); practical margin 0.01 → exploratory advantage **not met**.
- EXECUTE.json primary rematch PASS.
- Live artifact `du` ≈ **0.0121 GiB** (12 668 KiB); counter `artifacts_gib.used=0.0` is not a filesystem measurement.
- Fits this step: **0**. Counters remain 30/40 (smoke 5; scientific 25; failed 0).

## Scientific interpretation

This pilot asked a claim-level-2 question: under whole-target-chromosome ATAC masking, can RNA plus visible ATAC predict a training-only-selected binary accessibility target, and does CA improve donor-average cell log-loss over matched token-concat?

Diagnostic numbers do **not** meet the pre-fit exploratory advantage rule. More importantly, M9 execution used an unlocked real-data path introduced after M8/Checkpoint C, so those numbers **cannot** be promoted to scientific acceptance under the amended prospective-review rule. Valid closeout outcomes here are the recorded prospective-gate **FAIL**, diagnostic replay agreement, preserved counters, and unchanged prior INVALID/`B_NULL` labels — not a positive-result search or silent PASS.

## Raw / log paths

| Path | Role |
|---|---|
| `<worktree>/reports/generated/nn_masked_atac_pilot_20261001/` | Owned raw root |
| `…/predictions/` | 30 prediction sidecars (5 smoke + 25 main) |
| `…/attempt_counter.json` | Durable counters (SHA `2b4bd43c…`; unchanged by M10) |
| `…/attempt_ledger.jsonl` | 30 attempt records |
| `…/constant_arm_descriptive.json` | Zero-fit constant arm (folds 0–4) |
| `…/checkpoints/` / `…/logs/` | Empty at coverage audit (no separate checkpoint files retained) |

Absolute raw root: `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/masked-atac-20261001/reports/generated/nn_masked_atac_pilot_20261001`

## Cumulative resources (this stage)

| Cap | Used |
|---|---|
| Total attempts ≤40 | **30** (5 smoke + 25 main; 0 failed) |
| Fitting hours ≤6 | **≈0.00178** |
| Artifacts ≤4 GiB | **≈0.0121 GiB** live `du` (counter field 0.0) |
| Workers × torch threads | **1 × 2** (serial) |
| Package installs / push / merge / vault / packet / MOM edits | **None** |
| M10 fits / refits / counter resets | **None** |

## Accepted claims

- Claim-level-2 computational prediction scope was the correct ceiling for this stage.
- Prospective executor-review gate **FAIL** is a truthful blocker of scientific M9 acceptance.
- Diagnostic saved-prediction replay agrees with EXECUTE primary contrast; exploratory TC−CA advantage not met under frozen margin/bootstrap.
- Prior S10/S9/S7 `INVALID`, S8 `NO FIT`, primary `B_NULL`, Q2 `ENDPOINT_UNRESOLVED` unchanged.
- Chromosome-mask / mixed-label donor-average cell-log-loss protocol contracts remain the right estimand framing for any future locked re-run.

## Rejected / not authorized

- Scientific PASS or method validation of M9 under the unlocked `masked_atac_pilot` path.
- Biological state, causal modality routing, or external validation claims.
- Relabeling prior INVALID / NO FIT / B_NULL / ENDPOINT_UNRESOLVED.
- New learning, refits, target/seed/model sweeps, or counter resets during M10.
- Push, merge, vault/MOM/sent-packet edits, or professor email.

## One next action

**Stop.** Do not search for a positive result. Any future scientific claim on this masked-ATAC estimand requires a **new** independent pre-fit hash lock that includes the real-data execution path (`masked_atac_pilot.py` / runner) before fits — retrospective inspection of the current sidecars cannot authorize PASS. Separate remaining research tracks (independent cell-state endpoint; F4 bounded-null paper) stay outside this closed M0–M10 loop.

## Checkpoint D

Stop condition met: M10 coverage audit finished with prospective gap **explicitly FAILED**; saved-prediction replay finished with counters preserved; HANDOFF/VERIFICATION committed with claim limits and one next action. Independent safe work for this amended plan is exhausted.

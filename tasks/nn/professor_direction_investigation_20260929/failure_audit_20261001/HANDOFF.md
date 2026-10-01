# R10 — Verified closeout → scientific `INVALID` (complete)

**Date:** 2026-10-01.  
**Scientific result for selected experiment:** **`INVALID`** (`S10_corrected_null_pairing_use_20261001`).  
**Not claimed:** method validation, biological `A_ADVANTAGE`, pairing-use as a published method result, NeMO acquisition, or overturn of immutable S9 `INVALID`.

Machine-readable verification: [VERIFICATION.json](VERIFICATION.json).  
R9 report: [EXECUTE.md](EXECUTE.md); [execute.json](execute.json).

## Identity

| Item | Value |
|---|---|
| Worktree | `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-engineering-20260928-gnhf-worktrees/read-tasks-nn-finish-ee2202-gnhf-worktrees/read-users-anuragdan-b61180-gnhf-worktrees/execute-the-p22-data-146414-gnhf-worktrees/execute-p22-s-failur-d8f02c` |
| Branch | `gnhf/execute-p22-s-failur-d8f02c` |
| Integration base | `67245a2b19de9d6fb094fc01190590d9362d6d43` (`codex/p22-failure-audit-base-20261001`) |
| Tip before R10 write | `faf67a24c7acab45de1da7f2f093e80a4bcc0599` (R8 / Checkpoint C) |
| GNHF run | `execute-p22-s-failur-d8f02c` |
| Interpreter | `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python` with `PYTHONPATH=<worktree>/src` |
| `p22.__file__` | `<worktree>/src/p22/__init__.py` |

Professor sources remain original July 2 / July 21 vault MOM. Prior S9 `INVALID`, S7-v1/v2 `INVALID`, prior S8 `NO FIT`, and primary `B_NULL` are preserved. Worker recommendations are not professor records.

## Task dispositions (R0–R10)

| Task | Disposition | Evidence |
|---|---|---|
| **R0** provenance | **DONE** (`PASS`) | [PREFLIGHT.md](PREFLIGHT.md) |
| **R1** S9 replay | **DONE** (`REPLAY_PASS`) | [S9_AUDIT.md](S9_AUDIT.md); [s9_audit.json](s9_audit.json) |
| **R2** null diagnosis | **DONE** (`NULL_AUDIT_PASS`) | [NULL_AUDIT.md](NULL_AUDIT.md); [null_audit.json](null_audit.json) |
| **Checkpoint A** | **DONE** | [CHECKPOINT_A.md](CHECKPOINT_A.md) |
| **R3** execution audit | **DONE** (`EXECUTION_AUDIT_PASS`) | [EXECUTION_AUDIT.md](EXECUTION_AUDIT.md); 12/12 diagnostic fits |
| **R4** guidance/claims | **DONE** (`GUIDANCE_CLAIMS_PASS`) | [GUIDANCE_AND_CLAIMS.md](GUIDANCE_AND_CLAIMS.md); independent review PASS |
| **R5** task/data options | **DONE** (`TASK_DATA_OPTIONS_BOUNDED`) | [TASK_DATA_OPTIONS.md](TASK_DATA_OPTIONS.md); NeMO role PRESERVED |
| **Checkpoint B** | **DONE** | [CHECKPOINT_B.md](CHECKPOINT_B.md) |
| **R6** decision | **DONE** (`EXPERIMENT_SELECTED`) | [DECISION.md](DECISION.md); [BUDGET_LEDGER.md](BUDGET_LEDGER.md) |
| **R7** protocol/implement | **DONE** (`PROTOCOL_FROZEN` + `IMPLEMENT_PASS`) | [S10_PROTOCOL.md](S10_PROTOCOL.md); [IMPLEMENT.md](IMPLEMENT.md) |
| **R8** independent review | **DONE** (`PASS`) | [INDEPENDENT_REVIEW_R8.md](INDEPENDENT_REVIEW_R8.md); agent `fd860419-c20a-4e11-8c6f-f56ddc15fdec` |
| **Checkpoint C** | **DONE** (`PASS`) | [CHECKPOINT_C.md](CHECKPOINT_C.md); authorized 49≤90 under R8 hashes |
| **R9** bounded experiment | **DONE** (`INVALID`) | [EXECUTE.md](EXECUTE.md); [execute.json](execute.json); skip-fits replay of 49 saved fits |
| **R10** verified handoff | **DONE** (this file) | [VERIFICATION.json](VERIFICATION.json) |
| **Checkpoint D** | **DONE** | stop condition met |

## Scientific interpretation

This failure audit asked whether prior S9 `INVALID` was driven by a broken null, execution interference, claim/endpoint mis-scoping, or dataset inadequacy — then ran at most one discriminating claim-1 experiment.

Read-only findings established: exact ρ=0 orthogonalization breaks within-donor ATAC shuffle exchangeability (R2); concurrent RNG race path exists but tiny diagnostic showed `NO_DIVERGENCE_OBSERVED_UNDER_SPEC` (R3); Q2 `ENDPOINT_UNRESOLVED` blocks claim-L4 biology only (R4); no dataset change from null alone and NeMO external role preserved (R5). Selected experiment `S10_corrected_null_pairing_use_20261001` repaired the null to independent Gaussians without orthogonalization; R8 independently locked the serial executor.

Authorized serial batch completed **49/49** (0 failed). Closeout used **saved-sidecar replay only** (`--skip-fits`); attempt counters were not incremented. Disposition **`INVALID`**: at ρ=1, unimodal marginal BA fails the ≤0.60 gate (`logreg_rna` ≈0.333 PASS; `logreg_atac` 0.625 FAIL). Under the corrected null, ρ=0 pairing gate is **`PAIRING_NEGATIVE`** — supporting that S9’s ρ=0 `PAIRING_POSITIVE` is explained by broken orthogonal-null exchangeability rather than requiring a leak claim from that alone. CA ρ=1 is also `PAIRING_NEGATIVE`. Neither pairing label is a method claim.

Primary remains **`B_NULL`**. S9 remains immutable **`INVALID`**. S7-v1/v2 remain **`INVALID`**. Prior S8 remains **`NO FIT`**. Power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`. A finished **`INVALID`** corrected-null control plus precise remaining blockers is a complete answer for this ordered task; do not continue searching for a positive result.

## Raw / log paths

| Path | Role |
|---|---|
| `<worktree>/reports/generated/nn_failure_audit_20261001/` | Stage raw root (attempt_counter; R1–R5 ledgers) |
| `<worktree>/reports/generated/nn_failure_audit_20261001/s10_corrected_null_pairing_20261001/` | S10 raw root (49 fits; 12 CA/TC checkpoints; 49 donor-prediction sidecars; attempt ledger) |
| `<worktree>/reports/generated/nn_failure_audit_20261001/s10_corrected_null_pairing_20261001/attempt_ledger.jsonl` | Durable attempt ledger |
| `<worktree>/reports/generated/nn_failure_audit_20261001/s10_corrected_null_pairing_20261001/checkpoints/` | Neural checkpoints with `initial_state_sha256` + `learning_history` |
| Prior S9 shared raw (read-only) | `…/execute-the-p22-data-146414/reports/generated/nn_s9_analytic_pairing_20260930/` |

Absolute S10 raw root: `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-engineering-20260928-gnhf-worktrees/read-tasks-nn-finish-ee2202-gnhf-worktrees/read-users-anuragdan-b61180-gnhf-worktrees/execute-the-p22-data-146414-gnhf-worktrees/execute-p22-s-failur-d8f02c/reports/generated/nn_failure_audit_20261001/s10_corrected_null_pairing_20261001`

## Cumulative resources (this stage)

| Cap | Used |
|---|---|
| Scientific fits ≤90 / ≤6 fitting hours / ≤4 GiB new artifacts | **49** / **~0.00074 h** / **~0.0034 GiB** |
| Diagnostic fits ≤12 | **12/12** (exhausted in R3; 0 remaining) |
| Generator-only draws ≤256 | **97** (R2 81 + R7 16) |
| Network metadata ≤32 MiB / 20 req; payloads ≤256 MiB | **~0.88 MiB / 20 req**; **0** payloads |
| Package installs / push / merge / vault / packet / MOM / outbound email | **None** |
| Workers × torch threads (R9) | **1 × 2** (serial) |

## Reviewed hashes (Checkpoint C / R9; unchanged)

| Artifact | SHA-256 |
|---|---|
| `S10_PROTOCOL.json` | `f16e503df4e4ba19029ddf06354b3c95aa1612a6ba0c49dbc2d891e8beb1798c` |
| `S10_SPLIT_MANIFEST.json` | `ec210b253386938a62047728992c094107e6e65f0169aa04ef7e59ff6b676ba6` |
| `S10_SEED_SCHEDULE.json` | `4ef154fe783db23aa0df09ba31d38e409a3efd2070cb581603a226b8b25c33ec` |
| `src/p22/eval/s10_analytic.py` | `5440d8cd42feb69c4c8f0e6416620315b6916dd2d980d655b8ff1b409ad3fb9e` |
| `src/p22/eval/s10_execute.py` | `2aed78eaf2f0e9ef9643acfad9ddc7a8e7d81afca35ac7e92ad426e012eefe77` |

## Accepted claims

- Primary advantage **not demonstrated** (`B_NULL`); study `STUDY_PARTIAL`; power `POWER_UNESTABLISHED`.
- Prior S9 analytic pairing-use control remains immutable **`INVALID`**.
- Selected S10 corrected-null control finished **`INVALID`** under frozen reviewed hashes; not a method claim.
- Under corrected null, ρ=0 pairing gate **`PAIRING_NEGATIVE`** supports exchangeability repair of the prior null defect (does not alone prove absence of all other failure modes).
- Q2 `ENDPOINT_UNRESOLVED` correctly continues to block claim-L4 biology.
- Prior S8 **`NO FIT`** and S7-v1/v2 **`INVALID`** unchanged.

## Rejected / not authorized

- Real-label / biological cell-state pilot without an independent endpoint.
- Full NeMO count-package download or out-of-budget acquisition.
- Redesigning or refitting S9/S10 to chase a positive result after `INVALID`.
- Weakening marginal/null gates to make the batch look valid.
- Promoting RNA-derived clusters or N16 scores to independent cell-state truth.
- Dataset change inferred from null alone.
- Push, merge, vault/MOM/sent-packet edits, or professor email.
- New fits during R9/R10 closeout (replay only).

## What the experiment ruled out / what remains unidentified

**Ruled in / supported:** S9’s ρ=0 `PAIRING_POSITIVE` is consistent with the R2 exchangeability break; under the corrected independent-Gaussian null the ρ=0 gate holds (`PAIRING_NEGATIVE`).

**Ruled out as a completed method claim:** CA ρ=1 pairing-positive under the corrected null with marginal PASS (observed ρ=1 `PAIRING_NEGATIVE` and marginal FAIL via `logreg_atac` 0.625).

**Still unidentified / blocked:** independent cell-state endpoint for claim-L4; whether further representation/optimization work under a new reviewed protocol is warranted after this INVALID; confirmatory external NeMO evaluation (role preserved, not acquired).

## Remaining blockers (outside this GNHF stop)

1. **Precise biological blocker:** no independently measured cell-state/maturation endpoint orthogonal to NN RNA inputs (`ENDPOINT_UNRESOLVED`).
2. Any future pairing-use protocol needs a new scientifically justified ID/null/joint rule and fresh independent review — not outcome-guided rescue of S9/S10.
3. Local branch only — not pushed or merged.

## One smallest next action

Obtain or define an independently measured cell-state/maturation endpoint orthogonal to NN RNA inputs before any biological pilot; otherwise write the already-framed F4 bounded null/detectability paper from immutable gates (including this S10 `INVALID` and the established S9 null-exchangeability defect). Do not search for a positive S10 redesign.

## Stop

**COMPLETE — R0–R10 evidence-backed dispositions; Checkpoint D met.** Selected experiment `INVALID`; independent safe work exhausted; attempt counters preserved on replay. GNHF stop condition satisfied. Do not continue searching for a positive result.

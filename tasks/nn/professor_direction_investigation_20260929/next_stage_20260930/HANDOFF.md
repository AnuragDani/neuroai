# Q12 — Verified closeout → scientific `INVALID` (complete)

**Date:** 2026-10-01.  
**Scientific result for selected experiment:** **`INVALID`** (`S9_analytic_pairing_use_synthetic_20260930`).  
**Biological pilot:** **`BLOCKED`** (Q2 `ENDPOINT_UNRESOLVED`).  
**Not claimed:** method validation, biological `A_ADVANTAGE`, pairing-use as a published method result, or NeMO acquisition.

Machine-readable verification: [VERIFICATION.json](VERIFICATION.json).

## Identity

| Item | Value |
|---|---|
| Worktree | `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-engineering-20260928-gnhf-worktrees/read-tasks-nn-finish-ee2202-gnhf-worktrees/read-users-anuragdan-b61180-gnhf-worktrees/execute-the-p22-data-146414` |
| Branch | `gnhf/execute-the-p22-data-146414` |
| Integration base | `04282f0a803cc40c5d40aa0a9a7c535a213e1560` (`codex/p22-data-driven-base-20260930`) |
| Tip before Q12 write | `d685124085e4c245b2bfa54f5fe00447a645f198` (Q10 commit) |
| GNHF run | `execute-the-p22-data-146414` |
| Interpreter | `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python` with `PYTHONPATH=<worktree>/src` |
| `p22.__file__` | `<worktree>/src/p22/__init__.py` |

Professor sources remain original July 2 / July 21 vault MOM. Prior continuation `NO FIT` (S8 chance-null) and S7-v1/v2 `INVALID` are preserved. Worker recommendations are not professor records.

## Task dispositions (Q0–Q12)

| Task | Disposition | Evidence |
|---|---|---|
| **Q0** provenance | **DONE** (`PASS`) | [PREFLIGHT.md](PREFLIGHT.md) |
| **Q1** diagnostic replay | **DONE** (`PASS`) | [REPLAY.md](REPLAY.md); fresh root `reports/generated/nn_next_stage_q1_replay_20260930/` |
| **Q2** endpoint audit | **DONE** (`ENDPOINT_UNRESOLVED`) | [ENDPOINTS.md](ENDPOINTS.md); [endpoint_inventory.json](endpoint_inventory.json) |
| **Q3** regulatory coverage | **DONE** (`REGULATORY_ADEQUACY_UNRESOLVED`; structural `STRUCTURAL_COVERAGE_PASS`) | [REGULATORY_COVERAGE.md](REGULATORY_COVERAGE.md); [regulatory_coverage.json](regulatory_coverage.json) |
| **Checkpoint A** | **DONE** | Q1–Q3; unresolved endpoint cannot unlock biological fits |
| **Q4** sampling / eligibility | **DONE** (`SUPPORT_REPAIR_PASS`; `ELIGIBILITY_FROZEN`) | [SAMPLING_FEASIBILITY.md](SAMPLING_FEASIBILITY.md); [sampling_feasibility.json](sampling_feasibility.json) |
| **Q5** external feasibility | **DONE** (`EXTERNAL_FEASIBILITY_BOUNDED`; confirmatory `UNRESOLVED`) | [EXTERNAL_FEASIBILITY.md](EXTERNAL_FEASIBILITY.md); [external_feasibility.json](external_feasibility.json) |
| **Checkpoint B** | **DONE** | Q4–Q5; null does not imply dataset defect |
| **Q6** research decision | **DONE** (`EXPERIMENT_SELECTED`; fit arithmetic `PASS`) | [RESEARCH_DECISION.md](RESEARCH_DECISION.md); [FIT_LEDGER.json](FIT_LEDGER.json); S8 exact-Bernoulli correction retained; prior S8 `NO FIT` |
| **Q7** protocol freeze | **DONE** (`PROTOCOL_FROZEN`) | [SYNTHETIC_PROTOCOL.md](SYNTHETIC_PROTOCOL.md); [SYNTHETIC_PROTOCOL.json](SYNTHETIC_PROTOCOL.json); [SPLIT_MANIFEST.json](SPLIT_MANIFEST.json) |
| **Q8** implement | **DONE** (`IMPLEMENT_PASS`) | [IMPLEMENT.md](IMPLEMENT.md); [implement.json](implement.json); `src/p22/eval/s9_analytic.py` |
| **Q9** independent review | **DONE** (`PASS`) | [NO_FIT_REVIEW.json](NO_FIT_REVIEW.json); [INDEPENDENT_REVIEW_Q9.md](INDEPENDENT_REVIEW_Q9.md); Task agent `393c27bd-2487-49eb-8225-ddd76b74ec4a` |
| **Checkpoint C** | **DONE** (`PASS`) | [CHECKPOINT_C.md](CHECKPOINT_C.md); authorized 49≤60 under reviewed hashes |
| **Q10** synthetic batch | **DONE** (`INVALID`) | [EXECUTE.md](EXECUTE.md); [execute.json](execute.json); raw root below |
| **Q11a** real pilot protocol | **BLOCKED** | Q2 `ENDPOINT_UNRESOLVED` (+ Q3/Q5 unresolved); Q10 `INVALID` does not unlock |
| **Q11b** runner adaptation | **BLOCKED** | with Q11a |
| **Q11c** bounded pilot | **BLOCKED** | with Q11a; 0 real-pilot fits |
| **Q12** verified handoff | **DONE** (this file) | [VERIFICATION.json](VERIFICATION.json) |
| **Checkpoint D** | **DONE** | stop condition met |

## Scientific interpretation

This continuation asked whether data/measurement/support/external gates plus one discriminating synthetic control could unlock a justified next experiment after primary `B_NULL`, S7 `INVALID`, and prior S8 `NO FIT`.

Read-only gates established: no independent cell-state endpoint orthogonal to NN RNA (`ENDPOINT_UNRESOLVED`); ATAC panels are structurally measured but regulatory adequacy unresolved; targeted sampling repairs rare-type support without establishing biological power; NeMO remains confirmatory-unresolved under the public-metadata budget. The single selected experiment was analytic pairing-use software control `S9_analytic_pairing_use_synthetic_20260930` (49≤60 fits; fitted ρ=0 pairing-plant null; independent review PASS; Checkpoint C authorized).

Authorized batch completed **49/49**. Disposition **`INVALID`**: at ρ=1, unimodal marginal BA fails the ≤0.60 gate (`logreg_rna` 0.75; `logreg_atac` ≈0.708), so pairing-only interpretation is refused. Secondary: fitted ρ=0 null yielded `PAIRING_POSITIVE` and ρ=1 CA pairing was `PAIRING_NEGATIVE` — neither is a method claim. Replay from saved donor-prediction sidecars (`--skip-fits`) reproduces gates without refit. Q11 biological pilot remains blocked by the unresolved endpoint.

Primary remains **`B_NULL`**. S7-v1/v2 remain **`INVALID`**. Prior S8 remains **`NO FIT`**. Power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`. A finished **`INVALID`** control plus precise biological blocker is a complete answer for this ordered task; do not continue searching for a positive result.

## Raw / log paths

| Path | Role |
|---|---|
| `<worktree>/reports/generated/nn_s9_analytic_pairing_20260930/` | S9 raw root (49 fits; 12 CA/TC checkpoints; 49 donor-prediction sidecars; attempt ledger) |
| `<worktree>/reports/generated/nn_s9_analytic_pairing_20260930/logs/` | Fit logs |
| `<worktree>/reports/generated/nn_s9_analytic_pairing_20260930/attempt_ledger.jsonl` | Durable attempt ledger |
| `<worktree>/reports/generated/nn_next_stage_q1_replay_20260930/` | Q1 fresh diagnostic replay |
| `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v3/` | Canonical real ladder (shared read-only) |
| `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_20260929/` | S7-v1 durable (immutable) |
| `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929/` | S7-v2 durable (immutable) |

Absolute S9 raw root: `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-engineering-20260928-gnhf-worktrees/read-tasks-nn-finish-ee2202-gnhf-worktrees/read-users-anuragdan-b61180-gnhf-worktrees/execute-the-p22-data-146414/reports/generated/nn_s9_analytic_pairing_20260930`

## Cumulative resources (this continuation)

| Cap | Used |
|---|---|
| Synthetic fits ≤60 / ≤4 fitting hours / ≤2 GiB new artifacts | **49** / **~0.00145 h** / **~0.0034 GiB** |
| Whole continuation ≤180 fits / ≤12 h / ≤4 GiB | **49** / **~0.00145 h** / **~0.0034 GiB** |
| Real pilot ≤120 further fits | **0** (blocked) |
| Network bytes (Q5 budget) | **0** new |
| Package installs / push / merge / vault / packet / MOM / outbound email | **None** |
| Workers × torch threads | **2 × 2** |

## Reviewed hashes (Checkpoint C / Q10; unchanged)

| Artifact | SHA-256 |
|---|---|
| `SYNTHETIC_PROTOCOL.json` | `eedf5e77c4ba08d8a801609e5a2bdfccc5d882e2d297d9469c4af364ad25ec7a` |
| `SPLIT_MANIFEST.json` | `2d9a3b9fac7bfd8dd48b7517e0ad22e297eab9a4e9f775ac814dd99b8c50fd4d` |
| `FIT_LEDGER.json` | `841c8468b6b17a43628d14af00f277ffb156b774264fe1dad0545b2ab5cd3563` |
| `src/p22/eval/s9_analytic.py` | `dad126cd6dc33e9e8226b9924baa7c0b0fd3e88f8b413a6b06c9313c06d4ea02` |

## Accepted claims

- Primary advantage **not demonstrated** (`B_NULL`); study `STUDY_PARTIAL`; power `POWER_UNESTABLISHED`.
- Selected S9 analytic pairing-use control finished **`INVALID`** under frozen reviewed hashes; not a method claim.
- Q11 biological pilot correctly **BLOCKED** by `ENDPOINT_UNRESOLVED`.
- Prior S8 **`NO FIT`** and S7-v1/v2 **`INVALID`** unchanged.
- Exact S8 Bernoulli boundary correction retained; mechanism-mismatch rejection retained.

## Rejected / not authorized

- Real-label / biological cell-state pilot without an independent endpoint.
- Full NeMO count-package download or out-of-budget acquisition.
- Redesigning or refitting S9 to chase a positive result after `INVALID`.
- Weakening marginal/null gates to make the batch look valid.
- Promoting RNA-derived clusters or N16 scores to independent cell-state truth.
- Push, merge, vault/MOM/sent-packet edits, or professor email.

## Remaining blockers (outside this GNHF stop)

1. **Precise biological blocker:** no independently measured cell-state/maturation endpoint orthogonal to NN RNA inputs (`ENDPOINT_UNRESOLVED`); also `REGULATORY_ADEQUACY_UNRESOLVED` and external confirmatory `UNRESOLVED`.
2. Any future pairing-use protocol needs a new scientifically justified ID/null/joint rule and fresh independent review — not outcome-guided rescue of S9.
3. Local branch only — not pushed or merged.

## One smallest next action

Obtain or define an independently measured cell-state/maturation endpoint orthogonal to NN RNA inputs before any biological pilot; otherwise write the already-framed F4 bounded null/detectability paper from immutable gates. Do not search for a positive S9 redesign.

## Stop

**COMPLETE — Q0–Q12 evidence-backed dispositions; Checkpoint D met.** Selected experiment `INVALID`; Q11 blocked; independent safe work exhausted. GNHF stop condition satisfied. Do not continue searching for a positive result.

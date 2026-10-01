# DECISION — R6 cause ranking and one next experiment

**Disposition:** `EXPERIMENT_SELECTED`  
**Fit feasibility:** `PASS`  
**Date:** 2026-10-01  
**Branch:** `gnhf/execute-p22-s-failur-d8f02c`  
**Dependencies:** R2 `NULL_AUDIT_PASS`; R3 `EXECUTION_AUDIT_PASS`; R5 `TASK_DATA_OPTIONS_BOUNDED`; Checkpoint B DONE.  
**Machine records:** [decision.json](decision.json); [BUDGET_LEDGER.md](BUDGET_LEDGER.md); [budget_ledger.json](budget_ledger.json).

No research fits, no payload downloads, no package installs, no vault/MOM/sent-packet edits in R6. Scientific labels retained: S9 `INVALID`; primary `B_NULL`; Q2 `ENDPOINT_UNRESOLVED`; study `STUDY_PARTIAL`. Prior S9 INVALID remains immutable; this decision does not rescue or re-label it.

## A. Cause ranking (by evidence strength)

Explicit partition: **null invalidity** vs **learned-model inadequacy** vs **dataset/task inadequacy**.

| Rank | Cause class | Finding | Evidence strength | What would change this conclusion |
|---|---|---|---|---|
| 1 | **Null invalidity** (software design) | Frozen ρ=0 exact orthogonalization places planted (z,w) on measure-zero {w⊥z}; within-donor ATAC shuffle is **not exchangeable**. Orig max \|product mean\| ~1.73e-16 vs shuffled mean abs ~0.1465. ρ=0 `PAIRING_POSITIVE` is consistent with this broken null. | **ESTABLISHED** (R2 analytic + 81 generator draws) | An exchangeable ρ=0 generator that still yields ρ=0 pairing CI lower >0 after complete coverage would move cause toward leak/optimization rather than null design. |
| 2 | **Missing provenance / review coverage** | Q10 executor `s9_execute.py` outside Q9 `REVIEWED_HASHES`; checkpoints lack epoch/learning history. | **ESTABLISHED process gap** (R1); **LOW as causal claim for INVALID** | Independent full-path review of actual executor + learning histories on a new protocol would close the process gap without overturning historical INVALID. |
| 3 | **Uncertain optimization** | Five-second fit totals and state_dict-only checkpoints cannot establish under-training or adequate learning. | **PARTIAL** (R1) | Persisted epoch/learning histories with initial-state hashes on the next experiment would allow discrimination. |
| 4 | **Concurrent RNG / ledger accounting** | ThreadPoolExecutor × process-global `set_all_seeds` code path exists; tiny R3 diagnostic: `NO_DIVERGENCE_OBSERVED_UNDER_SPEC`. No per-job attempt reserve; hours post-hoc. | **CODE PATH EXISTS; EFFECT UNCONFIRMED** at S9 scale (R3) | Confirmed serial-vs-thread divergence on a reviewed larger diagnostic, or mid-batch hours breach, would elevate this; absent that, serial default is precautionary. |
| 5 | **Finite-sample unimodal BA / leak inference** | Marginal BA 0.75/≈0.708 at n=24; Hypergeometric P(BA≥0.75)≈0.020. One positive 95% null CI is not proof of leak. | **UNRESOLVED; leak not established** | Valid exchangeable null + repeated independent draws (not bootstrap of one saved vector) required before leak claims. |
| 6 | **Learned-model inadequacy (architecture)** | No measured architecture defect requiring rewrite; primary ladder remains `B_NULL` under a separate biological estimand. | **NOT ESTABLISHED** as S9 INVALID cause | Persistent ρ=0 INVALID under a corrected exchangeable null with adequate optimization provenance would reopen model/optimization investigation. |
| 7 | **Dataset inadequacy** | Structural paired matrices PASS; rare-type support repaired (Q4). Dataset change from DS null / S9 INVALID alone is **forbidden**. No public candidate ready for ≤256 MiB predictive ingestion; NeMO ~1.4G role PRESERVED. | **NOT ESTABLISHED** as S9 cause; **ingestion blocked** for new public payloads | A measured limitation addressed by a feasible pinned ≤256 MiB object (or costed larger proposal) could justify dataset change — null result alone cannot. |
| 8 | **Task/endpoint inadequacy (claim-4 biology)** | Q2 `ENDPOINT_UNRESOLVED` blocks independent cell-state biology only (R4). | **ESTABLISHED blocker for L4 only** | Orthogonal wet-lab/state assay unlocks claim-4; does not change claim-1 software ranking. |

## B. Selected experiment (exactly one)

| Field | Value |
|---|---|
| **ID** | `S10_corrected_null_pairing_use_20261001` |
| **Kind** | `corrected_software_null_reproducibility_test` |
| **Claim level** | **1** (software / mechanism control) |
| **Route** | Corrected software null / reproducibility test — **not** claim-2 pilot, **not** new-dataset ingestion |
| **Null basis** | R2 candidate `independent_gaussian_rho0_within_donor_shuffle_20261001`: centre-scaled independent Gaussians targeting ρ=0 **without** exact orthogonalization; within-donor ATAC shuffle remains exchangeable under this construction (diagnostic product-mean shuffle/original ratio ≈1.003) |
| **Estimand** | CA donor log-loss drop under within-donor ATAC shuffle at planted ρ=1, with ρ=0 exchangeable fitted null gate (CI lower ≤0 required for VALID); unimodal marginal BA gate retained |
| **Arms (planned)** | Same seven equally supervised arms as S9: `cross_attention`, `token_concat`, `rna_atac_concat`, `gated_fusion`, `logreg_concat`, `logreg_rna`, `logreg_atac` |
| **Coverage arithmetic** | smoke 7 + screen ρ=0 (7×3) + screen ρ=1 (7×3) = **49** attempted scientific fits ≤ **90** |
| **Execution** | Serial neural worker (`workers=1`); ≤2 torch threads; no ThreadPoolExecutor scientific dispatch unless a later reviewed diagnostic proves isolation |
| **Acquisition** | **0** new payloads; synthetic generator only |
| **Raw root** | New worktree-owned path under `reports/generated/nn_failure_audit_20261001/` (exact subdir frozen in R7) |
| **Forbidden** | S9 rescue; seed shopping; outcome-driven threshold change; biology upgrade; NeMO development use |

### Smallest useful result (declared before outcomes)

Complete 49-fit coverage under the corrected exchangeable null with:

1. **VALID ρ=0 null gate** (pairing CI lower ≤0) — establishes that the prior ρ=0 `PAIRING_POSITIVE` is explained by the broken orthogonal null rather than requiring a leak claim; and/or  
2. **ρ=1 PAIRING_POSITIVE** with marginal gate PASS — establishes that CA can detect planted pairing under the corrected generator.

Either alone is scientifically useful. **INVALID** under the corrected null is also useful: it moves cause beyond null exchangeability. Fit feasibility is **not** established power. Effect assumption: planted ρ controls within-cell covariance only; unimodal planted channels remain label-blind by construction.

### Result that would change direction after this experiment

| Outcome | Next direction |
|---|---|
| VALID ρ=0 + ρ=1 PAIRING_POSITIVE + marginal PASS | Software control repaired; claim-2 masked ATAC pilot becomes eligible for a **later** stage (not combined here) |
| VALID ρ=0 + ρ=1 PAIRING_NEGATIVE | Representation/optimization under corrected null — not dataset change |
| INVALID ρ=0 under corrected null | Optimization/leak/implementation beyond exchangeability; escalate provenance + serial accounting before new data |
| INCOMPLETE / resource breach | Precise NO FIT; no seed restart |

## C. Rejected alternatives (not selected)

| Alternative | Why rejected now |
|---|---|
| Claim-2 `current_paired_masked_atac_from_rna_20261001` | Feasible (R5) but addresses a **different** estimand; does not resolve the established null-invalidity that invalidated S9. Deferred — not combined with the selected experiment. |
| Bounded new-dataset ingestion (NeMO / GSE280175 / GSE204684) | No candidate ready within 256 MiB; NeMO role PRESERVED; dataset change forbidden from null alone; GSE280175 lacks ATAC; GSE204684 lacks DS design. |
| Biological cell-state pilot | Q2 `ENDPOINT_UNRESOLVED` (claim-L4 blocked). |
| S9 relaunch / widen gates / seed search | PLAN forbids; prior INVALID immutable. |
| Paper-only closeout as this experiment | PLAN: do not choose paper-only by default. |
| Runner rewrite for unconfirmed RNG race | R3: no confirmed divergence; serial default sufficient precaution for R7–R9. |

## D. Cross-references (every claim → evidence)

| Claim in this decision | Evidence |
|---|---|
| Exact orthogonality breaks shuffle exchangeability | [NULL_AUDIT.md](NULL_AUDIT.md); [null_audit.json](null_audit.json); [NULL_INVARIANCE_DIAGNOSTIC.json](NULL_INVARIANCE_DIAGNOSTIC.json) |
| Candidate independent-Gaussian null | null_audit `candidate_null.id` |
| No confirmed thread divergence under tiny spec | [EXECUTION_AUDIT.md](EXECUTION_AUDIT.md); R3 diagnostic results |
| Claim hierarchy; Q2 = L4 only | [GUIDANCE_AND_CLAIMS.md](GUIDANCE_AND_CLAIMS.md) |
| Claim-2 feasible; no public ingestion ready; NeMO preserved | [TASK_DATA_OPTIONS.md](TASK_DATA_OPTIONS.md) |
| July guidance: discriminating multimodal + concat baseline | R4 G7 (Jul 21 [14:02]–[17:39]); not a biology unlock |
| S9 structure 49 = 7+21+21 | Prior [SYNTHETIC_PROTOCOL.md](../next_stage_20260930/SYNTHETIC_PROTOCOL.md) |

## E. Acceptance checklist (R6)

| Requirement | Status |
|---|---|
| Rank causes by evidence; distinguish null / model / dataset-task | PASS (section A) |
| State what new evidence would change conclusions | PASS (section A column; section B outcomes) |
| Select exactly one next experiment | PASS (`S10_corrected_null_pairing_use_20261001`) |
| Exact fit/download/resource arithmetic within budgets | PASS ([BUDGET_LEDGER.md](BUDGET_LEDGER.md)) |
| Expected inference limitations declared | PASS (section B) |
| Effect assumptions + smallest useful result before outcomes | PASS (section B) |
| No fits / payloads in R6 | PASS |

## Next

R7: freeze separate protocol JSON/Markdown and minimal generator repair (independent-Gaussian ρ=0 path; no orthogonalize); focused leakage/exchangeability tests; serial executor defaults; no scientific fits until R8 PASS.

# Q6 — Research decision (one discriminating experiment)

**Disposition:** `EXPERIMENT_SELECTED`  
**Fit feasibility:** `PASS`  
**Date:** 2026-09-30  
**Branch:** `gnhf/execute-the-p22-data-146414`  
**Dependencies:** Q2–Q5 complete; Checkpoint B accepted. No fits, downloads, or package installs.

Machine-readable: [research_decision.json](research_decision.json); [FIT_LEDGER.json](FIT_LEDGER.json).

## Bottleneck ranking

| Bottleneck | Rank | Summary |
|---|---|---|
| `task_endpoint` | `established` | No independently measured cell-state/maturation endpoint orthogonal to NN RNA inputs. |
| `implementation_optimization_control` | `established` | S7-v1/v2 INVALID and prior S8 NO FIT leave pairing-use / fitted-null software control unresolved; July 21 discriminating multimodal benchmark vs concat remains open. |
| `sampling_support` | `plausible_resolved_for_support` | Targeted sampling restores rare-type support; eligibility frozen; not every-fold feasible for MIC/OPC. |
| `atac_regulatory_coverage` | `plausible_structural_unknown_regulatory` | Structural 25-panel coverage PASS; regulatory adequacy unresolved without element catalog. |
| `donor_count_power` | `established_limit_unknown_cause` | 30 donors / 15+15 limits replication; cell count ≠ donor count; power unestablished. |
| `external_confirmatory` | `unknown_unresolved` | NeMO confirmatory evaluation unresolved (QC/specimen/feature); role preserved. |

Unresolved flags retained for later stages: `ENDPOINT_UNRESOLVED`, `REGULATORY_ADEQUACY_UNRESOLVED`, `EXTERNAL_FEASIBILITY_BOUNDED/confirmatory UNRESOLVED`, `POWER_UNESTABLISHED`.

## S8 numerical correction (exact vs rounded)

Prior continuation DECISION illustrated a Bernoulli-0.5 central 95% BA band as ≈`[0.326, 0.674]`. Exact recomputation (10k draws, seed 0, 16/14 labels) yields:

| Quantity | Value |
|---|---|
| Exact central 95% | `[0.3258928571428572, 0.6741071428571428]` |
| Rounded to 3 d.p. | `[0.326, 0.674]` |
| `gated_fusion` exact pooled BA | `0.3258928571428572` |
| Equals exact lower quantile? | **True** |
| Inside exact band? | **True** |
| Inside rounded 3 d.p. band? | **False** |

Rounded endpoints [0.326, 0.674] incorrectly exclude gated_fusion exact BA 0.32589285714285715, which sits exactly on the Bernoulli 2.5% quantile 0.32589285714285715. Exact band classification must be used.

| Arm | Exact pooled ρ=0 BA | Inside exact band | Inside rounded 3 d.p. |
|---|---:|---|---|
| `cross_attention` | 0.357142857143 | True | True |
| `token_concat` | 0.330357142857 | True | True |
| `rna_atac_concat` | 0.357142857143 | True | True |
| `gated_fusion` | 0.325892857143 | True | False |
| `logreg_concat` | 0.388392857143 | True | True |
| `logreg_rna` | 0.357142857143 | True | True |
| `logreg_atac` | 0.441964285714 | True | True |

**Retained:** chance/Bernoulli predictors remain an invalid fitted-model null (mechanism mismatch). Prior S8 **`NO FIT`** unchanged. Primary **`B_NULL`**; S7-v1/v2 **`INVALID`** unchanged.

**Illustrative claim with exact values:** Under the exact Bernoulli central 95% band, every S7-v2 rho=0 pooled BA (including token_concat and gated_fusion) falls inside. Adopting that chance band after seeing the frozen [0.35,0.65] failures remains an outcome-guided relaxation. Mechanism mismatch alone still rejects chance predictors as a fitted-model null.

## Chosen experiment

- **ID:** `S9_analytic_pairing_use_synthetic_20260930`
- **Kind:** `analytic_synthetic_pairing_use_software_control`
- **Plan / professor refs:** PLAN D3 / Q6–Q7; July 21 MOM 14:02–17:39 discriminating multimodal benchmark + concat baseline; 03:40 stratified/donor sampling already audited in Q4
- **Fit candidate:** `selected_pairing_use_fitted_plant_null` at **49** attempted fits (cap 60)
- **Result that would change direction:** PAIRING_POSITIVE under valid rho=0 null + oracle PASS would support that the CA implementation can use planted within-cell pairing on this generator/budget; PAIRING_NEGATIVE / oracle-fail / INVALID would direct repair of representation/optimization before new disease data or pilots.
- **Still unidentified:** Biological cell-state endpoint (Q2 ENDPOINT_UNRESOLVED); Regulatory-element adequacy (Q3 REGULATORY_ADEQUACY_UNRESOLVED); NeMO confirmatory QC/specimen/feature (Q5 UNRESOLVED); Biological power / min_detectable_delta (POWER_UNESTABLISHED)

## Rejected alternatives

- **biological_cell_state_pilot**: Q2 ENDPOINT_UNRESOLVED; Checkpoint A forbids unlocking biological cell-state fits
- **targeted_sampling_full_ladder_rerun**: Q4 repaired support but endpoint/power gates fail; PLAN forbids full-ladder rerun merely for more cells
- **atac_regulatory_representation_pilot**: Q3 regulatory adequacy unresolved; structural coverage PASS does not authorize a biological regulatory claim; endpoint still unresolved
- **external_nemo_acquisition_or_predictive_eval**: Q5 confirmatory UNRESOLVED; payload ~1.54 GiB out of budget; NeMO evaluation role PRESERVED
- **relaunch_rejected_s8_chance_null**: Prior NO FIT preserved; chance-null mechanism mismatch retained after exact-band correction; budget 119>60
- **new_real_label_ca_advantage_same_30_donors**: Primary already B_NULL; POWER_UNESTABLISHED; between-model gap small vs practical_margin
- **paper_only_closeout_as_this_experiments_destination**: Bounded null paper remains valid later writing path but is not the predetermined destination of Q0–Q12

## Fit / resource ledger

| Candidate | Status | Attempts | Reason |
|---|---|---:|---|
| `rejected_s8_chance_null_relaunch` | `REJECT` | 119 | Prior S8 draft smoke14+screen105=119>60; chance/Bernoulli BA band is mechanism-mismatched for fitted seven-arm pooled BA (exact-band correction does not rehabilitate it). |
| `s7_shaped_5fold_3rho_7arm` | `REJECT` | 119 | Smoke14+screen105 exceeds synthetic cap 60 before any new calibration. |
| `decision_5fold_2rho_7arm_plus_smoke` | `REJECT` | 77 | 7 arms × 5 folds × 2 rho = 70 plus smoke 7 = 77 > 60. |
| `fitted_ba_montecarlo_joint_calibration` | `DESIGN_UNRESOLVED` | 280 | R≥20 independent complete-pipeline null replicates for a joint seven-arm fitted BA critical value at even 2 folds is ≥280 fits, far above 60. Do not shrink joint calibration or relax thresholds to unlock fits. |
| `selected_pairing_use_fitted_plant_null` | `SELECT` | 49 | 49 ≤ 60 attempts with seven equally supervised arms, fitted rho=0 pairing null matching the tested pairing mechanism, and no chance-predictor BA calibration. |

Selected design uses F=3 × 7 arms × ρ∈{0,1} (smoke 7 + screen 42 = 49 ≤ 60). Fitted-mechanism null is the **ρ=0 pairing plant** under the same training pipeline — not a chance BA band. Fitted BA Monte Carlo joint calibration remains `fitted_ba_montecarlo_joint_calibration` and is not selected.

## Scientific invariants (unchanged)

Primary `B_NULL`; S7-v1/v2 `INVALID`; prior S8 `NO FIT`; power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`.

## Next

Q7 may freeze `SYNTHETIC_PROTOCOL` for `S9_analytic_pairing_use_synthetic_20260930` with exact seeds, generator equations, oracle, and the pairing-plant null above. No fits until Checkpoint C.

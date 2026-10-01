# BUDGET_LEDGER — R6 selected experiment resource arithmetic

**Date:** 2026-10-01  
**Experiment:** `S10_corrected_null_pairing_use_20261001`  
**Machine record:** [budget_ledger.json](budget_ledger.json)  
**Counter source:** `reports/generated/nn_failure_audit_20261001/attempt_counter.json`

R6 itself uses **0** scientific fits, **0** diagnostic fits, **0** payloads. Figures below are the **prospective** R7–R9 budget for the selected experiment against remaining stage caps.

## Cumulative stage usage (before R7)

| Resource | Used | Cap | Remaining |
|---|---:|---:|---:|
| Generator-only draws | 81 | 256 | 175 |
| Diagnostic fit attempts | 12 | 12 | **0** |
| Scientific fit attempts | 0 | 90 | 90 |
| Fitting hours | ~0.00022 | 6.0 | ~5.999 |
| Artifact GiB | 0.0 | 4.0 | 4.0 |
| Network metadata (R5 ledger) | 927209 B / 20 req | 32 MiB / 20 | exhausted for metadata budget this stage |
| Network payloads | 0 | 256 MiB | 256 MiB |

## Selected experiment planned consumption

| Item | Value | Notes |
|---|---|---|
| Smoke fits | 7 | One per arm; **counts as scientific** (diagnostic allowance exhausted) |
| Screen ρ=0 | 21 | 7 arms × 3 folds |
| Screen ρ=1 | 21 | 7 arms × 3 folds |
| **Total planned scientific fits** | **49** | 7+21+21; ≤90; headroom 41 |
| Diagnostic fits for this experiment | **0** | Cap already 12/12; no new diagnostic allowance |
| Additional generator draws (R7 null checks) | ≤64 recommended | Within remaining 175; preregistered seeds only |
| Workers × torch threads | **1 × 2** | Serial scientific default |
| Fitting hours (planned upper) | ≤6.0 | Historical S9 ≈0.0015 h on similar 49-fit path; not a power claim |
| New artifacts | ≤4.0 GiB | Fresh raw root; refuse overwrite of old shared S9 |
| Payload acquisition | **0 MiB** | Synthetic corrected null; no public download |
| NeMO / GEO matrices | **not acquired** | Costed larger-download proposal only if a later stage selects dataset change |

## Fit feasibility

| Check | Result |
|---|---|
| 49 ≤ 90 scientific remaining | **PASS** |
| 0 ≤ 0 diagnostic remaining | **PASS** (no diagnostic needed for selected path) |
| 0 MiB ≤ 256 MiB payload | **PASS** |
| Serial workers=1 within PLAN default | **PASS** |
| Claim-4 biology / dataset change | **N/A / rejected** |

**Fit feasibility:** `PASS` for the selected software-null experiment. Fit feasibility is **not** established statistical power.

## Concrete missing measurement (if selected route had been dataset)

If R6 had required new public multimodal DS data within this stage, the concrete missing resource would be: a pinned NeMO (or alternate) ATAC+RNA object **≤256 MiB** with resolved QC/specimen/feature contracts — current NeMO ATAC counts package remains ~1.4G. That is a **costed larger-download proposal**, not this experiment.

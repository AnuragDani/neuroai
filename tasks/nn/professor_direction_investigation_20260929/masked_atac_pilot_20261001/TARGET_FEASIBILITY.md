# Masked ATAC pilot M2 — target feasibility

**Disposition:** `TARGET_FEASIBILITY_PASS`
**Date:** 2026-10-01
**Claim level:** 2 (computational prediction of measured accessibility presence; not biological state, causal mechanism, or external validation)

## Preserved labels

- Primary: `B_NULL`
- S7/S9/S10: `INVALID` / `INVALID` / `INVALID`
- S8: `NO FIT`
- Q2: `ENDPOINT_UNRESOLVED`

## Binary target rationale

- Definition: 1 if exact-region unique_fragment_overlap count > 0 else 0
- Why useful: Binary presence reuses two-class heads, stays a measured computational estimand under chromosome masking, and supports a fair CA-vs-token-concat comparison without claiming regulatory function or reconstructing count magnitude.
- Imbalance: Union-region accessibility is sparse (typical inner-train prevalence well below 0.5); eligibility requires both classes at cell and donor support minima; ranking prefers closest to balanced prevalence among eligible regions.
- Estimand unit is the **training-only selection algorithm**, not one fixed genomic locus.

## Eligibility and ranking (frozen before outer-test labels)

- Criteria: `{"min_pos_cells": 100, "min_neg_cells": 100, "min_pos_donors": 8, "min_neg_donors": 8, "min_both_class_donors": 4}`
- Ranking: minimize |inner_train_prevalence - 0.5|; then maximize count_depth_sum; then sha256('p22-masked-atac-target-rank-v1' + '\n' + region_label); then region_label
- Inner split: label-free sha256('p22-masked-atac-inner-val-v1' + '\n' + donor); first 8 -> inner_val; remaining 16 -> inner_train
- Inner-split status: provisional for M2 feasibility; M3 freezes the pilot inner-validation partition. If M3 adopts the same salt/rule, targets remain; if M3 changes the carve, re-run this frozen algorithm before fits (no outcome-driven redesign).
- Forbidden: outer-test labels/prevalence, CA performance, disease separation, author_cell_type features.

## Per-fold selection

- Folds with target: **5/5**
- Unique targets: **2** (`fold_to_fold_target_varies=True`)
- Selected labels: chr19:6424686-6425606, chr3:93470145-93471055

| Fold | Target | Chrom | Inner-train prevalence | Pos/Neg cells | Both-class donors | Visible ATAC | Eligible |
|---:|---|---|---:|---:|---:|---:|---:|
| 0 | `chr19:6424686-6425606` | chr19 | 0.3368 | 42794/84248 | 16 | 423 | 461 |
| 1 | `chr3:93470145-93471055` | chr3 | 0.6597 | 85186/43937 | 16 | 440 | 460 |
| 2 | `chr3:93470145-93471055` | chr3 | 0.6505 | 99371/53387 | 16 | 440 | 460 |
| 3 | `chr3:93470145-93471055` | chr3 | 0.6726 | 91325/44459 | 16 | 440 | 460 |
| 4 | `chr3:93470145-93471055` | chr3 | 0.6685 | 92128/45690 | 16 | 440 | 460 |

## Checks

- Input hashes: **True**
- Chromosome-mask exclusivity: **True**
- Outer-test excluded from inner-train: **True**
- Disease absent from ranking: **True**

## What this does / does not authorize

Allowed next: M3 freeze of donor/inner-val/cell/feature manifests using these targets if the same inner carve is adopted; Continue independent safe feasibility without fits

Not authorized: Model fitting or neural smoke learning; Single-locus performance claims; Relabeling Q2/S9/S10/primary B_NULL; Using outer-test prevalence to drop targets; Strict inner-train-only historical 256-panel provenance

No fits were run.

# Masked ATAC pilot M4 — leakage and metric falsification

**Disposition:** `FALSIFICATION_PASS`
**Date:** 2026-10-01
**Claim level:** 2 (computational prediction of measured accessibility presence; not biological state, causal mechanism, or external validation)

## Preserved labels

- Primary: `B_NULL`
- S7/S9/S10: `INVALID` / `INVALID` / `INVALID`
- S8: `NO FIT`
- Q2: `ENDPOINT_UNRESOLVED`

## Metric contract (no fits)

- Binary target: 1 if exact-region unique_fragment_overlap count > 0 else 0
- Primary aggregation: equal mean across donors of within-donor mean cell binary log-loss
- Probability clip: `1e-15`
- Mixed cell labels within donor: **allowed**
- Donor-average probability as primary: **forbidden**
- Fake donor disease class: **forbidden**

### Hand-calculated mixed-label example

- Unequal cells (A=3, B=1); donor A mixed labels
- Expected donor-average cell log-loss: `0.270278741684`
- Got: `0.270278741684`
- Wrong log-loss(donor-mode-y, donor-mean-p): `0.406716673217` (differs from correct `0.270278741684`)

### Oracle / constant direction

- Oracle near-zero: **True** (value `1e-06`)
- Constant p=0.5 equals ln(2): **True**
- Oracle better than constant: **True**

## Leakage contract

- Mask: whole target chromosome excluded from ATAC input
- Fit statistics: ATAC TF/IDF/panel depth fit on visible regions and train rows only
- Target-count perturbation leaves RNA + visible ATAC fit stats unchanged: **True**
- Target-inclusive panel depth path refused: `target_inclusive_nCount_or_panel_depth` (toy demo shows visible TF changes under that wrong path)
- Forbidden feature fields: `disease`, `donor_id`, `group`, `nCount_ATAC`, `nFeature_ATAC`, `nucleosome_signal`, `TSS.enrichment`, `target_count`, `target_region_index`, `target_chrom`, `gene_activity_all_regions`

## Adapter requirements

- Existing MIL assumption: p22.training.mil_loop._donor_label_map refuses any donor with mixed cell labels; disease bags assume one label per donor
- Required adapter: donor-average of within-donor mean cell-target binary log-loss (equal donor weighting); do not substitute donor-average probability or invent a fake donor disease class
- Live mixed-label refusal: **True** (`donor 'D0' carries both labels`)
- Preserve classification API: **True**

## M3 frozen-fold mask recheck

- M3 disposition: `SPLITS_AND_SAMPLING_FROZEN`
- Folds checked: **5**; all chromosome-exclusive: **True**

## Checks

- `hand_calculated_metric_match`: **True**
- `wrong_donor_avg_prob_differs`: **True**
- `oracle_better_than_constant`: **True**
- `oracle_near_zero`: **True**
- `constant_equals_ln2`: **True**
- `mil_mixed_label_refused`: **True**
- `target_perturbation_invariant`: **True**
- `target_inclusive_depth_leaks`: **True**
- `chromosome_mask_exclusivity_ok`: **True**
- `chromosome_mask_leak_refused`: **True**
- `forbidden_features_detected`: **True**
- `allowed_features_clean`: **True**
- `feature_order_hash_sensitive`: **True**
- `prediction_reload_identity`: **True**
- `prediction_reload_detects_drift`: **True**
- `output_overwrite_refused`: **True**
- `m3_chromosome_mask_exclusivity`: **True**
- `m3_disposition_frozen`: **True**

## Guards

- Feature-order hash sensitive to permutation: **True**
- Prediction reload identity: **True**
- Output overwrite refused: **True**

## What this does / does not authorize

Allowed next: Checkpoint B after leakage/metric fixtures pass; M5 estimand/statistical/resource protocol freeze; Continue independent safe feasibility without fits

Not authorized: Model fitting or neural smoke learning; Reusing mil_loop donor-label bags for mixed cell targets without adapter; Donor-average probability or fake disease class as primary estimand; Target-inclusive ATAC depth/QC/IDF/latent inputs; Relabeling Q2/S9/S10/primary B_NULL

No fits were run.

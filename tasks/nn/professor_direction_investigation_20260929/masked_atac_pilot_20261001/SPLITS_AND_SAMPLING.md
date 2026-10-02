# Masked ATAC pilot M3 — splits and sampling freeze

**Disposition:** `SPLITS_AND_SAMPLING_FROZEN`
**Date:** 2026-10-01
**Claim level:** 2 (computational prediction of measured accessibility presence; not biological state, causal mechanism, or external validation)

## Preserved labels

- Primary: `B_NULL`
- S7/S9/S10: `INVALID` / `INVALID` / `INVALID`
- S8: `NO FIT`
- Q2: `ENDPOINT_UNRESOLVED`

## Outer donor folds (archival repeat-0)

- Source: `configs/atac_tiebreak_region_sets_2026-09-21.json per_fold`
- Repeat / split_seed: `0` / `0`
- Folds: **5**; each of 30 donors held out exactly once as outer-test
- All-donors SHA-256: `069be9dcc44e317d07ec202a7db582a70dd92f68ba315eb007c107e81f1bbca9`
- Disease stratification: disclosed archival provenance; **not** a model feature (`disease_as_model_feature=False`)

## Inner validation (FROZEN; matches M2)

- Status: `FROZEN`
- Rule: label-free sha256('p22-masked-atac-inner-val-v1' + '\n' + donor); first 8 -> inner_val; remaining 16 -> inner_train
- Matches M2: **True** (Same salt/rule as M2 provisional carve; adopted as FROZEN so M2 targets remain valid without re-selection.)

## Matched paired sampling

- Sampler: `p22.data.nn_sampling.sample_donor_stratified_cells`
- Cap / seed: **256** / **22**
- Strata: `['author_cell_type', 'library']` (RNA-derived type is stratum only)
- Label-free / disease consulted: **True** / **False**
- Cells selected: **7680** across **30** donors (0 below cap)
- Global cell-ID SHA-256: `9ace24c200672ee9b26027f2dafa4e7f9421848498961f8f8d886d94d90eef1a`
- Matched across arms: **True** (One global donor×type×library sample; every arm and fold reuses the same per-donor cell IDs)

## Per-fold pins

| Fold | Target | Chrom | Visible ATAC | Train/Val/Test cells | Test-cell SHA-256 |
|---:|---|---|---:|---:|---|
| 0 | `chr19:6424686-6425606` | chr19 | 423 | 4096/2048/1536 | `8d98f4d04e4f…` |
| 1 | `chr3:93470145-93471055` | chr3 | 440 | 4096/2048/1536 | `69d7edcacd07…` |
| 2 | `chr3:93470145-93471055` | chr3 | 440 | 4096/2048/1536 | `467677570f36…` |
| 3 | `chr3:93470145-93471055` | chr3 | 440 | 4096/2048/1536 | `3f4496e411b5…` |
| 4 | `chr3:93470145-93471055` | chr3 | 440 | 4096/2048/1536 | `f0b3d4565973…` |

## Class-dependent metrics policy

If a partition lacks both target classes, report secondary class-dependent metrics (AUROC/BA) as unavailable; do not drop donors or targets. Log-loss remains defined.

## Checks

- Input hashes: **True**
- Each donor once as outer-test: **True**
- Inner matches M2: **True**
- Chromosome-mask exclusivity: **True**
- Donor partitions disjoint: **True**
- Matched cells across arms: **True**
- No disease as feature: **True**

## What this does / does not authorize

Allowed next: M4 leakage/metric falsification using these frozen manifests; Checkpoint A after M1–M3 evidence check; Continue independent safe feasibility without fits

Not authorized: Model fitting or neural smoke learning; Disease/donor/author_cell_type as model features; Dropping donors for missing secondary class metrics; Relabeling Q2/S9/S10/primary B_NULL; Changing cap/seed/inner carve without re-freezing targets

No fits were run.

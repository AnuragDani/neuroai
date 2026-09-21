# Development ATAC matrix and real paired pilot

Date: 2026-09-21 · Run: `p22-results-executio-debda8` · Status: **pilot executed**

This records the first real paired RNA+ATAC execution for the development cohort.
Both artifacts below are `experimental result`; the scientific contrast is a
**pilot** (one fold, one initialization seed) and not a final estimate.

## 1. Frozen training-fold region set

The development cohort's per-library cellranger-arc peaks share no common exact
intervals (B10C1Q ∩ B17C2L = 0). The accepted protocol therefore needs a frozen
common region set. This run freezes the **exact-interval union of the training
libraries' peaks** for one predeclared donor-aware fold and selects the top 256
by training-library prevalence.

- Split plan: `iter_repeated_stratified_group_folds`, `n_repeats=5`, `n_folds=5`,
  `split_seed=0`; pilot uses repeat 0, fold 0 → 24 train / 6 test donors,
  28 training libraries.
- Union size: **1,440,187** exact intervals; selected **256**; prevalence max 6/28.
- Selection rule: top-N by training-library prevalence, ties by (chrom, start, end).
- Provenance: per-library GEO `features.tsv.gz` SHA-256 recorded in the region
  record; peaks are called per library from fragments, so discovery uses no
  disease labels and no held-out donors.
- Files: `configs/development_region_set_fold0_2026-09-21.json`,
  `configs/development_region_set_fold0_2026-09-21.bed`
  (`regions_sha256 = 192d0b7aebdfe5b71a5d65fba0001ebe0c102c3675b48752fc3f7a662330456b`).

Limitation (`inference`): `prevalence_max = 6/28` and the string tie-break bias
toward chr1 (193/256 selected). The feature set is mechanically valid but
biologically weak; the final protocol must re-freeze a better region set
prospectively before final fitting.

## 2. Real ATAC count matrix

Bounded remote tabix queries over the open CELLxGENE fragment
(`46b43994-…-fragment.tsv.bgz`, index SHA-256 in `docs/atac_development_matrix_2026-09-21.json`)
recovered the measured counts for the frozen regions.

- Shape **256 × 248,998**, `int64`, `nnz = 4,879,858`, min 1, max 4074.
- Count unit `fragment_overlap_sum`.
- **All 256 regions joined with zero unknown barcodes** (`join_complete` 256/256).
- Per-region nonzero cells: min 292, median 17,066, max 159,410.
- Per-cell nonzero regions: median 14, max 134; 3,967/248,998 cells have zero
  nonzero regions (a measured zero, not imputation).
- Network cost: **1.779 GB** fetched (median 6.55 MB/region, 25 requests/region);
  zero whole-asset bytes, no persistent fragment copy.
- Matrix SHA-256 `b1b7e9e3df01519310f4e7a3f73577acc55e53db8effed113d06b6ceb285c307`
  (gitignored run artifact; shape/hash recorded in tracked evidence).

Evidence: `docs/atac_development_matrix_2026-09-21.json`,
`docs/atac_development_matrix_regions_2026-09-21.tsv`.

## 3. Real paired pilot

`scripts/run_real_paired_pilot.py` consumed the local CELLxGENE RNA H5AD `X`
(35,477 genes) and the 256-region ATAC matrix on the **same cells**, sampled to
256 cells/donor (7,680 cells over 30 donors), and trained the six neural families
on one donor-isolated fold (train 4,096 / val 2,048 / test 1,536 cells).

| Model | Params | Donor balanced accuracy |
|---|---:|---:|
| rna_only | 4,690 | 0.625 |
| atac_only | 4,690 | 0.500 |
| rna_atac_concat | 9,378 | 0.625 |
| gated_fusion | 10,468 | 0.625 |
| token_concat | 12,546 | 0.625 |
| cross_attention | 13,634 | 0.625 |
| majority control | — | 0.500 |

Primary contrast — cross-attention minus matched token-concat donor-level
balanced accuracy: **0.0**, bootstrap interval [0.0, 0.0] (6 test donors,
910/1000 valid resamples), practical margin 0.5, `advantage_demonstrated=false`.

This is an honest null pilot: the six-family stack ingests real paired data,
splits donors, fits, and writes artifacts; it does **not** demonstrate an
attention advantage. Resources: 9.2 s elapsed, 1.14 GB peak RSS.

Evidence: `docs/real_paired_pilot_2026-09-21.json` (tracked summary),
`reports/generated/real_paired_pilot_20260921/run/run.json` (full per-model
predictions, splits, checkpoint hashes; SHA-256
`0e9f506939f0f82f…`).

## 4. What is verified vs proposed

- `verified` — region set is training-fold-only, exact-interval, label-independent.
- `verified` — ATAC matrix is a real measured count matrix on the pooled fragment
  with complete barcode joins; RNA/ATAC pairing is exact on the shared cells.
- `experimental result` — pilot donor-level scores above; cross-attention shows no
  advantage over token concat.
- `proposed` — final protocol: better frozen region set, accepted normalization,
  repeated donor splits, initialization sensitivity, faithfulness interventions.
- `unknown` — external cohort route (tar-packaged, per-file embargo) and whether
  the external paired counts MEX is usable.

## 5. Commands

```
# 1. freeze the region set (network: 29 small GEO features files)
.venv-p22/bin/python scripts/freeze_development_region_set.py \
  --features-dir reports/generated/development_region_set_20260921/features \
  --obs-h5ad <h5ad> --repeat 0 --fold 0 --n-repeats 5 --n-folds 5 --split-seed 0 \
  --top-n 256 --out reports/generated/development_region_set_20260921/region_set.json \
  --regions-file reports/generated/development_region_set_20260921/regions.bed

# 2. quantify the fragment (bounded remote tabix queries)
.venv-p22/bin/python scripts/quantify_development_atac.py \
  --regions-file reports/generated/development_region_set_20260921/regions.bed \
  --index-path reports/generated/development_region_set_20260921/fragment.tbi \
  --obs-h5ad <h5ad> --workers 12 \
  --counts-out reports/generated/development_region_set_20260921/counts \
  --out reports/generated/development_region_set_20260921/quantify.json

# 3. real paired pilot
.venv-p22/bin/python scripts/run_real_paired_pilot.py \
  --output-dir reports/generated/real_paired_pilot_20260921/run
```

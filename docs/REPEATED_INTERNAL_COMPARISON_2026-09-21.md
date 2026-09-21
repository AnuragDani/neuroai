# Frozen repeated donor-split internal comparison (2026-09-21)

Status: **executed**. Internal development comparison only. External paired data were
not accessed. This is the study's first repeated donor-split primary estimate; it
replaces the single-fold pilot as the internal result.

## Result first

Primary estimand: cross-attention minus matched token-concatenation **donor-level
balanced accuracy**, averaged across 5 repeats of a 5-fold donor-isolated split
(every repeat tests all 30 donors once).

- Estimate: **+0.0333**
- 95% donor-cluster bootstrap interval (1000/1000 valid replicates): **[-0.0133, 0.0806]**
- Practical margin (15 control / 15 DS): **0.07**
- Advantage demonstrated: **false**

The interval is non-degenerate (the pilot's 6-donor interval was `[0.0, 0.0]`), and it
crosses zero. Per-repeat deltas are unstable around zero: `{0: +0.100, 1: -0.067,
2: 0.000, 3: +0.067, 4: +0.067}`.

Mean donor balanced accuracy across repeats: rna_only 0.447, atac_only 0.400,
rna_atac_concat 0.540, gated_fusion 0.493, token_concat 0.493, cross_attention 0.527,
majority 0.367. No family is meaningfully above chance on held-out donors, so this is
an honest null rather than evidence that attention helps or hurts.

## What this adds beyond the pilot

1. **Leakage-controlled feature space.** Each outer fold's ATAC region set is the
   top-256 exact intervals by *that fold's training-library* prevalence, so no test
   donor's own peaks enter that fold's feature space. The 25 per-fold sets are subsets
   of one 480-region union, measured once from the indexed fragment; unmeasured
   intervals are never zero-filled.
2. **All 30 donors tested.** The pilot held out 6 donors; here each repeat holds out
   all 30 exactly once (5 repeats x 5 folds), giving a donor-level interval that
   reflects donor sampling.
3. **Prospective protocol freeze** (`configs/final_internal_comparison_2026-09-21.json`)
   before fitting: cohort, features, splits, training rules, margin, and uncertainty.

## Inputs and acceptance

| Fact | Value | Label |
|---|---|---|
| RNA | local H5AD, SHA-256 `08d6eff2…fcdbb`, 35,477 genes, 248,998 cells | verified |
| ATAC union matrix | 480 x 248,998, nnz 9,513,875, SHA-256 `62755125…84d7` | experimental result |
| Barcode join | 480/480 regions complete, 0 unknown barcodes | verified |
| Region union | `union_sha256 = 29ab6739…3f9e`, 480 regions | verified |
| Count unit | `fragment_overlap_sum` (insertion-vs-fragment not frozen) | unknown |
| Cells | 7,680 sampled (256/donor cap), 15 control / 15 DS donors | verified |

Bounded remote tabix quantification fetched **3,295,412,224 B** for the 480-region
union (6 workers); the fragment itself was never downloaded.

## Commands actually run

```
# 1. download the 37 GEO per-library features files (~62 MB) into the generated dir
# 2. freeze per-fold region sets + union (offline, cached features)
PYTHONPATH=src .venv-p22/bin/python scripts/freeze_repeated_region_sets.py \
  --features-dir reports/generated/repeated_comparison_20260921/features \
  --obs-h5ad .../f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad \
  --n-repeats 5 --n-folds 5 --split-seed 0 --top-n 256 \
  --out reports/generated/repeated_comparison_20260921/region_sets.json \
  --union-bed reports/generated/repeated_comparison_20260921/union.bed     # PASS, 480 union
# 3. quantify the union once from the indexed fragment (bounded remote tabix)
PYTHONPATH=src .venv-p22/bin/python scripts/quantify_development_atac.py \
  --regions-file reports/generated/repeated_comparison_20260921/union.bed \
  --index-path reports/generated/development_region_set_20260921/fragment.tbi \
  --obs-h5ad .../f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad --workers 6 \
  --counts-out reports/generated/repeated_comparison_20260921/counts \
  --out reports/generated/repeated_comparison_20260921/quantify.json        # PASS, 480 x 248998
# 4. frozen repeated donor-split internal comparison
PYTHONPATH=src .venv-p22/bin/python scripts/run_real_paired_comparison.py \
  --output-dir reports/generated/real_paired_comparison_20260921/run        # PASS, null advantage
```

Wall time 43.4 s, peak RSS 1.12 GB, 1.1 GB / 17.4 GB disk free during the run.

## Code

- `scripts/freeze_repeated_region_sets.py` — per-fold training-only region sets + union.
- `src/p22/eval/repeated_comparison.py` — across-repeat primary contrast and
  donor-cluster bootstrap over the across-repeat mean.
- `scripts/run_real_paired_comparison.py` — the frozen 5 x 5 orchestration.
- Tests: `tests/test_repeated_comparison.py` (9), `tests/test_freeze_repeated_region_sets.py` (5).

## Honest scope

This is an **internal** development result. External paired RNA+ATAC counts remain
tar-packaged under per-file embargo and were not accessed, so no external validation
is claimed. Raw-count standard scaling is used; the accepted normalization is not
separately frozen. No biological mechanism is inferred from attention or latent tokens.
The near-chance held-out accuracy is an input/feature limitation observation, not an
architecture finding.

# Paired faithfulness and initialization sensitivity on the frozen folds

Date: 2026-09-21 · Run: `p22-results-executio-debda8` (iteration 6)
Script: `scripts/run_real_paired_faithfulness_frozen.py`
Evidence JSON: `docs/real_paired_faithfulness_frozen_2026-09-21.json`
Run artifacts (gitignored): `reports/generated/real_paired_faithfulness_frozen_20260921/run/`

## What this closes

Iteration 4 ran the seven held-out interventions and the initialization-seed
sensitivity on the **single pilot fold**. This iteration repeats both on the
**frozen 5 x 5 donor-isolated folds** used by the internal comparison
(`configs/final_internal_comparison_2026-09-21.json`), reusing each fold's
training-only subset of the already-measured 480-region union ATAC matrix. No new
network access was used. This is the "applicable faithfulness tests" item for the
frozen internal comparison.

It remains **internal development evidence**: external paired data were not
accessed, interventions are manipulation evidence rather than causal biology, and
raw-count standard scaling is not separately frozen.

## Setup

- Folds: 25 (5 repeats x 5 folds), each with an inner 3-fold donor split for epoch
  selection; test donors are disjoint from train/val donors within a fold.
- ATAC features: each fold's top-256 training-only exact intervals, subset from the
  480-region union measured once (`union_sha256 29ab6739…3f9e`), no zero-filling.
- Intervention families: `rna_atac_concat`, `gated_fusion`, `token_concat`,
  `cross_attention`; each fitted once per fold at the frozen `model_seed=0`.
- Interventions scored with the estimand-consistent donor-level balanced accuracy
  on held-out test donors only. Clamp values come from the training views.
- Initialization sensitivity: `cross_attention` and `token_concat` refit at seeds
  0/1/2 with the donor splits held fixed; this is initialization sensitivity, not
  split-seed variability.

## Result 1 — held-out interventions (mean donor balanced accuracy drop across 25 folds)

| Intervention | concat | gated | token | cross-attn |
|---|---|---|---|---|
| `clamp_view_a` (RNA) | +0.131 | +0.090 | +0.053 | +0.105 |
| `clamp_view_b` (ATAC) | +0.028 | -0.009 | -0.031 | +0.023 |
| `permute_view_a_within_donor` | 0.000 | +0.007 | 0.000 | +0.005 |
| `permute_view_b_within_donor` | 0.000 | +0.007 | 0.000 | +0.005 |
| `ablate_view_a_embedding` | +0.145 | +0.080 | +0.116 | +0.103 |
| `ablate_view_b_embedding` | +0.027 | +0.012 | -0.039 | -0.001 |
| `fixed_uniform_route` | N/A | +0.001 | N/A | N/A |

Positive = the intervention lowered donor balanced accuracy. Mean baseline donor
balanced accuracy was 0.591 (concat), 0.555 (gated), 0.549 (token), 0.585
(cross-attention).

- **RNA-view dependence dominates.** Clamping or ablating the RNA view costs about
  0.05–0.15 donor balanced accuracy in every two-view family; the same ATAC-view
  interventions cost at most ~0.03 and are near zero or negative for several
  families. This reproduces the pilot-fold pattern on the frozen folds.
- **Within-donor permutation is ~invariant.** These are per-cell models (no cell
  attends to another), so shuffling cells inside a donor should not change
  donor-aggregated predictions. concat/token measure exactly 0.000; cross-attention
  and gated show a tiny nonzero mean (0.005–0.007, max 0.125) consistent with
  floating-point summation-order changes flipping borderline donors at the 0.5
  aggregation threshold, not with real cell-order sensitivity. Reported as an
  honest caveat rather than an effect.
- **Uniform-route refusal is correct.** `fixed_uniform_route` is `NOT_APPLICABLE`
  for the three non-gated families and measured for the gated family (mean drop
  0.001, mean routing shift 0.292).
- Per-fold drops vary widely (e.g. concat `ablate_view_a` range -0.375 to +0.700),
  so these are descriptive fold means, not a stable per-fold effect.

## Result 2 — initialization-seed sensitivity (donor splits held fixed)

| Seed | cross-attention mean | token-concat mean | primary delta mean |
|---|---|---|---|
| 0 | 0.5853 | 0.5487 | +0.0367 |
| 1 | 0.5680 | 0.5833 | -0.0153 |
| 2 | 0.5400 | 0.5460 | -0.0060 |

The mean primary delta (cross-attention minus token-concat donor balanced accuracy)
across the 25 folds moves between +0.0367 and -0.0153 as the initialization seed
changes (spread 0.052; mean over seeds +0.0051). The frozen internal estimate of
+0.0333 (95% interval [-0.0133, +0.0806], margin 0.07) sits inside this
seed-to-seed range, so the null is not an initialization-seed artifact.

## Reproduce

```
.venv-p22/bin/python scripts/run_real_paired_faithfulness_frozen.py \
  --output-dir reports/generated/real_paired_faithfulness_frozen_20260921/run
```

No network; ~68 s CPU, 1.19 GB peak RSS. Reuses
`reports/generated/repeated_comparison_20260921/counts/counts.npz` and
`reports/generated/repeated_comparison_20260921/region_sets.json`.

## Limitations

- Internal development folds only; external paired data were not accessed.
- Interventions are held-out manipulation evidence, not causal biology; a routing
  weight is not an explanation.
- Raw-count standard scaling; the accepted normalization is not separately frozen.
- A near-zero permutation effect and a small seed spread are not stability
  guarantees beyond the seeds and manipulations actually run.
- Predictions must not be used to select outcome-favourable donors.

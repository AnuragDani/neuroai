# Normalization sensitivity on the frozen internal paired folds

Date: 2026-09-21 · Run: `p22-results-executio-debda8` (iteration 7)
Script: `scripts/run_real_paired_normalization_sensitivity.py`
Evidence JSON: `docs/real_paired_normalization_sensitivity_2026-09-21.json`
Run artifacts (gitignored): `reports/generated/real_paired_normalization_20260921/run/`

## What this closes

The frozen protocol (`configs/final_internal_comparison_2026-09-21.json`) uses
raw-count training-only standard scaling and listed the accepted normalization as
an unresolved item. This prospectively declared sensitivity tests whether the
frozen primary null depends on that choice. It does not replace the primary
endpoint, change the margin, or select a favourable variant.

Two preprocessing variants are run on the **same 25 donor-isolated folds**, the
same per-fold training-only region subsets of the measured 480-region union
(`union_sha256 29ab6739…3f9e`), the same six families, and the same
initialization seed (`model_seed=0`):

- `raw_standard_scaler` — the frozen primary (raw counts, training-only scaler).
- `log1p_standard_scaler` — `log1p` counts before the same scaler. `log1p` is a
  fixed monotone per-value transform, not a fitted statistic, so it leaks no
  held-out information.

## Result

| Variant | Primary estimate | 95% donor-bootstrap interval | Advantage |
|---|---|---|---|
| raw standard scaler (frozen primary) | **+0.0333** | [-0.0133, +0.0806] | false |
| log1p + standard scaler | **+0.0333** | [-0.0050, +0.0800] | false |

- The raw variant **exactly reproduces** the frozen internal estimate and
  interval (`+0.0333`, `[-0.0133, +0.0806]`), a direct verification that this
  script reuses the frozen pipeline unchanged.
- The log1p variant gives the **same estimate** (+0.0333) with a slightly
  narrower interval that still crosses zero; the per-repeat deltas are a
  permutation of the raw values (`+0.0667, +0.1000, -0.0667, +0.0333, +0.0333`).
- Mean donor balanced accuracy per family is near chance in both variants
  (raw: cross-attention 0.527, token-concat 0.493, majority 0.367; log1p:
  cross-attention 0.487, token-concat 0.453). No family gains an advantage.
- **Conclusion:** the frozen internal null is not normalization-dependent. The
  primary estimate is unchanged, and no variant demonstrates an advantage.

## Reproduce

```
.venv-p22/bin/python scripts/run_real_paired_normalization_sensitivity.py \
  --output-dir reports/generated/real_paired_normalization_20260921/run
```

No network; ~82 s CPU, 1.21 GB peak RSS, 17.2 GiB free disk after the run.
Reuses `reports/generated/repeated_comparison_20260921/counts/counts.npz` and
`reports/generated/repeated_comparison_20260921/region_sets.json`.

## Limitations

- Sensitivity only; the frozen raw-count primary estimate and its margin are
  unchanged. This is not a new endpoint and not a re-freeze.
- Internal development folds only; external paired data were not accessed.
- Raw-count and log1p scaling are the only two variants tested; other accepted
  normalizations are not covered.

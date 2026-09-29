# chr21-forced sensitivity (ladder_v4)

Sensitivity only. Canonical primary remains `ladder_v3` `B_NULL`
(`docs/nn_v2/ladder_summary.json`). Amendment:
`configs/nn_protocol_v2_amendment_chr21forced.json` (`n_hvg` = HVG ∪ all chr21).

## Contrast (R3_ca − R3_tc, donor BA)

From `docs/nn_v2/v6/ladder_v4_summary.json`: estimate **0.060**, 95% CI
**[0.011, 0.113]**, margin 0.07, advantage false. Verifier
(`gnhf/verify_ladder.py`, no `--write`) **PASS**.

N10 labels → **`CHR21FORCED_D_SMALL_POSITIVE`** (CI lower > 0, estimate < 0.07).
Not `CHR21FORCED_A_ADVANTAGE` (needs estimate ≥ 0.07 and CI lower > 0), not
`CHR21FORCED_B_NULL` (CI excludes 0), not `CHR21FORCED_C_DISADVANTAGE`.

## Per-fold donor AUROC (mean over 25 folds)

Source: `docs/nn_v2/v6/chr21_forced_compare.json` (v3 vs v4).

| Arm | ladder_v3 | chr21-forced | Δ |
|---|---:|---:|---:|
| R3_ca | 0.656 | 0.780 | +0.124 |
| R3_tc | 0.658 | 0.816 | +0.158 |
| logreg_rna | 0.534 | 0.983 | +0.449 |
| logreg_concat | 0.497 | 0.980 | +0.482 |
| chr21_dosage | 1.000 | 1.000 | 0 |

## Reading

Forcing all 538 chr21 genes into the RNA view raises nearly every arm’s
per-fold AUROC (linear controls most). Absolute R3 performance improves, but
the CA−TC gap stays below the 0.07 advantage margin while excluding zero →
`CHR21FORCED_D_SMALL_POSITIVE`. Linear dosage features remain strongest.
Primary endpoint unchanged: report this as a sensitivity beside `ladder_v3`
`B_NULL`, do not retarget the headline.

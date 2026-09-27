# Ladder Summary

Outcome: B_NULL
Primary estimate: 0.0000

| Arm | BA | AUROC | Log-loss | Brier |
|---|---|---|---|---|
| R3_ca | 0.3333 | 0.2083 | 0.7702 | 0.2880 |
| R3_tc | 0.3333 | 0.3472 | 0.7256 | 0.2662 |

Artefact note: The pooled balanced-accuracy (mean_ba) for `majority` and other models might score around 0.353 instead of ~0.5. This artefact occurs because fold-wise training majorities flip under stratified folds, leading to misaligned predictions when pooled across folds. Mean per-fold balanced accuracy (`mean_per_fold_ba`) correctly handles this by calculating the metric per fold before averaging.

# Ladder Summary

Outcome: D_SMALL_POSITIVE
Primary estimate: 0.0600

| Arm | BA | AUROC | Log-loss | Brier |
|---|---|---|---|---|
| R0_ca | 0.6800 | 0.7778 | 0.5878 | 0.1999 |
| R0_tc | 0.6800 | 0.7644 | 0.5913 | 0.2015 |
| R1_ca | 0.6133 | 0.6729 | 0.7510 | 0.2438 |
| R1_tc | 0.6267 | 0.7031 | 0.7210 | 0.2375 |
| R2_ca | 0.5667 | 0.6640 | 0.6960 | 0.2448 |
| R2_tc | 0.5667 | 0.7333 | 0.6589 | 0.2328 |
| R3_ca | 0.4600 | 0.4720 | 0.7889 | 0.2827 |
| R3_gated | 0.4333 | 0.5200 | 0.8190 | 0.2822 |
| R3_tc | 0.4000 | 0.4516 | 0.7834 | 0.2829 |
| R3_tc_parammatched | 0.4533 | 0.5040 | 0.7732 | 0.2751 |
| R4_ca | 0.4733 | 0.4916 | 0.6978 | 0.2523 |
| R4_tc | 0.4600 | 0.4689 | 0.6963 | 0.2516 |
| chr21_dosage | 1.0000 | 1.0000 | 0.4324 | 0.1249 |
| latent_pca_lsi_head | 0.5667 | 0.6178 | 0.7314 | 0.2495 |
| logreg_concat | 0.8600 | 0.9351 | 0.5059 | 0.1611 |
| logreg_rna | 0.8467 | 0.9413 | 0.5021 | 0.1591 |
| majority | 0.3000 | 0.3000 | 25.2306 | 0.7000 |
| pseudobulk_rna_logistic | 0.6733 | 0.9120 | 0.5691 | 0.1925 |

Artefact note: The pooled balanced-accuracy (mean_ba) for `majority` and other models might score around 0.353 instead of ~0.5. This artefact occurs because fold-wise training majorities flip under stratified folds, leading to misaligned predictions when pooled across folds. Mean per-fold balanced accuracy (`mean_per_fold_ba`) correctly handles this by calculating the metric per fold before averaging.

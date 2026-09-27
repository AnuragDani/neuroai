# Ladder Summary

Outcome: B_NULL
Primary estimate: -0.0067

| Arm | BA | AUROC | Log-loss | Brier |
|---|---|---|---|---|
| R0_ca | 0.4600 | 0.3876 | 0.8576 | 0.3167 |
| R0_tc | 0.4800 | 0.4000 | 0.8665 | 0.3186 |
| R1_ca | 0.3333 | 0.3493 | 0.8319 | 0.3053 |
| R1_tc | 0.3533 | 0.3524 | 0.8281 | 0.3032 |
| R2_ca | 0.3533 | 0.3378 | 0.7970 | 0.2985 |
| R2_tc | 0.3733 | 0.3742 | 0.8003 | 0.2981 |
| R3_ca | 0.3733 | 0.3689 | 0.8693 | 0.2950 |
| R3_gated | 0.4600 | 0.4373 | 0.7758 | 0.2837 |
| R3_tc | 0.3800 | 0.3458 | 0.7707 | 0.2854 |
| R3_tc_parammatched | 0.3533 | 0.3147 | 0.7641 | 0.2835 |
| R4_ca | 0.4867 | 0.4720 | 0.6953 | 0.2511 |
| R4_tc | 0.4667 | 0.4880 | 0.6953 | 0.2511 |
| chr21_dosage | 0.9667 | 0.9982 | 0.4569 | 0.1376 |
| latent_pca_lsi_head | 0.3667 | 0.3689 | 0.8993 | 0.3099 |
| logreg_concat | 0.4733 | 0.3956 | 0.8591 | 0.3169 |
| logreg_rna | 0.4933 | 0.4089 | 0.8521 | 0.3132 |
| majority | 0.3533 | 0.3533 | 23.3082 | 0.6467 |
| pseudobulk_rna_logistic | 0.4467 | 0.5236 | 0.7475 | 0.2752 |

Artefact note: The pooled balanced-accuracy (mean_ba) for `majority` and other models might score around 0.353 instead of ~0.5. This artefact occurs because fold-wise training majorities flip under stratified folds, leading to misaligned predictions when pooled across folds. Mean per-fold balanced accuracy (`mean_per_fold_ba`) correctly handles this by calculating the metric per fold before averaging.

## chr21-excluded sensitivity (N11)

Holding the accepted ladder_v2 folds fixed and rerunning R3_ca, R3_tc, logreg_rna, and logreg_concat with chromosome-21 features dropped yields no-chr21 BA ≤ 0.55 for every arm (**DOSAGE_DOMINATED**). Details and source paths: `docs/nn_v2/chr21_excluded.json`, `docs/nn_v2/ROBUSTNESS.md`.

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

## Init/sampling-seed sensitivity (N12)

Fixed-protocol seed rerun under ladder_v2 widths (`seeds_v2/`, R3_ca params 384250): model-seed spread 0.020, sampling-seed spread 0.040. Outcome `B_NULL` → report spread only (`SPREAD_ONLY`); not `SAMPLING_SENSITIVE`. See `docs/nn_v2/seed_sensitivity.json` and `docs/nn_v2/ROBUSTNESS.md`.

## Faithfulness interventions (N13)

Held-out interventions on ladder_v2 fold models (R3_ca/R3_tc/R3_gated/R4_ca): NC Δ = 0 exact. Tags `CA_PAIRING_UNUSED` (I3 CI includes 0) and `ATAC_USED` (I1 log-loss CI excludes 0 on R3_tc and R3_gated). Attention knockout (I4), uniform MIL (I5), and gate clamps (I6) do not exclude 0. Planted PC not run (no saved S4/S5 models). Details: `docs/nn_v2/faithfulness.json`, `docs/nn_v2/FAITHFULNESS.md`.

## Nuisance-probe diagnostics (N14)

Held-out within-disease embedding probes on R1/R2/R3 (CA and TC): **R2_REJECTED** (`PROBE_DROP_INSUFFICIENT`; no `ADVERSARY_ERASES_SIGNAL`). Batch probe stays near chance (~0.05–0.06) and does not drop ≥ 5 points from R1 to R2; library probe is unscorable under donor hold-out. See `docs/nn_v2/nuisance_probe.json`, `docs/nn_v2/NUISANCE_PROBE.md`.

## Out-of-fold cell scores (N15)

Exported per-cell logits and MIL attention for R1_ca/R3_ca/R3_tc/R4_ca from ladder_v2 fold models (100 folds; every cell appears exactly 5 times per arm before averaging). Compact donor×cell-type means in `docs/nn_v2/donor_celltype_scores.csv.gz`. Full table: `reports/generated/nn_20260923/spectrum/cell_scores.csv.gz`. Evidence: `docs/nn_v2/cell_scores_export.json`, `docs/nn_v2/CELL_SCORES.md`. Chr21-excluded score export deferred.

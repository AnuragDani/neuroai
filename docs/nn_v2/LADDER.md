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

## Cell-state spectrum (N16)

Donor-mean R3_ca scores from the accepted N15 export: **SPECTRUM_NULL** (9 eligible types; no Holm-significant DS−CON difference). Support-floor exclusions include NEU_RELN/NEU_low/OPC (single-arm cell counts). Chr21-excluded score compare `NOT_NEEDED` (export deferred). Interpret-lane `SPECTRUM_LOCALIZED` from buggy/mixed-arm scores is superseded. Evidence: `docs/nn_v2/spectrum.json`, `docs/nn_v2/SPECTRUM.md`.

## Routing / attention (N17)

Per-cell-type descriptive readouts from ladder_v2 fold models (75 folds: R3_gated / R3_ca / R4_ca). All three readouts tagged **NOT_SHOWN_USED** because mapped N13 interventions I4 (CA / program-CA attention knockout) and I6 (gated route clamps) have Δ log-loss CIs that include 0. N13 `ATAC_USED` (I1) does not authorize attention/routing claims. Evidence: `docs/nn_v2/routing_attention.json`, `docs/nn_v2/ROUTING_ATTENTION.md`.

## Gene-activity secondary ladder (N21)

Secondary-only rerun under the decision-tree 500-gene amendment (`gene_activity_v2/`; primary remains N10 `B_NULL`). Outcome **GA_B_NULL**: GA_ca−GA_tc estimate 0.0533, CI [−0.0527, 0.1572] (includes 0; below practical margin). View-B gene-activity arms also null for R3_ca−R3_tc. GA_ca I1/I3/I4 faithfulness: NC exact zero; tags `GA_ATAC_UNUSED_OR_NULL`, `GA_CA_PAIRING_UNUSED`, `GA_ATTENTION_NOT_SHOWN_USED`. Never claim as independent external validation. Evidence: `docs/nn_v2/gene_activity_results.json`, `docs/nn_v2/GENE_ACTIVITY.md`.

## Results + unsent professor note (N22)

Written conclusion and D1–D13 coverage from verified JSON: `docs/nn_v2/NN_V2_RESULTS_2026-09-23.md`. Unsent note: `docs/nn_v2/PROFESSOR_NOTE_UNSENT.md`. Deferred experiments listed in `docs/nn_v2/FUTURE_WORK.md`.

## Final verification (N23)

Full suite `pytest -q -x` → **1188 passed**. Results top label **`NN_ASSIGNMENT_COMPLETE`** (claim limits retained: PC N/A; chr21 score export DEFERRED; N21 secondary). `gnhf/check_evidence.py` confirms verifier `primary_recomputed.ci` 3dp digits in the results doc. Paper phase N24–N34 remains.

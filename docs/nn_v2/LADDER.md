# Ladder Summary

Canonical run: `reports/generated/nn_20260923/ladder_v3` (v5 rebuild after shared-path control-fit fix; supersedes `ladder_v2` for primary claims).

Outcome: B_NULL
Primary estimate: 0.0267 (R3_ca − R3_tc; 95% CI includes 0; no complex-model advantage)

| Arm | BA | AUROC | Log-loss | Brier |
|---|---|---|---|---|
| R0_ca | 0.4733 | 0.3893 | 0.8567 | 0.3153 |
| R0_tc | 0.4867 | 0.3929 | 0.8668 | 0.3191 |
| R1_ca | 0.3467 | 0.3440 | 0.8323 | 0.3070 |
| R1_tc | 0.3400 | 0.3484 | 0.8287 | 0.3041 |
| R2_ca | 0.3867 | 0.3822 | 0.7931 | 0.2958 |
| R2_tc | 0.3533 | 0.3458 | 0.8113 | 0.3031 |
| R3_ca | 0.4000 | 0.3582 | 0.7465 | 0.2753 |
| R3_gated | 0.3667 | 0.3840 | 0.7477 | 0.2754 |
| R3_tc | 0.3733 | 0.3316 | 0.8306 | 0.3067 |
| R3_tc_parammatched | 0.3533 | 0.3396 | 0.8346 | 0.2940 |
| R4_ca | 0.5267 | 0.5147 | 0.6941 | 0.2505 |
| R4_tc | 0.5000 | 0.4427 | 0.6960 | 0.2514 |
| chr21_dosage | 1.0000 | 1.0000 | 0.4324 | 0.1249 |
| latent_pca_lsi_head | 0.3800 | 0.3787 | 0.9131 | 0.3125 |
| logreg_concat | 0.4133 | 0.3822 | 0.7693 | 0.2860 |
| logreg_rna | 0.4267 | 0.3982 | 0.7653 | 0.2840 |
| majority | 0.3000 | 0.3000 | 25.2306 | 0.7000 |
| pseudobulk_rna_logistic | 0.5133 | 0.5573 | 0.7387 | 0.2705 |

Artefact note: The pooled balanced-accuracy (mean_ba) for `majority` and other models might score around 0.30–0.35 instead of ~0.5. This artefact occurs because fold-wise training majorities flip under stratified folds, leading to misaligned predictions when pooled across folds. Mean per-fold balanced accuracy (`mean_per_fold_ba`) correctly handles this by calculating the metric per fold before averaging. See also `docs/nn_v2/v5/per_fold_metrics.json` and `docs/nn_v2/v5/BELOW_CHANCE.md`.

## v5 validity (V1–V4)

- **V1** per-fold metrics on canonical `ladder_v3`: majority BA exactly 0.5 every fold; learned-arm per-fold AUROC means remain near/above chance while pooled AUROC stays below chance (pooling artefact persists alongside the control-fit fix).
- **V2** positive control (forced chr21): logreg donor AUROC 0.924; shared-path fix = sklearn controls fit on full outer train.
- **V3** verdict `PIPELINE_BUG_FIXED` → mandatory V4 rebuild.
- **V4** this file / `ladder_summary.json` / `ladder_verification.json` regenerated from `ladder_v3` (`verify_ladder` PASS; still `B_NULL`).

## Downstream (P1 on ladder_v3)

N11 (`chr21_excluded_v3`), N12 (`seeds_v3`), N13 (`faithfulness_v3`), N14 (`nuisance_v3`), N15 (`spectrum_v3` cell-score export), and N16 (`SPECTRUM_NULL` + chr21 `COMPARED`) are done against `ladder_v3`. N17 still needs `_v3` analysis/publish on the new export.

## chr21-excluded sensitivity (N11)

Holding the canonical `ladder_v3` folds fixed and rerunning R3_ca, R3_tc, logreg_rna, and logreg_concat with chromosome-21 features dropped (`chr21_excluded_v3`, 100/100) yields no-chr21 BA ≤ 0.55 for every arm (**DOSAGE_DOMINATED**; R3_ca 0.333, R3_tc 0.373, logreg_rna 0.407, logreg_concat 0.400). Details: `docs/nn_v2/chr21_excluded.json`, `docs/nn_v2/ROBUSTNESS.md`.

## Init/sampling-seed sensitivity (N12)

Fixed-protocol seed rerun under ladder_v3 widths (`seeds_v3/`, R3_ca params 384250; m_0_s_22 reuses ladder_v3): model-seed spread 0.073, sampling-seed spread 0.033. Outcome `B_NULL` → report spread only (`SPREAD_ONLY`); not `SAMPLING_SENSITIVE`. See `docs/nn_v2/seed_sensitivity.json` and `docs/nn_v2/ROBUSTNESS.md`.

## Faithfulness interventions (N13)

Held-out interventions on ladder_v3 fold models (R3_ca/R3_tc/R3_gated/R4_ca): NC Δ = 0 exact. Tags `CA_PAIRING_UNUSED`, `ATAC_USED`. Attention knockout (I4), uniform MIL (I5), and gate clamps (I6) CIs that include 0 are not claimed as used. Planted PC not run (no saved S4/S5 models under ladder_v3). Details: `docs/nn_v2/faithfulness.json`, `docs/nn_v2/FAITHFULNESS.md`.

## Nuisance-probe diagnostics (N14)

Held-out within-disease embedding probes on ladder_v3 R1/R2/R3 (CA and TC): **R2_REJECTED** (`PROBE_DROP_INSUFFICIENT`). Batch probe stays near chance and does not drop ≥ 5 points from R1 to R2; library probe is unscorable under donor hold-out. See `docs/nn_v2/nuisance_probe.json`, `docs/nn_v2/NUISANCE_PROBE.md`.

## Out-of-fold cell scores (N15)

Exported per-cell logits and MIL attention for R1_ca, R3_ca, R3_tc, R4_ca from ladder_v3 fold models (100 folds; every cell appears exactly 5 times per arm before averaging). Compact donor×cell-type means in `docs/nn_v2/donor_celltype_scores.csv.gz`. Full table: `reports/generated/nn_20260923/spectrum_v3/cell_scores.csv.gz`. Evidence: `docs/nn_v2/cell_scores_export.json`, `docs/nn_v2/CELL_SCORES.md`. Chr21-excluded export: 60000 cell×arm rows from `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/chr21_excluded_v3`.

## Cell-state spectrum (N16)

Donor-mean R3_ca scores from the ladder_v3 N15 export (`spectrum_v3`): **SPECTRUM_NULL** (9 eligible types). Chr21-excluded score compare `COMPARED` (call `SPECTRUM_NULL`; agree=True). Evidence: `docs/nn_v2/spectrum.json`, `docs/nn_v2/SPECTRUM.md`.

## Routing / attention (N17)

Per-cell-type descriptive readouts from ladder_v2 fold models (75 folds: R3_gated / R3_ca / R4_ca). All three readouts tagged **NOT_SHOWN_USED** because mapped N13 interventions I4 (CA / program-CA attention knockout) and I6 (gated route clamps) have Δ log-loss CIs that include 0. N13 `ATAC_USED` (I1) does not authorize attention/routing claims. Evidence: `docs/nn_v2/routing_attention.json`, `docs/nn_v2/ROUTING_ATTENTION.md`.

## Gene-activity secondary ladder (N21)

Secondary-only rerun under the decision-tree 500-gene amendment (`gene_activity_v2/`; primary remains N10 `B_NULL`). Outcome **GA_B_NULL**: GA_ca−GA_tc estimate 0.0533, CI [−0.0527, 0.1572] (includes 0; below practical margin). View-B gene-activity arms also null for R3_ca−R3_tc. GA_ca I1/I3/I4 faithfulness: NC exact zero; tags `GA_ATAC_UNUSED_OR_NULL`, `GA_CA_PAIRING_UNUSED`, `GA_ATTENTION_NOT_SHOWN_USED`. Never claim as independent external validation. Evidence: `docs/nn_v2/gene_activity_results.json`, `docs/nn_v2/GENE_ACTIVITY.md`.

## Results + unsent professor note (N22)

Written conclusion and D1–D13 coverage from verified JSON: `docs/nn_v2/NN_V2_RESULTS_2026-09-23.md`. Unsent note: `docs/nn_v2/PROFESSOR_NOTE_UNSENT.md`. Deferred experiments listed in `docs/nn_v2/FUTURE_WORK.md`.

## Final verification (N23)

Full suite `pytest -q -x` → **1188 passed**. Results top label **`NN_ASSIGNMENT_COMPLETE`** (claim limits retained: PC N/A; chr21 score export DEFERRED; N21 secondary). `gnhf/check_evidence.py` confirms verifier `primary_recomputed.ci` 3dp digits in the results doc.

## Paper framing (N24)

Rule table on accepted evidence → **F4** (F1–F3 FALSE): rigorous negative-result / detectability-limit paper. Evidence: `paper/framing.md`.

## Paper figures (N25)

`paper/make_figures.py --only all` wrote `paper/figures/fig1_schematic`, `fig2_planted`, `fig3_ladder`, `fig4_faithfulness`, `fig5_spectrum` (PNG 300 dpi + PDF) from planted / ladder_summary / faithfulness / spectrum JSON. `SKIPPED_FIGURES=[]`. Stale `fig1_architecture` and buggy-lane `fig4_spectrum` removed.

## Paper Results + claims (N27)

Rewrote `paper/draft.md` Results from accepted ladder_v2 evidence (B_NULL; F4; figures linked) and wrote `paper/claims.csv`. `python paper/check_paper.py` PASS.

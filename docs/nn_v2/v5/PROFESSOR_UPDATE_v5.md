# Professor update v5 (unsent — do NOT send)

**Plain result.** On the accepted real-data ladder (`ladder_v3`, 450/450 folds,
verifier **PASS**), cross-attention does **not** beat matched token-concat:
R3_ca − R3_tc donor balanced accuracy ≈ **0.0267**, 95% CI includes 0 (summary ≈
[−0.027, 0.077]; verifier ≈ [−0.025, 0.077]), margin 0.07 unmet → **`B_NULL`**.
Secondary **`LINEAR_SUFFICIENT`** (RNA logistic BA 0.427 > R3_ca 0.400). Model-free
chr21 dosage AUROC **1.0**. After dropping chr21, every scored arm ≤ 0.55 BA →
**`DOSAGE_DOMINATED`**. Held-out cell-state spectrum **`SPECTRUM_NULL`** (9 eligible),
including on chr21-excluded scores. No complex-model superiority claim.

**Validity.** Pooled AUROC for learned arms can look below chance while **per-fold
AUROC** means stay above chance (R3_ca mean ≈ 0.656 vs pooled ≈ 0.366) — report both
(`docs/nn_v2/v5/per_fold_metrics.json`). Forced-chr21 positive control through the full
pipeline: logreg donor AUROC **0.924**. Sklearn controls previously fit only the
inner-train third; fitting on full outer train fixed that path
(`PIPELINE_BUG_FIXED` → rebuild as `ladder_v3`). Predictions were not flipped.

**Other calls (ladder_v3).** Seeds `SPREAD_ONLY` (model 0.073, sampling 0.033).
Faithfulness: NC exact zero; `CA_PAIRING_UNUSED`; `ATAC_USED` (R3_tc I1); routing
readouts all `NOT_SHOWN_USED`. Adversary `R2_REJECTED` / `PROBE_DROP_INSUFFICIENT`.
Planted benchmark: **no** `CA_FAVOURED` regime (N4 S0–S5 and gene-matched S6).
Gene-activity secondary: `GA_B_NULL`. Limits: 30 donors; internal cohort; attention ≠
explanation; PC N/A. Paper still `DRAFT_V1_COMPLETE` until P6. This note is **unsent**.

## Direction coverage (plan §1, D1–D13)

| ID | Status | Evidence | Finding |
|---|---|---|---|
| D1 | DONE | `ladder_summary.json`; `nuisance_probe.json` | MIL/GRL/InfoNCE rungs run; R2 rejected (probe drop insufficient). |
| D2 | DONE | `spectrum.json`; `v5/spectrum_chr21_excluded.json`; `routing_attention.json` | Spectrum null (9 types), including chr21-excluded; routing not shown used. |
| D3 | DONE | `gene_activity_results.json`; `v5/planted_gene_aligned.json`; `parameter_counts.json` | GA secondary null; gene-matched planted S6 no CA_FAVOURED. |
| D4 | DONE | `sampling_cap1000_seed22.json` | Author cell types are strata only, never a prediction target. |
| D5 | DONE | `parameter_counts.json`; `ladder_summary.json` | Equal splits/features/head; R3_tc param-matched within 5%. |
| D6 | DONE | `planted_benchmark.json`; `v5/planted_gene_aligned.json` | Zero CA_FAVOURED regimes (additive linear-sufficient; pairing MLP-favoured). |
| D7 | DONE | `ladder_summary.json` (`logreg_concat`); planted concat arms | Concat logistic/MLP and token-concat present in every comparison table. |
| D8 | DONE | `sampling_cap1000_seed22.json` | Stable donor×cell-type×library sampler used throughout. |
| D9 | DONE | `faithfulness.json`; `seed_sensitivity.json` | Held-out interventions + seeds; PC N/A; tags CA_PAIRING_UNUSED / ATAC_USED; SPREAD_ONLY. |
| D10 | DONE | `PROTOCOL_FREEZE.md`; `NN_V2_RESULTS` §9 | Each refinement names a frozen-bib precedent; adapted combination only. |
| D11 | DONE | this note §plain result; `NN_V2_RESULTS` §1 | Plain-language null lead; no Tasic rerun. |
| D12 | DONE | `paper/refs_frozen.bib`; results §9 | No citations beyond frozen set; no novelty claim. |
| D13 | DONE | `chr21_excluded.json`; ladder `chr21_dosage`; P3 spectrum | Dosage perfect; beyond-dosage null (`DOSAGE_DOMINATED`); spectrum still null without chr21. |

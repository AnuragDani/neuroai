# Professor update v6 (unsent — do NOT send)

**Plain result.** On the accepted real-data ladder (`ladder_v3`, 450/450 folds,
verifier **PASS**), cross-attention does **not** demonstrate an advantage over
matched token-concat: R3_ca − R3_tc donor balanced accuracy ≈ **0.027**, 95% CI ≈
**[−0.025, 0.077]**, margin 0.07 unmet → **`B_NULL`** (advantage not demonstrated,
not equivalence). That remains the primary endpoint. Secondary
**`LINEAR_SUFFICIENT`**; model-free chr21 dosage AUROC **1.0**; after dropping
chr21, arms stay ≤ 0.55 BA → **`DOSAGE_DOMINATED`**. Held-out cell-state spectrum
**`SPECTRUM_NULL`**. PC N/A; N21 gene-activity secondary only. No complex-model
superiority claim.

**v6 sensitivities (do not retarget the headline).** (1) **chr21-forced**
representation (HVG ∪ all 538 chr21 genes; amendment before run): pooled CA−TC
donor BA **0.060**, CI **[0.011, 0.113]** → secondary
`CHR21FORCED_D_SMALL_POSITIVE` (estimate < 0.07); mean-fold CA−TC CI still
includes 0. Linear arms rise most (logreg_rna per-fold AUROC ~0.534 → 0.983).
(2) **Per-fold** mean CA−TC donor BA on `ladder_v3`: **0.016**, CI
**[−0.016, 0.045]** (includes 0; agrees with `B_NULL`). (3) **Detectability** at
30 donors (planted S4, CA vs TC): detection fraction **0** at every δ through
**1.0** → `min_detectable_delta` = **null** (not detectable up to δ = 1.0).

**External validation is deferred** (T13; author decision). This note is
**unsent**. Paper header `DRAFT_V3_COMPLETE` (`check_paper` pass; engineering
suite check still pending while E1 runs).

## Direction coverage (plan §1, D1–D13)

| ID | Status | Evidence | Finding |
|---|---|---|---|
| D1 | DONE | `ladder_summary.json`; `nuisance_probe.json` | MIL/GRL/InfoNCE rungs run; R2 rejected (probe drop insufficient). |
| D2 | DONE | `spectrum.json`; `v5/spectrum_chr21_excluded.json`; `routing_attention.json` | Spectrum null (9 types), including chr21-excluded; routing not shown used. |
| D3 | DONE | `gene_activity_results.json`; `v5/planted_gene_aligned.json`; `parameter_counts.json` | GA secondary null; gene-matched planted S6 no CA_FAVOURED. |
| D4 | DONE | `sampling_cap1000_seed22.json` | Author cell types are strata only, never a prediction target. |
| D5 | DONE | `parameter_counts.json`; `ladder_summary.json` | Equal splits/features/head; R3_tc param-matched within 5%. |
| D6 | DONE | `planted_benchmark.json`; `v5/planted_gene_aligned.json`; `v6/detectability.json` | Zero CA_FAVOURED regimes; S4 CA−TC not detectable up to δ=1.0 at 30 donors. |
| D7 | DONE | `ladder_summary.json` (`logreg_concat`); planted concat arms | Concat logistic/MLP and token-concat present in every comparison table. |
| D8 | DONE | `sampling_cap1000_seed22.json` | Stable donor×cell-type×library sampler used throughout. |
| D9 | DONE | `faithfulness.json`; `seed_sensitivity.json` | Held-out interventions + seeds; PC N/A; tags CA_PAIRING_UNUSED / ATAC_USED; SPREAD_ONLY. |
| D10 | DONE | `PROTOCOL_FREEZE.md`; `NN_V2_RESULTS` §12 | Each refinement names a frozen-bib precedent; adapted combination only. |
| D11 | DONE | this note §plain result; `NN_V2_RESULTS` §1, §8–§10 | Plain-language null lead; v6 sensitivities reported; no Tasic rerun. |
| D12 | DONE | `paper/refs_frozen.bib`; results §12 | No citations beyond frozen set; no novelty claim. |
| D13 | DONE | `chr21_excluded.json`; ladder `chr21_dosage`; `v6/CHR21_FORCED.md`; P3 spectrum | Dosage perfect; beyond-dosage null; chr21-forced sensitivity D_SMALL_POSITIVE only. |

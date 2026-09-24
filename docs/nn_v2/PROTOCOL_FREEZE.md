# NN-v2 Protocol Freeze (N9)

- **Frozen (UTC):** 2026-09-24T22:04:02Z
- **Git HEAD at freeze:** `1306bc508f19bb519e74cde25fad7bf12e284148` (parent of the commit
  carrying this note)
- **Protocol file:** `configs/nn_protocol_v2_2026-09-23.json`
- **Protocol sha256 (canonical JSON, sha256 field excluded):**
  `80931bfc05c403804db47f53b02b29989204a6c04720476cb752dd62968b7161`
- **Parameter counts:** `docs/nn_v2/parameter_counts.json`
- **Sampling artifact:** `docs/nn_v2/sampling_cap1000_seed22.json` (sha256
  `e515b2eee03804b3836256ba3e8b7604fa6a8043e50c06c36b24988250423b2f`)
- **ATAC tie-break region set:** `configs/atac_tiebreak_region_sets_2026-09-21.json`
  (sha256 `13f630a6777a059db4ac1b5f17b397976030e0b0e29193e2bc09eab24dc46407`; 465
  union regions, 256 per fold, salt `p22-atac-tiebreak-v1`, 25 folds)

## No real-label fit has run

No real-DS-label NN-v2 model has been fit as of this freeze. Evidence:
`reports/generated/nn_20260923/` contains only the N2 sampling/planted artifacts
(`N2`, `gene_activity`, `planted`, `logs`); no `ladder/` directory exists. The
factory in `src/p22/eval/nn_factory.py` builds architecture only and never reads
real disease labels.

## Frozen decisions

1. **Arms (18).** `R0_{ca,tc}`, `R1_{ca,tc}`, `R2_{ca,tc}`, `R3_{ca,tc}`,
   `R4_{ca,tc}`, `R3_tc_parammatched`, `R3_gated`, `latent_pca_lsi_head`, plus
   controls `logreg_rna`, `logreg_concat`, `pseudobulk_rna_logistic`,
   `chr21_dosage`, `majority`. N5–N8 all DONE, so the full ladder is listed and no
   arm is renamed.
2. **Primary contrast.** `R3_ca − R3_tc` donor balanced accuracy, margin 0.07,
   1000-draw donor-cluster bootstrap CI (seed 22). Secondary: donor AUROC,
   log-loss, Brier.
3. **Splits.** `iter_repeated_stratified_group_folds(donor, label, 5, 5, 0)`;
   3-fold inner validation; selection on inner-validation **donor log-loss**.
4. **Sampling.** cap 1000 cells/donor, seed 22, donor×cell-type×library strata;
   the historical 256-cap sample is the reproduction reference.
5. **Representation.** RNA log1p-CP10k, top-2000 training-only HVG, per-gene
   training-only scaling; ATAC per-cell TF-IDF, training-only IDF, per-fold
   tie-break 256-region set (union 465).
6. **Architecture (A13).** embed 32, hidden 128, dropout 0.2, 8 latent tokens,
   4 heads, Adam 1e-3, max 30 epochs, patience 6, bag size 64, model seed 0, CPU.
7. **Grid.** `R2: λ_adv ∈ {0.1, 1.0}`; `R3: λ_adv × λ_nce ∈ {0.1,1.0}²` selected by
   inner-val donor log-loss; the R2 winner is **not** carried into R3.
8. **Rung rejection rules** as plan §4.2; a rejected rung is still reported and the
   primary contrast stays fixed at R3.
9. **Parameter matching.** `R3_tc_parammatched` must be within 10% of `R3_ca`
   (5% informational); achieved relative error 1.10% (380,026 vs 384,250 params).

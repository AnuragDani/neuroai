# Framing decision (N24)

Rule: evaluate the N24 table in order; the first TRUE row decides the title and the
headline claim. Rule is applied to the frozen evidence, not to preference. Null/blocked
outcomes are valid inputs (plan A16).

## Evaluated truth table

| # | Condition | Evidence | Value |
|---|---|---|---|
| F1 | N10 outcome `A_ADVANTAGE` (not `A_FRAGILE`) AND N13 `CA_USES_PAIRING` | N10 = BLOCKED (lane stalled; no `ladder_summary.json`); N13 = BLOCKED (no fold models). Neither tag exists. | FALSE |
| F2 | N4 has ≥ 1 `CA_FAVOURED` regime AND N10 outcome B/C/D | `docs/nn_v2/planted_benchmark.json` `regime_labels`: 0 of 15 cells are `CA_FAVOURED` (14 `LINEAR_SUFFICIENT`, 1 `MLP_FAVOURED`); N10 outcome absent (BLOCKED). | FALSE |
| F3 | N16 `SPECTRUM_LOCALIZED` (any N10 outcome) | `docs/nn_v2/spectrum.json` = `NOT_ESTIMABLE(input_missing)`; no localized cell types. | FALSE |
| F4 | none of the above | F1–F3 all FALSE. | **TRUE** |

## Decided framing (F4)

Type: rigorous negative-result / benchmark paper.

Question answered: on paired RNA+ATAC single-cell data at 30 donors, does cross-modal
attention give a donor-level gain over simpler fusion, and what detectability limits
apply? The bench evidence says no attention advantage appears in any planted regime
tested, and the planned real-data primary contrast could not be estimated because the
ladder run was not completed.

### Title

RNA-linear sufficient? A donor-held-out benchmark of cross-modal attention on paired
single-cell RNA+ATAC

(No forbidden words: novel, first, mechanism, biomarker; title contains none.)

### Headline claim allowed by F4

"RNA-linear sufficient; stated detectability limits."

Concretely, the two allowed claims are:

1. **Benchmark.** Across the planted regimes tested (S0–S5, δ ∈ {0.25, 0.5, 1.0}),
   no cross-attention arm beats the best non-attention model by the pre-declared 0.07
   margin; a linear model on concatenated features already reaches the planted ceiling.
2. **Negative result with stated limits.** The real-data primary contrast (R3_ca −
   R3_tc) is not estimable in this run because the ladder execution is BLOCKED, so no
   real-data attention advantage is claimed. The limitation is stated, not hidden.

### What is NOT claimed

- No real-data advantage or disadvantage; the estimate does not exist.
- No mechanism, causality, clinical, external-validity or regulatory claim.
- No novelty claim for any component (adapted combination only; plan D10/D12).
- Gene-activity / program-token arms are NOT_NEEDED/BLOCKED and are omitted from claims.

### Section budget handed to N25–N34

Figures: Fig 2 (planted) is available; Figs 1, 3, 4, 5 are skipped and renumbered
because their source JSONs are absent (decision-tree N24 figure rule).
Results/Abstract carry only numbers traceable to `docs/nn_v2/*.json`; blocked-arm
facts are reported in Limitations. Framing selected by rule, not preference.

# N24 framing decision (accepted ladder_v2)

Evaluated 2026-09-28 against verified JSON only. First TRUE row decides framing.

## Truth table

| # | Predicate | Evidence | Value |
|---|---|---|---|
| F1 | N10 `A_ADVANTAGE` (not `A_FRAGILE`) AND N13 `CA_USES_PAIRING` | `ladder_summary.json` outcome `B_NULL`; `faithfulness.json` tags `CA_PAIRING_UNUSED`, `ATAC_USED` | FALSE |
| F2 | N4 ≥1 `CA_FAVOURED` AND N10 outcome B/C/D | `planted_benchmark.json` regimes: 13 `LINEAR_SUFFICIENT`, 3 `MLP_FAVOURED`, **0** `CA_FAVOURED`; N10 is `B_NULL` | FALSE |
| F3 | N16 `SPECTRUM_LOCALIZED` | `spectrum.json` `spectrum_call` = `SPECTRUM_NULL` (9 eligible; 0 Holm-sig) | FALSE |
| F4 | none of the above | residual | TRUE |

Superseded buggy-ladder framing that selected F3 from `SPECTRUM_LOCALIZED` is archived under `paper/superseded_buggy_ladder/` and must not be reused.

## Chosen framing (F4)

**Kind:** rigorous negative-result / detectability-limit paper.

**Headline claim allowed:** At 30 donors, paired RNA+ATAC cross-attention gives no donor-level DS gain over matched RNA-linear / token-concat baselines; planted regimes show no CA-favoured cell; stated power and dosage limits apply.

**Not allowed:** method-advantage claims; “pairing is used”; planted CA-helps headlines; cell-type localization of DS score; attention-as-explanation.

## Working title

Paired RNA+ATAC cross-attention shows no donor-level gain over RNA-linear baselines in a 30-donor developmental cortex cohort

(Forbidden words absent: novel, first, mechanism, biomarker.)

## Supporting facts for later sections (not headline)

- Primary R3_ca−R3_tc ≈ −0.0067; CI includes 0; margin 0.07 unmet → `B_NULL`.
- Secondary `LINEAR_SUFFICIENT`; model-free chr21 dosage AUROC ≈ 0.998; N11 `DOSAGE_DOMINATED`.
- N13 NC exact zero; I3/I4/I6 CIs include 0; N17 all `NOT_SHOWN_USED`; PC N/A.
- N21 gene-activity secondary `GA_B_NULL` only — not external validation.
- Claim limits: PC N/A; chr21 score export DEFERRED; no F2 planted support.

Sources: `docs/nn_v2/ladder_summary.json`, `ladder_verification.json`, `planted_benchmark.json`, `faithfulness.json`, `spectrum.json`, `NN_V2_RESULTS_2026-09-23.md`.

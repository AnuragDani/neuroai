# Adversarial self-review (N32; refreshed for P6 / DRAFT_V2_COMPLETE)

Eight reviewer objections against the accepted F4 / ladder_v3 draft. For each: cite an
existing `paper/draft.md` section if already answered, else add a Limitations sentence.
No new experiment was run beyond the v5 validity / P2–P3 evidence already accepted.

1. **Leakage between folds.** The reviewer asks whether outer-test donors can influence
   feature selection or model fitting. Resolved by Methods ("Representation"): every
   fitted transform (gene selection, scaler, IDF, region set) is fitted on outer-training
   cells only; outer-test donors never influence any fit. Results ("Sampling and parameter
   matching") records the fold-preparation smoke (training-only 2,000-gene / 256-region
   feature set).

2. **Confounding by age or batch.** The reviewer notes that donor-level scores could track
   developmental stage or sequencing batch rather than disease state. Batch side answered
   by Results ("Faithfulness, nuisance probe, and attention readouts") and Limitations:
   held-out probes reject R2 (`R2_REJECTED` / `PROBE_DROP_INSUFFICIENT`), so library and
   batch confounding are not shown to be erased. Age side: Limitations — developmental
   stage is recorded but not residualized or probed as a DS confounder beyond the declared
   library / batch / QC adversary.

3. **Thirty-donor power.** The reviewer asks whether thirty donors can support a
   donor-level contrast. Resolved by Limitations: the cohort contains thirty donors, so
   donor-level contrasts are low-powered and between-donor variance cannot be
   characterised with confidence. Abstract and title also state the 30-donor scope.

4. **Planted-signal realism.** The reviewer questions whether a synthetic planted ladder
   vindicates a negative real-data claim. Resolved by Results ("Planted benchmark"),
   Discussion, and Limitations: every planted signal is synthetic; the benchmark speaks
   only to detectability on constructed labels and carries no biological claim; zero of
   the S0–S5 regimes and the gene-matched S6 cells are `CA_FAVOURED`.

5. **Parameter mismatch.** The reviewer asks whether the attention arm simply has more
   capacity. Resolved by Results ("Sampling and parameter matching") and Discussion: the
   parameter-matched TC arm has 380,026 parameters against the 384,250-parameter `R3_ca`
   target (relative error 0.010993), inside both the 10% acceptance rule and the 5%
   informational bound.

6. **Attention interpretation.** The reviewer warns against reading attention weights as
   explanations. Resolved by Results, Discussion, and Limitations: all N17 readouts are
   `NOT_SHOWN_USED` (I4/I6 CIs include 0); attention weights are diagnostics, not
   explanations [@jain2019attention; @wiegreffe2019attention].

7. **Region-panel adequacy.** The reviewer asks whether the ATAC panel supports regulatory
   conclusions. Resolved by Methods ("Data and cohort") and Limitations: the panel is a
   prevalence / tie-break window set, not a curated regulatory panel; the N21 gene-activity
   rerun uses a gene-window amendment and remains secondary only.

8. **Lack of external cohort.** The reviewer asks about transportability. Resolved by
   Methods ("Controls and matching") and Limitations: no external cohort is used; all
   work is on a single internal development cohort, so estimates carry no transportability
   guarantee. Optional N21 gene-activity is never independent external validation.

9. **Below-chance pooled AUROC.** Added in v5: Results ("Per-fold AUROC and below-chance
   pooled scores") and Limitations state the pooling gap, the forced-chr21 positive
   control (donor AUROC 0.924), and the `PIPELINE_BUG_FIXED` → `ladder_v3` rebuild. Report
   per-fold AUROC alongside pooled metrics; never flip predictions.

## Disposition

| # | Objection | Disposition |
|---|---|---|
| 1 | Leakage | Cite Methods + Results |
| 2 | Age/batch confounding | Cite Results/Limitations for batch; Limitations for age |
| 3 | 30-donor power | Cite Limitations |
| 4 | Planted-signal realism | Cite Results + Discussion + Limitations |
| 5 | Parameter mismatch | Cite Results + Discussion |
| 6 | Attention interpretation | Cite Results + Discussion + Limitations |
| 7 | Region-panel adequacy | Cite Methods + Limitations |
| 8 | External cohort | Cite Methods + Limitations |
| 9 | Below-chance pooled AUROC | Cite Results + Limitations (v5 / P6) |

Draft header advanced to `DRAFT_V2_COMPLETE`. Superseded buggy-ladder self-review under
`paper/superseded_buggy_ladder/self_review.md` must not be reused.

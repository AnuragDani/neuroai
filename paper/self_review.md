# Adversarial self-review (N32)

Eight reviewer objections, each resolved either by pointing to an existing section of
`paper/draft.md` or by adding a sentence to Limitations. No new experiment was run.

1. **Leakage between folds.** The reviewer asks whether outer-test donors can influence
   feature selection or model fitting. Resolved by Methods: the outer-test holdout donors
   never influence fits, the feature set is training-only, and the fold-preparation smoke
   test reports the split sizes. See Methods and Results, "Sampling and input integrity".

2. **Confounding by age or batch.** The reviewer notes that donor-level gains could track
   age or sequencing batch rather than biology. Not previously answered: the nuisance probe
   is `R2_UNEVALUATED`, so batch recoverability was never tested. Added to Limitations.

3. **Thirty-donor power.** The reviewer asks whether thirty donors can support a
   donor-level contrast. Resolved by Limitations: donor-level contrasts are described as
   low-powered and between-donor variance as not confidently characterised.

4. **Planted-signal realism.** The reviewer questions whether a synthetic planted ladder
   vindicates a negative real-data claim. Resolved by Limitations and Discussion: every
   planted signal is synthetic, the benchmark speaks only to detectability on constructed
   data, and no biological or clinical claim is made.

5. **Parameter mismatch.** The reviewer asks whether the attention arm simply has more
   capacity. Resolved by Results, "Parameter matching": the matched arm is within the 10%
   acceptance rule and the 5% informational bound, so the comparison is capacity-matched.

6. **Attention interpretation.** The reviewer warns against reading attention weights as
   explanations. Resolved by Limitations: attention weights are explicitly not treated as
   explanations, the held-out interventions are unavailable, and readouts are not shown
   to be used.

7. **Region-panel adequacy.** The reviewer asks whether the ATAC panel supports regulatory
   conclusions. Resolved by Limitations: the panel is a window-derived feature set, not a
   curated regulatory panel, because the regulatory-panel task did not complete.

8. **Lack of external cohort.** The reviewer asks about transportability. Resolved by
   Limitations: all work is on a single internal development cohort with no external
   validation, so estimates carry no transportability guarantee.

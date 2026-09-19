# P22: results and next decision

Prepared 19 September 2026. Status: RNA study complete; paired RNA+ATAC study incomplete.

## Question and result

Do Down syndrome RNA effects agree across independent fetal-cortex cohorts, and
can accepted paired RNA+ATAC inputs support a later multimodal model comparison?

**The completed RNA comparison is inconclusive.** All four prespecified comparisons
have correlation intervals that cross zero. This does not establish directional
replication, and it does not prove that reproducible effects are absent.

## Completed work

- Compared donor-level discovery effects from **9 Down syndrome and 8 control
  donors** against published differential-expression summaries from an external
  study with **5 Down syndrome and 5 control donors**. The external raw matrix was
  not analyzed. Discovery effects include age and sex adjustment.
- Completed 1,000 donor bootstraps and 1,000 permutations per comparison, with
  zero failed bootstraps. Local and free-CPU Colab RNA results matched exactly.
- Completed **68 post-hoc donor omissions**. One donor had the largest influence
  across the four comparisons. All donors were kept; the primary result did not
  change. This diagnostic is exploratory, not another independent replication.
- Built donor-aware paired-model, cross-attention, final-refit and scoring code.
  Synthetic-data tests passed; real paired training and external scoring remain pending.

| Discovery → external population | Spearman correlation, 95% donor-bootstrap interval |
|---|---|
| Radial glia → outer radial glia | −0.0079 [−0.2516, 0.3187] |
| Radial glia → ventricular radial glia | −0.0305 [−0.2425, 0.2644] |
| Cycling progenitors → cycling progenitors | 0.0967 [−0.1806, 0.3349] |
| Intermediate progenitors → intermediate progenitors | 0.0097 [−0.1920, 0.2642] |

The comparisons share discovery donors; the first two also share cells. They
are not four independent biological experiments.

## What remains unresolved

Paired input status is **SOURCE_UNRESOLVED**. Two inspected raw libraries have
zero exactly shared peak intervals. This does not establish that the uninspected
processed objects are unusable. Common measured ATAC features, remaining release
and quality-control semantics, and specimen identity evidence must pass the
existing acceptance rules before real paired training.

The next bounded step is **E2-M1: read-only runtime/control feasibility**. Establish
available runtime identity and evidence for the agreed resource limits, or record
the exact blocker and smallest next action. A conditional metadata request and
processed-object inspection follow only after their controls and approvals pass.
No larger GPU, fragment download, or paid run is justified by this summary.

## Evidence to open first

- [Executed RNA notebook: code and saved results](html/current/P22_external_rna_local.executed.html)
  and [RNA result report](evidence/EXTERNAL_RNA_REPLICATION_RESULTS_2026-09-08.md).
- [Donor-influence report](evidence/RNA_DONOR_INFLUENCE_RESULTS_2026-09-10.md).
- [Executed paired Colab notebook](html/current/P22_paired_workflow_Colab.saved.html)
  and [Colab run record](evidence/PAIRED_COLAB_VERIFICATION_2026-09-15.md):
  **181 offline tests passed in Colab; 892 tests passed in the recorded local suite**.
  This run displayed saved RNA results. It did not download a dataset or train a real paired model.

This package contains saved evidence and new HTML exports, not new experiment results.

---
title: "Does Cross-Modal Attention Help Paired RNA and ATAC? A Donor-Held-Out Study"
format: docx
---

## Abstract

RNA and chromatin accessibility were measured in the same cells, creating an opportunity to learn how the two modalities work together. We asked whether cross-modal attention improves Down syndrome classification for donors the model has never seen. In a developmental-cortex cohort of 30 donors, we compared attention with a similarly sized model that joins RNA and ATAC tokens without attention, alongside simpler RNA-only models. Across 25 donor-held-out splits, the attention model scored 0.400 in donor balanced accuracy, compared with 0.373 for token concatenation. The difference was 0.0267 (95% donor-cluster confidence interval −0.0250 to 0.0768): too uncertain to establish an advantage and smaller than the planned 0.07 threshold for a useful gain. RNA-only logistic regression scored 0.427. Donor-level pseudobulk RNA logistic regression scored 0.513. These descriptive scores do not establish statistical superiority. Chromosome 21 dosage had donor AUROC 1.0. The results do not prove that attention and simpler fusion are equivalent. They show what this cohort supports, and where a new study would be needed.

## I. Introduction

Paired RNA and ATAC data offer two views of the same cell. RNA records expression; ATAC records accessible chromatin. It is tempting to assume that a model able to attend between those views will learn something a simpler model misses. Yet when the outcome belongs to a donor, a cell-level improvement is not enough: the model must work for people absent from training.

We studied this question in paired profiles from developing Down syndrome and control cortices [1]. The comparison focuses on a held-out donor, uses the same cells and features for attention and non-attention models, and includes an RNA-only baseline. We also ask whether any apparent gain depends on chromosome 21 dosage, the dominant known signal in this disease. The aim is a fair account of what the models learned, including a result that does not favour the more complex model.

## II. Related work

- Methods such as weighted-nearest-neighbour integration [2] and MultiVI [3] show that paired single-cell modalities can be combined in several ways. They address broader integration questions; our narrower question is whether attention improves donor-level disease-state prediction over matched, simpler choices.
- Attention-based multiple-instance learning can turn a set of cells into one prediction for a donor [4]. We use that idea without claiming that attention itself is a new method.
- Cells from one donor do not supply independent donor-level evidence [5]. We therefore hold out entire donors and treat attention weights as signals to test, not explanations of a prediction [6].

## III. Data and comparison

The source atlas contains 248,998 processed cells from 30 donors [1]. We sampled at most 1,000 cells per donor, preserving the mix of cell types and sequencing libraries. Every comparison used five repeats of five donor-held-out folds. In each fold, gene and ATAC-region selection and all fitted transformations used training donors only. We selected 2,000 RNA genes and 256 ATAC regions for each training fold; the regions were chosen by prevalence, not by a curated regulatory annotation.

The main comparison was the difference in donor balanced accuracy between cross-modal attention and token concatenation after both models received the same donor-level pooling and RNA–ATAC pairing objective. The models used the same splits, features, training budget and prediction head. Their parameter counts differed by about 1.1%: 384,250 for attention and 380,026 for concatenation. Before examining the result, we set 0.07 balanced-accuracy points as the threshold for a practically useful gain. RNA-only logistic regression, donor-level pseudobulk RNA logistic regression, concatenated-feature logistic regression, gated fusion and chromosome 21 dosage supplied simpler comparisons. The pseudobulk arm is a separate donor-level RNA baseline.

## IV. Analysis

We evaluated each model on donors excluded from its training fold and summarized the attention-minus-concatenation difference with a donor-cluster bootstrap confidence interval. We report balanced accuracy and AUROC. Because pooled scores from different stratified folds can give a misleading ranking, we also examined AUROC within folds; we did not reverse predictions to improve a metric.

We then asked three follow-up questions. First, what happens when chromosome 21 genes are excluded or deliberately retained? Second, do constructed RNA–ATAC interaction labels reveal a setting where attention helps? Third, do changes to cell pairing alter the attention model's predictions? Constructed labels test the comparison under known signals; they are not evidence of a biological interaction.

## V. Results

The attention model reached donor balanced accuracy 0.400; token concatenation reached 0.373. Their difference, 0.0267, had a 95% confidence interval from −0.0250 to 0.0768. The interval includes zero, and the observed difference is below the planned 0.07 threshold. We therefore cannot establish a useful attention advantage. This uncertainty also prevents an equivalence claim. RNA-only logistic regression reached 0.427. Donor-level pseudobulk RNA logistic regression reached balanced accuracy 0.513 and AUROC 0.557. These scores are descriptive. A larger point estimate alone does not establish superiority over attention.

Selected arms from the full comparison appear below.

| Model | Donor balanced accuracy | Donor AUROC |
|---|---:|---:|
| Cross-modal attention | 0.400 | 0.358 |
| Matched token concatenation | 0.373 | 0.332 |
| RNA-only logistic regression | 0.427 | 0.398 |
| Donor-level pseudobulk RNA logistic regression | 0.513 | 0.557 |

The table reports pooled out-of-fold metrics. Scores pooled across fitted folds are not a single calibrated ranking. Per-fold AUROC is a separate sensitivity analysis.

The strongest simple signal was chromosome 21 dosage, with donor AUROC 1.0. Removing chromosome 21 features left the tested disease-state models near chance. Retaining all chromosome 21 genes raised performance, including for the simpler models. In that follow-up comparison, the pooled attention-minus-concatenation difference was 0.060 (interval 0.011 to 0.113), while the average difference across folds had an interval that included zero. The follow-up does not alter the original comparison.

In 16 constructed-signal settings, none showed a clear attention advantage over the declared simpler alternatives. A later gene-matched interaction check reached the same conclusion. Across nine cell types with enough held-out observations, no disease-state difference survived the multiple-comparison correction. These findings describe this dataset and these tests; they do not establish that no joint biological signal exists.

## VI. What the models appear to use

If attention were using the pairing of RNA and ATAC from the same cell, disturbing that pairing should change its predictions in a consistent way. The saved interventions did not establish such a response, and the original comparison lacked a successful constructed-signal pairing check. We therefore do not claim that the model used cell pairing. Attention weights alone cannot answer that question [6].

A model component intended to reduce library and sequencing-batch information also failed to show the expected reduction in held-out probes. We cannot claim that these technical effects were removed. Later constructed-signal controls were invalid under their fixed gates. One had a held-out split with only one class. A second failed the no-signal and pairing-response checks. A further control failed its fixed marginal gate: RNA-only balanced accuracy was 0.750 and ATAC-only balanced accuracy was 0.708, both greater than 0.60. It also imposed exact orthogonality at zero correlation, which within-donor ATAC permutation did not preserve. The orthogonality defect does not identify the cause of every failed gate. The corrected independent-Gaussian control also failed its marginal gate: ATAC-only balanced accuracy was 0.625, greater than the allowed 0.60. These controls do not establish pairing use, method validity, or a biological mechanism. They also do not establish a dataset defect.

## VII. Discussion and limitations

In this cohort, chromosome 21 dosage discriminated donors strongly. The primary comparison did not establish a useful attention advantage over matched token fusion. RNA-only and pseudobulk RNA baselines had larger balanced-accuracy point estimates, without an accepted superiority claim here. The comparison concerns donor disease labels. It does not measure cell-state maturation or prove a disease mechanism.

The cohort has 30 donors, so the estimate is imprecise. The separate constructed-signal detectability exercise did not produce a confidence interval excluding zero at the tested amplitudes. This exercise does not establish statistical power for the real-data primary contrast. Donor count, model choice and task design remain possible limits. Developmental stage was recorded but not separately adjusted for the disease-state comparison. The ATAC panel was selected by prevalence. Disease labels came from the source atlas, and no independent paired cohort tested whether this result transports elsewhere.

## VIII. Conclusion and next experiments

The completed donor-held-out comparison does not demonstrate that cross-modal attention adds a useful gain for this disease-state task. It does not show that attention could never help paired RNA and ATAC data. A next study would need an independent paired cohort or a new, biologically motivated question, with a clear pairing check and donor-level analysis chosen before training. Until then, the current result is best reported as a bounded comparison in one cohort.

## Internal provenance note

A later masked-ATAC pilot is excluded from the accepted numerical results in this paper. Its real-data executor was added after the independent pre-fit review. Saved-result replay agrees with its predictions, but its scientific status remains NOT_AUTHORIZED. Later execution repairs passed an independent review and preserved that historical status. The repair-stage decision was NO_GO for an automatic new pilot. This paper reports the accepted original comparison, not a retrospective authorization of the later pilot.

## Declarations (venue-neutral preparation)

These stubs finish venue-neutral preparation. They do not invent funding, conflicts, author facts, ethics approvals or professor endorsement. Venue selection remains open. Status: **preparation complete; submission pending**.

| Item | Status | Owner | Completion condition |
|---|---|---|---|
| Funding statement | Unresolved | Researcher | Supply exact funding text, or an explicit none statement, for the chosen venue |
| Competing interests | Unresolved | Researcher | Supply conflicts disclosure, or an explicit none statement |
| Author list and contributions | Unresolved | Researcher | Confirm authors, affiliations and contribution roles before submission |
| Ethics / data-use statement | Unresolved | Researcher | Confirm reuse language required by the source atlas and chosen venue |
| Data availability | Partial | Researcher | Public atlas citation is present; add accession or repository links required by the venue |
| Code / artifact availability | Partial | Researcher | Repository paths and verifier commands exist; add a public release URL if the venue requires one |
| Venue length and style | Unresolved | Researcher | Select venue; apply length, section and reference-style rules |

No submission-ready claim is made here.

## References

1. Lattke et al., “Single-cell atlas of the developing Down syndrome brain cortex,” *Nature Medicine*, 2026. [Article](https://www.nature.com/articles/s41591-026-04211-1).
2. Hao et al., “Integrated analysis of multimodal single-cell data,” *Cell*, 2021. DOI: 10.1016/j.cell.2021.04.048.
3. Ashuach et al., “MultiVI: deep generative model for the integration of multimodal data,” *Nature Methods*, 2023. DOI: 10.1038/s41592-023-01909-9.
4. Ilse, Tomczak and Welling, “Attention-based Deep Multiple Instance Learning,” *ICML*, 2018. [Paper](https://proceedings.mlr.press/v80/ilse18a.html).
5. Squair et al., “Confronting false discoveries in single-cell differential expression,” *Nature Communications*, 2021. DOI: 10.1038/s41467-021-25960-2.
6. Jain and Wallace, “Attention is not explanation,” *NAACL*, 2019. DOI: 10.18653/v1/N19-1357.

<!--
P22-NN paper draft. Section authorship is tracked by task:
N28 wrote Introduction and Related Work only; Abstract/Methods/Results/
Discussion/Limitations/References are filled by later tasks. Framing is neutral:
the question is "when does cross-modal attention help on paired single-cell
RNA+ATAC?", with no result claims in this file yet.
-->

## Abstract

## Introduction

Many single-cell assays now measure RNA and chromatin accessibility in the same
cell, producing paired multiome profiles. A natural modelling choice is to fuse the
two modalities rather than analyse them separately, and cross-modal attention has
become a common fusion tool in other areas of machine learning. It is less clear,
however, when attention adds anything over simpler fusion on paired single-cell data.
A linear model on concatenated features, or a simple gated sum, can already capture
complementary information when the modalities carry consistent signal.

We study this question on paired single-cell RNA and ATAC profiles: when does
cross-modal attention help, and when are non-attention baselines sufficient? We treat
the question as an empirical one and answer it with an internal, donor-held-out
comparison. The protocol pairs a planted-signal benchmark, in which the pairing
structure and the class boundary are known, with a real disease-state task. The
planted benchmark asks whether an attention advantage appears in regimes where the
label depends on the joint configuration of the two modalities; the real task tests
whether any such advantage survives on measured data.

The design is an adapted combination of known techniques: multiple-instance learning
with attention, conditional nuisance removal by gradient reversal, and a contrastive
auxiliary objective, assembled into a single donor-level model. We do not claim the
components as new. We report both positive and negative outcomes, and we state where
the evidence does not support an attention advantage. All comparisons use
donor-held-out folds, and inference is done at the donor level, following the
pseudobulk literature.

## Related Work

**Multimodal single-cell integration.** Weighted nearest neighbours assign each cell a
set of modality weights and are a known precedent for per-cell modality weighting
[@hao2021integrated]. MOFA+ factorises multi-omics data into shared and
modality-specific factors [@argelaguet2020mofa]. MultiVI jointly models RNA and ATAC
with a variational autoencoder [@ashuach2023multivi]. These methods are established,
and the present work treats them as reference points rather than as baselines; the
baseline set is restricted by our protocol.

**Cross-modal attention.** Attention is the central building block of transformers
[@vaswani2017attention]. Multimodal transformers fuse unaligned modality sequences
with cross-modal attention [@tsai2019multimodal], and attention bottlenecks were
proposed to scale audiovisual fusion [@nagrani2021attention]. Attention also underlies
deep multiple-instance learning [@ilse2018attention], which motivates a donor-level bag
formulation. Contrastive objectives have been used to align modalities
[@oord2018representation; @radford2021learning].

**Attention and interpretation.** Whether attention weights explain a model's
decisions is contested [@jain2019attention; @wiegreffe2019attention]. We therefore
treat attention weights as diagnostics to be probed, not as explanations, and we test
whether the model uses the pairing.

**Nuisance and inference.** Domain-adversarial training removes nuisance signal by
gradient reversal [@ganin2015unsupervised; @ganin2016domain]. Single-cell differential
expression is best performed with the donor as the unit of inference
[@squair2021confronting]. Chromatin accessibility is summarised as gene activity over
gene bodies and upstream windows [@stuart2021signac], and matrix factorisation
provides a classical alternative for shared structure [@lee1999learning]. The source
cohort used here is annotated in the same study [@lattke2026down], so it is a
development resource rather than an independent validation cohort.

## Methods

**Data and cohort.** We analyse paired single-cell RNA and ATAC profiles from one
development cohort. The processed expression matrix holds 248,998 cells and 35,477
genes; raw counts are retained in `raw/X`, because the `X` layer is already normalised.
Disease status, author cell type, donor identity, library, sequencing batch, developmental
stage, sex and technical quality columns (`nCount_RNA`, `nCount_ATAC`, `TSS.enrichment`,
`percent.mt`, `nucleosome_signal`) are all present in `obs`. Donor is the unit of
inference throughout [@squair2021confronting]. ATAC is represented by unique
fragment-overlap counts over a 465-region union; the per-fold region set is chosen by
training-library prevalence and is an unbiased-order selection, not a regulatory
annotation. The cohort is annotated in the same source study [@lattke2026down].

**Cell sampling.** Each donor contributes at most 1,000 cells (sampling seed 22), drawn by
a stable donor × author-cell-type × library stratified sampler. The historical
256-cell-per-donor sample is kept as the reproduction reference. Sampling is fixed before
any label is read and balances cell counts across donors and strata.

**Representation.** RNA counts are transformed per cell as
`log1p(1e4 · raw_count / cell_total_raw_count)`. Within each outer-training fold, the top
2,000 genes are selected by label-free normalised dispersion, and each gene is
standard-scaled using training cells only. ATAC counts are transformed per cell by TF-IDF,
`log1p(tf · idf)`, with IDF fitted on training cells only, over the per-fold 256-region
training-only set. Every fitted transform — gene selection, scaler, IDF and region set —
is fitted on outer-training cells; outer-test donors never influence any fit.

**Model ladder.** The ladder adds one refinement per rung, and at every rung a
cross-attention (CA) arm and a matched token-concatenation (TC) arm are trained
identically: same donors, splits, cells, features, head and selection budget. R0 is a
cell-level cross-entropy model with inherited donor labels. R1 replaces cell-level
training with gated-attention multiple-instance learning over donor bags of 64 cells
[@ilse2018attention]; attention is `a_i = softmax_i(wᵀ(tanh(V h_i) ⊙ sigmoid(U h_i)))`,
the bag embedding is `H_b = Σ_i a_i h_i`, and the donor probability is `sigmoid(f(H_b))`
trained with binary cross-entropy. Per-cell scores `s_i = f(h_i)` are exported for
held-out donors. R2 adds a conditional gradient-reversal nuisance adversary
[@ganin2015unsupervised; @ganin2016domain] on library (cross-entropy), sequencing batch
(cross-entropy) and a five-column standardised QC vector (mean squared error), with one
hidden layer of 64 units and gradient-reversal slope `γ(p) = 2/(1+exp(−10p)) − 1`; the
adversary is conditional on the disease label because two batches contain disease donors
only. R3 adds a symmetric InfoNCE pairing loss [@oord2018representation;
@radford2021learning] between L2-normalised 32-dimensional projections of the RNA and
ATAC views at temperature `τ = 0.1` within each minibatch. R4 replaces the learned latent
tokens with training-only NMF gene-program tokens and region modules [@lee1999learning].
The total objective is `L = L_MIL + λ_adv·L_adv + λ_nce·L_nce`.

**Architecture and training.** The frozen widths are 8 latent tokens, embedding 32,
hidden 128, dropout 0.2, 4 attention heads, attention width 64, gate hidden 32, program
width 32 with 4 heads, adversarial hidden 64, pairing projection 32 and latent width 64.
Training uses Adam at 1e-3, minibatch 64, at most 30 epochs, early stopping with patience
6 on inner-validation donor log-loss, model seed 0, on CPU with one torch thread per
worker and at most 14 workers. `λ_adv` and `λ_nce` are selected from {0.1, 1.0} on
inner-validation donor log-loss: R2 selects `λ_adv`, R3 selects both without carrying the
R2 winner forward. Cross-modal attention follows the multimodal-transformer
[@tsai2019multimodal] and attention-bottleneck [@nagrani2021attention] precedents, with
transformer attention as the underlying block [@vaswani2017attention]; per-cell modality
weighting is a known precedent [@hao2021integrated]. Gene-activity summaries follow gene
body plus upstream windows and TF-IDF summarisation [@stuart2021signac]. The components
are an adapted combination and are not claimed as new.

**Evaluation contract.** Every arm is evaluated on the same 5 × 5 repeated stratified
donor folds (split seed 0), with a 3-fold inner donor split of the training donors for
validation. The primary endpoint is donor balanced accuracy of `R3_ca` minus `R3_tc`, with
a pre-declared practical margin of 0.07 and a 1,000-draw donor-cluster bootstrap
confidence interval (bootstrap seed 22); secondary endpoints are donor AUROC, donor
log-loss and donor Brier score. Rung rejection rules are pre-declared: R1 is rejected if
donor log-loss is not lower than R0 for both CA and TC; R2 if the held-out nuisance probe
does not drop at least 5 points versus R1, or donor balanced accuracy falls by more than
0.05; R3 if pairing retrieval top-1 is at most twice chance, or donor log-loss is worse
than R2; R4 if donor balanced accuracy is more than 0.05 below R2. A rejected rung is
still reported, and the primary contrast remains fixed at R3.

**Controls and matching.** Comparators are logistic regression on RNA, logistic regression
on concatenated RNA+ATAC features, a pseudobulk RNA logistic model, a chromosome-21
dosage baseline, a majority-class baseline, a gated-fusion arm, and a parameter-matched
token-concatenation arm required to stay within 10% of the cross-attention parameter count
(5% informational). A latent PCA(RNA)+LSI(ATAC) model is included as a classical
alternative. No external cohort is used; all results are internal and donor-held out.
Diagnostic interventions probe whether predictions depend on the pairing (within-donor,
within-cell-type ATAC permutation) and on the learned attention, but attention weights are
treated as diagnostics rather than explanations [@jain2019attention;
@wiegreffe2019attention].

## Results

## Discussion

## Limitations

## References

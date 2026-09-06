# Paired DS multiome dataset options

**Audit date:** 2026-09-03; plan revised 2026-09-05 after technical review.

**Question:** Can a public Hugging Face or repository dataset close P22's real neural-network data gap?

## Decision

**Public paired data are available. Readiness for comparable training and external evaluation is still conditional.**

Use two primary-source cohorts:

1. **Use GSE305146 as the training/development candidate**, the exact fetal-cortex multiome subseries within GSE305153. Its official GEO deposit contains combined RNA+ATAC MEX matrices. Library mapping, QC, and a comparable ATAC representation must pass before training.
2. **Reserve the Vuong et al. NeMO cohort for external multimodal evaluation.** Its public metadata contains 26 donors and the archive provides paired RNA+ATAC count packages. Reconcile the release/QC discrepancy and assess specimen independence before treating it as an accepted external cohort.

Do not call GSE305146 an external replication. GSE305146, GSE305153, and CELLxGENE dataset `f16c25da-15bd-46a4-9a3f-17093f27a2f1` are different releases of the **same Lattke et al. cohort**.

Development order and acceptance checks are in [tasks/plan.md](../tasks/plan.md) and [tasks/todo.md](../tasks/todo.md). The first data-audit implementation and measured file results are in [the audit guide](PAIRED_MULTIOME_AUDIT.md); training remains blocked. The existing [RNA replication plan](EXTERNAL_RNA_REPLICATION_PLAN.md) remains a separate workstream. Prior B2b run results remain historical results; public matrix discovery does not retroactively make those runs multimodal.

## What gap each source closes

| Source | DS/control | Same-nucleus RNA+ATAC | Processed counts/peaks | Independent of current cohort | Correct role |
|---|---:|---:|---:|---:|---|
| [GSE305146](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE305146) / current CELLxGENE | 15/15 published final cohort | Yes, study design | Yes, GEO combined MEX | No | Training candidate; compatibility pending |
| [Vuong et al. NeMO](https://assets.nemoarchive.org/col-umstjg0) | 13/13 in downloaded metadata | Yes, study design and matching barcode manifests | Yes, open RNA and ATAC MEX | Different study; specimen audit pending | Reserved external evaluation candidate |
| [GSE280175](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE280175) | 5/5 | No, RNA only | RNA counts only | Different study; retain provenance checks | RNA-only external validation |
| [HF brain Zarr](https://huggingface.co/datasets/KokosDev/single-cell-brain-zarr) | Mixed Census export | No, RNA only | RNA Zarr | Not guaranteed | RNA pretraining/I/O testing only |
| [GSE204684](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE204684) | No DS arm | Yes | Public GEO data | Different study | General cortex pretraining only |

Availability establishes a source for paired measurements, not a verified model input. External evaluation excludes NeMO from model fitting, learned feature selection, threshold selection, and early stopping. Metadata, schema, and predeclared QC checks are permitted before that evaluation and must be logged.

## 1. Exact current-cohort source: GSE305146

### Identity and provenance

- [GSE305153](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE305153) is the Lattke et al. SuperSeries.
- [GSE305146](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE305146), BioProject `PRJNA1304509`, is its exact **fetal cortex multiome** subseries.
- The associated paper is [Lattke et al., Nature Medicine (2026)](https://www.nature.com/articles/s41591-026-04211-1).
- The current [CELLxGENE collection](https://cellxgene.cziscience.com/collections/0e9fd1d3-ef4c-47c6-a2e4-ef4bfadf7c79) points to that paper and SuperSeries.

These are not three independent cohorts.

### Biological design

- 10x Genomics Multiome: gene expression and chromatin accessibility from the same nuclei.
- Fetal cortex, post-conception weeks 10–20.
- Acquired: 20 euploid control and 19 DS specimens.
- Retained after exclusions and QC: 15 control and 15 DS donors; 248,998 nuclei.
- CELLxGENE metadata exposes 30 donor IDs and balanced disease labels.
- The existing P22 run retained 248,960 nuclei after its own QC. Preserve the distinction between published counts, downloaded counts, and P22-retained counts.

### Available files

The official [GEO supplementary directory](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE305nnn/GSE305146/suppl/) contains:

- 46 `matrix.mtx.gz` objects, with matching `barcodes.tsv.gz` and `features.tsv.gz` files.
- About **3.37 GiB compressed** across the matrix files.
- Combined feature spaces. A checked example, [`GSE305146_B10C1Q_features.tsv.gz`](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE305nnn/GSE305146/suppl/GSE305146_B10C1Q_features.tsv.gz), has 36,601 `Gene Expression` and 46,672 `Peaks` features.
- Two optional processed Seurat archives: about 8.7 GB for the complete object and 7.6 GB for the excitatory-lineage object.

CELLxGENE also exposes:

- Processed H5AD: about **1.46 GiB**; the current local analysis uses its RNA-centered matrix.
- ATAC fragment BGZF: about **23.76 GiB**, plus a roughly 5.1 MiB tabix index.

Start with a bounded GEO MEX inspection. The 46 files are library-level matrices, not 46 independent donors and not automatically the final 30-donor cohort. Resolve library-to-donor mapping, repeat libraries, excluded samples, and retained barcodes explicitly.

MEX files may avoid fragment processing for a pilot, but that is not established for a comparable multi-donor or cross-cohort analysis. Peak sets may differ between libraries as well as studies. A precomputed common-count object could help; otherwise exact recounting on common regions may require fragments. See the feature contract below.

### Gap verdict

- **Paired data source:** identified; usable shared feature representation pending.
- **Closes independent-validation gap:** no.
- **Overlap risk:** certain; it is the same study and donor cohort as the current CELLxGENE dataset.
- **License/terms:** GEO and CELLxGENE expose public downloads, but no dataset-specific license was found in their catalog metadata. Cite the source paper and accession; check repository terms before redistribution.

## 2. Strongest independent option: Vuong et al. NeMO

### Identity and provenance

- Paper: [Vuong et al., Science (2026), DOI 10.1126/science.aea1259](https://pubmed.ncbi.nlm.nih.gov/42024758/).
- Official archive: [NeMO collection `nemo:col-umstjg0`](https://assets.nemoarchive.org/col-umstjg0).
- Open processed RNA child collection: [`nemo:col-mbgxwtz`](https://assets.nemoarchive.org/collection/nemo:col-mbgxwtz).
- Open processed ATAC child collection: [`nemo:col-ad8t52b`](https://assets.nemoarchive.org/collection/nemo:col-ad8t52b).

### Biological design

- Human mid-gestation neocortex.
- 10x Multiome paired RNA and ATAC from the same nuclei.
- Downloaded metadata identifies 26 donors: 13 control and 13 trisomy 21; independence from GSE305146 requires the provenance audit below.
- Processed metadata audit: 117,532 nuclei total.
  - Control: 61,656 nuclei.
  - Trisomy 21: 55,876 nuclei.
- Gestational weeks 13–23.
- Metadata fields include `donor`, `condition`, `gw`, `region`, `sex`, `ancestry`, `sample`, `barcode`, `nCount_RNA`, `nFeature_RNA`, `nCount_ATAC`, and `nFeature_ATAC`.

The final [Science article](https://pmc.ncbi.nlm.nih.gov/articles/PMC13225313/) reports **113,801 high-quality nuclei**, whereas the audited metadata has **117,532 rows**, a difference of **3,731**. The cause is unresolved. Pin the release, reconcile matrix columns against metadata, and identify documented QC exclusions or version differences. Never delete 3,731 arbitrary cells to match the paper. If the discrepancy cannot be explained, ingestion diagnostics may continue, but confirmatory external evaluation remains pending.

The RNA and ATAC manifests reference the same barcode checksum. This supports a shared nucleus index; the loader must still verify the downloaded files, ordered barcodes, unique metadata join, and matching dimensions before declaring file-level pairing verified.

### Minimum useful downloads

| File | Format | Approximate size |
|---|---|---:|
| Metadata | CSV in tar archive | 4.4 MiB |
| RNA counts | MEX tar.gz | 684 MiB |
| ATAC counts | MEX tar.gz | 1.43 GiB |
| **Core total** | Metadata + both count matrices | **about 2.11 GiB** |
| Optional ATAC fragments | Fragment archive | about 19.2 GiB |

Direct processed count directories:

- [RNA counts](https://data.nemoarchive.org/other/grant/r21_delatorre/delatorre/multimodal/sncell/10xMultiome_RNAseq/human/processed/counts/)
- [ATAC counts](https://data.nemoarchive.org/other/grant/r21_delatorre/delatorre/multimodal/sncell/10xMultiome_ATACseq/human/processed/counts/)

The parent NeMO collection lists 127 files and 760.22 GB because it includes controlled raw data. Those raw files are not required for the proposed count-matrix model.

### Independence and overlap audit

- Different paper, author group, archive, and collection from Lattke/GSE305146.
- All 26 processed donor IDs differ from the current GSE305146/CELLxGENE donor IDs.
- No donor-identifier overlap found.

Different identifiers can name the same specimen across repositories. Compare documented tissue providers, specimen accessions, donor metadata, and any published crosswalks; do not infer identity or non-identity from names alone. Record `confirmed_overlap`, `no_overlap_evidence`, or `unresolved`, with sources. Known overlap excludes the affected donors from external evaluation; unresolved plausible overlap blocks an unqualified independent-validation claim. Until completed, use “different-study candidate with no shared donor identifiers found.”

### Access terms

- Processed RNA and ATAC count packages are currently exposed through the open child collections.
- Raw/controlled collections require institutional approval. [NeMO's controlled-access page](https://nemoarchive.org/resources/accessing-controlled-access-data) states General Research Use, not-for-profit use, institutional/IRB documentation, a NeMO/NIMH agreement, one-year access, and requester-pays cloud egress.
- A per-file manifest may still label an access field as `embargo` while current open collection pages provide public links. Verify terms at download time; do not redistribute by assumption.

### Gap verdict

- **Paired data source:** identified; file/QC and feature checks pending.
- **Independent-validation candidate:** identified; acceptance and evaluation pending.
- **Processed peak/count matrix:** yes.
- **Statistical scale:** 13 donors per condition before new exclusions; not a power calculation or proof of adequate sample size.
- **Main risks:** release/QC discrepancy, specimen overlap, age and region differences, library effects, and ATAC comparability.

## 3. GSE280175: useful, but RNA only

The [GSE280175 GEO record](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE280175) and [Nature Communications paper](https://www.nature.com/articles/s41467-025-63752-0) report:

- Fetal cortex, post-conception weeks 13–19.
- 5 DS and 5 euploid donors.
- 122,663 nuclei after QC.
- Single-nucleus RNA sequencing only.

No same-nucleus ATAC or processed peak matrix is present. Therefore:

- **Multimodal model training:** no.
- **Multimodal external validation:** no.
- **RNA-only external validation:** yes.
- **Role in P22:** retain as an orthogonal RNA replication set; do not present it as closing the neural-network modality gap.
- **License/terms:** public GEO download; no dataset-specific license found in the GEO record. The article license does not automatically define data redistribution rights.

## 4. Hugging Face audit

No Hugging Face dataset found that met all required conditions: DS versus euploid developing cortex, same-nucleus RNA+ATAC, independent donor IDs, and a processed peak/count matrix.

The closest plausible result was [`KokosDev/single-cell-brain-zarr`](https://huggingface.co/datasets/KokosDev/single-cell-brain-zarr):

- A derivative export from CELLxGENE Census, not an original study deposit.
- RNA expression only; no ATAC matrix.
- Full card reports 28,967,109 cells by 61,497 genes across 29 Zarr shards and about 38.14 GB compressed. The Hub file display reports a different aggregate size because of repository/Xet accounting.
- A 150,000-cell quickstart sample is about 52.52 MB.
- Metadata can include `dataset_id`, disease, and donor fields, but a generic brain filter does not establish an independent DS cohort.
- Any DS cells can include the current CELLxGENE study, creating hidden same-study overlap.
- The Hub card declares MIT for the mirror while also directing users to upstream Census terms. The mirror label cannot override source-dataset terms.

Verdict: useful for RNA encoder pretraining or storage-pipeline testing. It cannot train or validate P22's paired multimodal model.

## 5. General cortex pretraining option

[GSE204684](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE204684), associated with [Zhu et al., Science Advances (2023)](https://doi.org/10.1126/sciadv.adg3754), simultaneously profiled gene expression and chromatin accessibility in 45,549 human cortical nuclei across six developmental stages.

It can help pretrain an RNA/ATAC representation or test integration code. It lacks a DS-versus-euploid disease design, so it cannot train the target classifier or validate DS biology. Defer pretraining for the first pilot; adding cells does not increase the number of independent DS donors in the target evaluation.

## Recommended study design

### Primary design

1. **Training/development candidate:** GSE305146 combined MEX matrices, after cohort and feature checks.
2. **Split unit:** donor, never nucleus.
3. **Internal evaluation:** donor-held-out folds within GSE305146.
4. **External multimodal evaluation:** accepted Vuong/NeMO cohort after documented QC, reserved from fitting and model selection. Log prior metadata inspection separately from evaluation.
5. **External RNA replication:** GSE280175.
6. **Pretraining:** deferred. A later protocol must exclude evaluation donors from pretraining too.

### Research question and donor-level inference

The [existing same-cap run](../reports/generated/verification/down_syndrome/same_cap_final/run_20260815T001359Z/runs/real_analysis_20260728/SUMMARY.md) reports chromosome-21 dosage balanced accuracy of 1.00 at every cell cap; RNA-only reaches 0.833 at the primary 256-cell cap. A new network cannot improve on that observed internal accuracy ceiling.

Proposed primary question: **Does cross-attention improve donor-level DS prediction in a different study relative to RNA+ATAC concatenation?** Freeze this question and the protocol before external predictions. The result may be negative or inconclusive; successful training is an engineering outcome, not evidence of scientific advantage.

- Primary contrast: external donor balanced accuracy, cross-attention minus concatenation. Predeclare model configuration, prediction threshold, and one final checkpoint per model before evaluation.
- Keep majority, chromosome-21 dosage, QC/covariate, pseudobulk RNA, RNA-only, ATAC-only, concatenation, and gated fusion controls. Report all on the same retained donors and matched cell caps. An attention-versus-concat improvement alone does not establish superiority to dosage or the other simpler controls.
- Reuse the existing primary cap of 256 cells/donor and 64/128 sensitivity caps, using the same nested paired cells for every eligible model. Report donors below the cap and any exclusion; no performance-driven sample removal.
- Repeat the existing five-by-five donor-held-out evaluation on GSE305146. Use separate inner validation donors for checkpoint/hyperparameter selection; outer held-out donors and NeMO never select a model. Fit all learned transforms inside each training fold.
- Effective initial sample sizes are 30 training donors and 26 external donors, not the cell totals. Use a small network, equal donor contribution to training, and donor-level validation scoring. The current `train_model` scores validation cells; it needs an explicit donor-aggregation option for this extension.
- Compute a paired donor-resampling 95% interval for the primary delta, with 1,000 resamples and seed 22; preserve pairing between models, report invalid resamples, and never treat repeats or cells as independent donors. Use one primary contrast; additional contrasts and ablations are secondary unless a multiplicity rule is frozen.
- Retain the plan's resolution rule: `r = max(1/(2*n_control), 1/(2*n_ds))`, practical margin `ceil(2*r*100)/100`. At 13+13 external donors this is 0.08. An external advantage requires delta at least this margin and interval lower bound above zero. Recompute from accepted donor counts before predictions; this rule is not a statistical-power guarantee.
- An optional chromosome-21-masked analysis must be registered beforehand and mask corresponding RNA and ATAC features consistently. It asks about signal beyond direct dosage, not causal mechanism. Do not switch the primary endpoint after viewing results or interpret attention weights as biological proof.

### Developmental age and cohort shift

GSE305146 uses post-conception weeks (PCW). Vuong uses gestational weeks (GW), with ultrasound/LMP dating documented in the [article methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC13225313/). The previous instruction to filter both raw columns to 13–20 was incorrect.

Retain `age_raw`, `age_unit`, `age_source`, `age_conversion`, and a canonical `age_pcw`. For documented obstetric GW, use `age_pcw = age_raw - 2` as an explicit approximate conversion. Already-PCW values remain unchanged. Missing or ambiguous definitions must remain unresolved, not silently converted. Thus PCW 13–20 corresponds to GW 15–22 only where that convention is verified.

The primary external analysis uses all otherwise eligible donors; the prespecified age-overlap sensitivity uses canonical PCW 13–20. Report donor/condition counts after filtering, tissue region, cell-type composition, sex, library, and QC distributions. If either condition lacks support, report the sensitivity as not applicable. Freeze cell-type mapping and any covariate treatment before predictions; never jointly fit batch correction on discovery plus external matrices.

### Cross-cohort feature contract

Peak counts aggregate signal over specific intervals. Renaming, overlapping, or summing different intervals cannot generally reconstruct exact counts on a new interval. A missing peak row is unmeasured coverage, not an observed biological zero. This applies within GSE305146 as well as between cohorts. [Signac merging guidance](https://stuartlab.org/signac/articles/merging) explicitly describes inaccuracies when merging without recounting.

Use this ordered decision:

1. Inspect published matrices and documented common-count objects for compatible, genuinely quantified regions and matching count semantics. Record how upstream peaks/features were selected; study-wide processing may limit a strict held-out interpretation even when labels were not used.
2. For confirmatory evaluation, require identical measured regions/count semantics, or recount on frozen common regions from fragments. Common regions must come from a fixed reference annotation or the relevant training fold only. Feature lists alone do not provide counts for unmeasured regions. Prefer reusing available common-count objects before budgeting a fragment recount.
3. A peak-to-gene sum is permitted for an **exploratory pilot**, labeled `peak_derived_gene_score`. It is not exact fragment-derived gene activity and does not automatically pass the confirmatory compatibility gate. Pin gene annotation, interval rules, overlap/double-counting policy, coverage masks, and whether ATAC counts represent insertions or fragments. Never fill unmeasured coverage with zero without exposing that distinction. [10x count semantics](https://www.10xgenomics.com/support/software/cell-ranger-arc/latest/analysis/feature-barcode-matrices)

For the approximation, test hand-calculated overlapping-peak examples, quantify covered genomic length and missingness per gene/library, and compare against exact counts on a training-only fragment subset if available. Freeze numerical acceptance limits before examining validation outcomes. Without an adequate reference or accepted limits, keep the approximation exploratory. Failure returns `NEEDS_RECOUNT` or `INCONCLUSIVE`; it must not silently promote the cheap route.

Freeze genome build, chromosome naming, gene identifiers, peak-to-gene windows, blacklists, duplicate handling, zero/missing semantics, normalization, and feature order in a versioned contract. Structural external-file inspection is allowed, but external expression, ATAC values, or labels must not select the representation or its thresholds. If external compatibility fails, record failure before changing the protocol; do not tune until it passes and call the result untouched.

### Cross-attention is a separate implementation task

`src/p22/models/fusion.py::GatedFusionModel` explicitly implements an MLP gate plus weighted branch sum. It is not query/key/value cross-attention. Reuse it as a baseline, alongside `ConcatFusionModel` and `BaselineMLP`.

Add a small `CrossAttentionFusionModel` only after the data and protocol gates pass. Specify RNA-query/ATAC-key-value direction (or a fixed bidirectional design), token construction, dimensions, heads, pooling, and output contract before implementation. Each attended modality must provide more than one key/value token: softmax over one key cannot learn a selective attention distribution. Keep tokenization independent of external data; learned latent tokens must not be labeled as biological genes or pathways.

Use the installed PyTorch attention implementation. Match token encoders, feature budgets, and training/selection budgets with a concatenation control, and report parameter counts. Verify finite outputs/gradients, dependence on both modalities, and correctly implemented ablations. Attention-weight plots alone do not satisfy the professor's architectural comparison or establish regulatory mechanisms.

### Acceptance checks before training

- Checksums, count semantics, matrix dimensions, unique ordered barcodes, and metadata joins pass for both MEX layouts.
- Library-qualified barcodes map to one donor/condition; repeat libraries remain in the same donor split. Excluded GSE305146 libraries are accounted for.
- Published, downloaded, and retained counts are reported separately. Reconcile NeMO's 117,532 versus 113,801 discrepancy and record any donor loss from the initial 15/15 and 13/13 cohorts.
- Specimen provenance audit is documented; donor-ID comparison alone is insufficient.
- Age units/conversion and canonical-PCW filtering are verified, with class support reported.
- The shared ATAC feature/count contract passes, or the run is explicitly exploratory/pending recount.
- Train/validation/test partitions contain disjoint donors.
- Feature fitting, normalization statistics, early stopping, and threshold selection use training/development donors only.
- Report performance by donor and condition, not only by nucleus.
- The primary hypothesis, small-model budget, donor-level checkpoint scoring, uncertainty rule, and baseline list are frozen.
- Cross-attention is distinguished from gating and compared with an appropriate concatenation control.

## Compute consequence

The processed packages make a bounded local pilot plausible: about 3.37 GiB for GSE305146 matrix files and 2.11 GiB for NeMO core packages, excluding additional indices, annotations, temporary files, and outputs. Compressed download size is not peak memory or working-disk demand.

Measure available disk, extraction overhead, sparse loading, peak memory, and wall time on a small training-cohort pilot; reduce to capped cells/features before any dense tensor conversion. The current generic transform/training helpers accept dense arrays, so passing the full sparse atlas through them is not a safe memory plan. Reuse resource measurements from `src/p22/data/resources.py` and record a fresh budget. If exact recounting is needed, budget fragments and workspace separately. GPU or cloud choice follows those measurements; neither is established as required or sufficient by the file listing.

## Final recommendation

Next deliverable: **a bounded paired-data ingestion and compatibility report**, followed by donor-aware training only when its required gates pass. Keep GSE280175 for RNA replication. Public availability is established; full ingestion, comparable ATAC features, and independent validation are not yet completed.

The [development checklist](../tasks/todo.md) orders source/QC reconciliation, age normalization, sparse ingestion, ATAC compatibility, protocol freeze, donor-aware baseline training, a distinct cross-attention implementation, and locked external evaluation. Data-audit code and a bounded public-file pilot are now available; model development and predictive evaluation remain gated by the unresolved inputs and approval.

# Citation-support audit — 2026-10-03

**Source gate C3: PASS after surgical wording corrections.** Scope: provisional venue copy only; accepted full/short manuscripts and frozen bibliography are unchanged. Gemini plan review: PASS via AGy CLI.

Coverage: 17/17 unique keys; 14 original citation groups / 22 key uses; 21 revised groups / 22 key uses. Original and revised occurrences are preserved in [CITATION_SUPPORT.json](CITATION_SUPPORT.json). References-list entries are metadata, not independent scientific claims; the declaration’s atlas citation is also covered.

## Primary source support

All source passages below are faithful paraphrases, not verbatim quotations. Broad architectural motivations use primary abstracts. Specific cohort and Signac-window claims use article results/methods. No metadata-only PASS, search snippet, or model-memory verdict.

| Key | Primary source and locator | Supporting paraphrase and scope | Verdict |
|---|---|---|---|
| `lattke2026down` | [Primary text](https://www.nature.com/articles/s41591-026-04211-1); Results: A single-cell gene expression and chromatin accessibility atlas; first paragraph / Fig. 1a–b | Profiling used 10X Multiome in 15 DS and 15 control fetal samples, with 248,998 cells retained after QC. Same-cohort disease groups and paired modality provenance are supported; local sampled counts require the sampling ledger. | PASS; methods narrowed to distinguish available cells from sampled analysis |
| `squair2021confronting` | [Primary text](https://pubmed.ncbi.nlm.nih.gov/34584091/); Abstract, second paragraph; Fig. 3 caption | DE methods ignoring variation between biological replicates are prone to false discoveries. This supports the DE warning; it does not validate donor-held-out classifier performance or mandate our precise bootstrap design. | NARROWED_AND_PASS; both uses distinguish our donor design from published DE findings |
| `hao2021integrated` | [Primary text](https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=34062119&retmode=xml); PubmedArticle/MedlineCitation/Article/Abstract/AbstractText; PMID 34062119 | WNN is an unsupervised framework learning each modality’s relative utility in each cell for multimodal integration. The abstract is sufficient for this general claim; no specific RNA–ATAC benchmark or algorithmic reproduction is attributed to it. | PASS; claim made source-specific |
| `argelaguet2020mofa` | [Primary text](https://link.springer.com/article/10.1186/s13059-020-02015-1); Abstract; Background paragraph beginning MOFA+, in contrast | MOFA+ provides scalable multimodal integration and uses a common sample space with measurements from the same cells. No superiority over our neural arms is claimed. | PASS |
| `ashuach2023multivi` | [Primary text](https://www.nature.com/articles/s41592-023-01909-9); Abstract; Main paragraphs describing paired and single-modality integration | MultiVI creates joint representations of multiomic data and accommodates missing modalities, integrating multimodal with single-modality datasets. | PASS |
| `vaswani2017attention` | [Primary text](https://arxiv.org/abs/1706.03762); Abstract; arXiv v7 viewed, first submitted 2017 | The Transformer uses attention for sequence transduction, without recurrence or convolutions. This is architectural background, not RNA–ATAC or donor-task evidence. | NARROWED_AND_PASS; separated from cross-modal applications |
| `tsai2019multimodal` | [Primary text](https://aclanthology.org/P19-1656/); Abstract, second paragraph | MulT uses directional pairwise cross-modal attention for unaligned multimodal language sequences. Donor bag adaptation is ours, not a reported application. | PASS |
| `nagrani2021attention` | [Primary text](https://arxiv.org/abs/2107.00135); Abstract, second paragraph; arXiv v3 viewed | Multimodal fusion bottlenecks require information exchange through a limited set of latent bottlenecks. Audio-visual results are not transferred to this biological task. The viewed revision notes an AudioSet metric correction; none of those numbers is cited here. | PASS |
| `ilse2018attention` | [Primary text](https://proceedings.mlr.press/v80/ilse18a.html); Abstract, first paragraph | MIL assigns a class to a bag of instances and uses a permutation-invariant attention aggregation operator. Donor bags are our application; this source does not validate donor biology or explanations for this study. | NARROWED_AND_PASS |
| `jain2019attention` | [Primary text](https://aclanthology.org/N19-1357/); Abstract, second and final paragraphs | On tested NLP tasks, attention distributions can disagree with gradient importance and different distributions can yield equivalent predictions; authors caution against treating standard attention as explanations. | NARROWED_AND_PASS; position attributed individually |
| `wiegreffe2019attention` | [Primary text](https://aclanthology.org/D19-1002/); Abstract, second through fourth paragraphs | Authors challenge blanket conclusions, tie explanation claims to definitions and whole-model tests, and propose diagnostics. Their position is not consensus that attention never explains. | NARROWED_AND_PASS; disagreement explicit |
| `ganin2015unsupervised` | [Primary text](https://proceedings.mlr.press/v37/ganin15.html); Abstract, second/third paragraphs | Domain-adaptation training promotes task-discriminative yet domain-invariant features using gradient reversal. Our conditional nuisance adversary is an adaptation, not evidence of successful removal in this cohort. | PASS |
| `ganin2016domain` | [Primary text](https://jmlr.org/papers/v17/15-239.html); Abstract, second/third paragraphs | Domain-adversarial learning uses gradient reversal to pursue task discrimination and domain indiscrimination. The grouped 2015/2016 citation independently supports this common motivation. | PASS |
| `oord2018representation` | [Primary text](https://arxiv.org/abs/1807.03748); Abstract, second paragraph; arXiv v2 viewed | Contrastive predictive coding uses a probabilistic contrastive objective and negative sampling for representations. It does not itself establish cross-modal RNA–ATAC pairing utility. | NARROWED_AND_PASS; paired with its own claim |
| `radford2021learning` | [Primary text](https://proceedings.mlr.press/v139/radford21a.html); Abstract, second paragraph | Predicting which caption matches an image learns transferable visual representations. Cross-modal matching motivates our pairing choice, without validating RNA–ATAC performance. | NARROWED_AND_PASS; image–text attribution explicit |
| `stuart2021signac` | [Primary text](https://pmc.ncbi.nlm.nih.gov/articles/PMC9255697/); Methods: PBMC multiome analysis / Multimodal label transfer | Signac counts fragments over each gene body and a 2-kb upstream region. Our implementation instead expands both genomic boundaries; the draft now states the distinction rather than claiming an identical window. | NARROWED_AND_PASS |
| `lee1999learning` | [Primary text](https://www.nature.com/articles/44565); Abstract, first/second paragraphs | NMF uses non-negativity constraints for additive representations, demonstrated on faces and text. Token construction in this study is our adaptation, not this paper’s biological result. | NARROWED_AND_PASS |

## Repeated and grouped claim coverage

| Original group | Location | Keys | Disposition |
|---|---|---|---|
| 1 | Original draft line 21 | lattke2026down | PASS against atlas results; processed availability and sampling distinguished |
| 2 | Original draft line 27 | lattke2026down | PASS against atlas results; processed availability and sampling distinguished |
| 3 | Original draft line 27 | squair2021confronting | Both DE-related uses narrowed: our classification/inference design is a choice, not validated by Squair |
| 4 | Original draft line 31 | hao2021integrated, argelaguet2020mofa, ashuach2023multivi | Every key evaluated individually; revised claims split where sources differ |
| 5 | Original draft line 31 | tsai2019multimodal, nagrani2021attention, vaswani2017attention | Every key evaluated individually; revised claims split where sources differ |
| 6 | Original draft line 31 | ilse2018attention | Every key evaluated individually; revised claims split where sources differ |
| 7 | Original draft line 31 | jain2019attention, wiegreffe2019attention | Every key evaluated individually; revised claims split where sources differ |
| 8 | Original draft line 31 | ganin2015unsupervised, ganin2016domain, oord2018representation, radford2021learning | Every key evaluated individually; revised claims split where sources differ |
| 9 | Original draft line 31 | stuart2021signac | Every key evaluated individually; revised claims split where sources differ |
| 10 | Original draft line 31 | lee1999learning | Every key evaluated individually; revised claims split where sources differ |
| 11 | Original draft line 35 | lattke2026down | PASS against atlas results; processed availability and sampling distinguished |
| 12 | Original draft line 35 | squair2021confronting | Both DE-related uses narrowed: our classification/inference design is a choice, not validated by Squair |
| 13 | Original draft line 68 | lattke2026down | PASS against atlas results; processed availability and sampling distinguished |
| 14 | Original draft line 82 | lattke2026down | PASS against atlas results; processed availability and sampling distinguished |

## Local-source boundary and surgical edits

- Atlas results establish 15 DS + 15 controls, 10X Multiome and 248,998 retained cells. `sampling_cap1000_seed22.json` independently has `primary.n_cells_available=248998`, `n_donors=30`, `cap=1000`, `seed=22`, `n_cells_selected=30000`. The draft now distinguishes available processed cells from the capped analysis; no numerical result changed.
- Squair’s DE findings motivate biological-replicate caution. Donor hold-out and donor-cluster inference remain this study’s design; literature does not guarantee generalization.
- Jain/Wiegreffe are opposing positions, now attributed separately. We do not infer a scientific consensus or explanations for our own weights.
- Split generic Transformer background from cross-modal applications, and adversarial learning from contrastive/image–text motivations. MIL donor bags and NMF tokens are our adaptations.
- Signac methods use gene body plus upstream region; `scripts/build_gene_activity_bed.py` defines `[max(0,start-flank),end+flank)`. Our window includes both flanks and is now distinguished. No code/feature generation was run.

## Access and resource limitations

Nature/Cell endpoints sometimes failed; PMC for Squair/Hao returned CAPTCHA and was not bypassed. Squair’s official PubMed abstract supplies the narrow DE statement. Hao’s official PubMed XML abstract supplied the general WNN statement after HTML/author-copy access failures. An author PDF fetch was rejected as oversized by the tool; no document body was retained. No full-paper reproduction claim is made for abstract-only checks.

See [NETWORK.json](NETWORK.json): primary acquisitions/search attempts, cached navigation operations, measured response representations and hidden HTTP limitations are recorded separately. The old ≈25/24 submission-prep ledger remains unchanged. This audit certifies citation support, not historical request-cap compliance.

## Verification

Both paper checkers returned exit 0, ok=true, failures=0; saved-prediction ladder replay returned exit 0, PASS, advantage=false. Protected-file rematch: **12/12**. Citation inventory: **17/17 keys, 22/22 revised key uses, 21 revised groups**. Provisional diff is limited to Introduction, Related Work and Methods; Abstract, Results, figures, accepted full/short drafts, frozen bib, claims and original MOM are unchanged. Human author/funding/ethics/venue/export inputs remain unresolved and cannot be inferred from this audit.

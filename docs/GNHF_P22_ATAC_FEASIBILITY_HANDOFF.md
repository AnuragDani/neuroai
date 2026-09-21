# P22 ATAC access & recount feasibility — GNHF handoff (iteration 3)

Worktree: `P22-gnhf-worktrees/p22-atac-access-and-b89c8a`
Initial HEAD: `8217719713c271349d1e54eda679672b82133a56` (matches expected base `8217719713c2`; `git merge-base --is-ancestor` confirms).
Contract hash verified `9a13d8be…113f2`; evidence-note hash verified `66b1d815…b18b9` (both rechecked at the start of this revision and match the prompt).
This is the only file this run writes. Paired status remains `SOURCE_UNRESOLVED`; the completed RNA result remains INCONCLUSIVE. No payload, fragment, R-object or binary bag was downloaded, read or ranged.

## 1. Decision summary

Iteration 3 resolved Package A from the pinned author pipeline and provider descriptions. **No provider-documented common-count export exists on any searched surface.** GEO `GSE305146` lists exactly 140 supplementary files (46 per-library triples + 2 `.rda.gz`); the SOFT does not enumerate assays, and each sample describes the objects only as "rda files containing the Seurat objects with labelled cell clusters and sample metadata (for complete dataset and filtered excitatory lineage cells)". The paper's Methods confirm the study's ATAC representation was the per-cluster `peaks_by_cluster` assay, produced only by the author-local `F01` script.

The pinned code shows the lineage: `B01` builds each library's ATAC assay from cellranger-arc `counts$Peaks` and merges with `merge.data = TRUE`; `B02`–`B04` and the `C` scripts never drop ATAC; `F01` loads `C03_seur_integr_labelled.rda` and needs `DefaultAssay = "ATAC"` plus `Fragments(seur)`. The labelled objects therefore almost certainly carry an ATAC assay — but it is the **pre-`F01` merged per-library peak space**, not a common measured region set. Signac's merging vignette states that merging `ChromatinAssay` objects without first quantifying a common peak set "can result in inaccuracies in the count matrix, as some peaks will be extended to cover regions that were not originally quantified" — exactly `B01`'s path. The deposited object cannot supply exact shared measured ATAC counts.

Dispositions: A **no documented common-count export; missing small artifact = `F01_peaks_by_cluster.bed`**. B both cohorts have fragments+index; within-library-only uniqueness. C worksheet complete. D leading-route counterexample unchanged. One next action: bounded fragment-header inspection.

## 2. Progress table (A–D)

| Package | Result | Open question | Next action |
|---|---|---|---|
| A. Documented development asset | **Resolved (iter 3).** No provider common-count export or assay inventory. 140 GEO files = 138 per-library + 2 rda; provider describes rda as labelled Seurat objects + metadata; pinned code shows the labelled object carries a `B01`-merged per-library ATAC peak space, not a common set. | Whether each deposited rda actually retains the ATAC assay and fragments (uninspected). | Author manifest question (§6) |
| B. Fragment access + barcode compatibility | Both cohorts have fragments+index and the same within-library-only uniqueness. External open release enumerated (8 files, 26,003,983,635 B). Access terms: collection `open`, per-file `embargo`. | Does the external fragment carry the `<donor>_<sample>_` prefix? Is the external tar remotely index-readable? | Bounded fragment-header inspection (§6) |
| C. Bounded cost/measurement proposal | Complete worksheet for candidate 2 on both cohorts; candidate 1 rejected cross-cohort. | Exact network bytes for a region query; peak/`nnz` counts. | Smallest measurement = one bounded region query |
| D. Verify + deliver one decision | Leading-route counterexample: external tar packaging + prefix risk; **new: `B01` merge-inaccuracy + no pre-`F01` common set**. | Which single validation to authorize. | Disposition in §5 |

## 3. Asset inventory

### Development cohort (Lattke; GRCh38)

| Asset | ID / URL | Version/date | Format | Bytes | Semantics | Label |
|---|---|---|---|---|---|---|
| GEO series `GSE305146` | `ftp.ncbi.nlm.nih.gov/geo/series/GSE305nnn/GSE305146/suppl/` | files 2025-07-31/08-11; series public 2025-12-23 | 140 files: 46 × barcodes/features/matrix + 2 `.rda.gz` | matrices ≈3.5 GB; rda 8.7 G + 7.6 G (rounded) | raw cellranger-arc counts; library-specific peaks | OBSERVED_NOW |
| `GSE305146_seur_integr_labelled_complete_dataset.rda.gz` | same suppl dir | listed 2025-08-11 11:39 | gzip R workspace | 8.7 G (rounded) | provider: labelled Seurat object + sample metadata, complete dataset | OBSERVED_NOW |
| `GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz` | same suppl dir | listed 2025-08-11 11:44 | gzip R workspace | 7.6 G (rounded) | provider: labelled Seurat object + sample metadata, filtered excitatory lineage | OBSERVED_NOW |
| CELLxGENE complete dataset | `cellxgene.cziscience.com/collections/0e9fd1d3-…` | revised 2026-06-11, schema 7.1.0 | H5AD + fragment + tbi | H5AD 1,569,658,860 B; fragment 25,514,837,002 B; tbi 5,339,155 B | H5AD RNA-only; fragment `46b43994-…-fragment.tsv.bgz`; assay label `10x multiome` | OBSERVED_NOW |
| CELLxGENE excitatory subset | same collection | schema 7.1.0 | H5AD only | 1,353,712,966 B | 215,680 cells; no fragment asset | OBSERVED_NOW |
| Local H5AD | `data/real/f16c25da-…h5ad` | — | H5AD backed | 1,569,658,860 B | 248,998 × 35,477 genes; obs `cell_id`=`<library>_<barcode>-1`; 37 libraries, 30 donors; `nCount_ATAC`/`nFeature_ATAC`/`nucleosome_signal`/`TSS.enrichment` present, 0 nulls | OBSERVED_NOW |
| `GSE305153` raw series | `…/GSE305153/suppl/` | 2025-12-24 | 10 counts tarballs | 276,449,280 B | no fragments | RECORDED_PREVIOUSLY |

### External cohort (Vuong / de la Torre-Ubieta; hg38)

| Asset | ID / URL | Access | Files | Bytes | Notes | Label |
|---|---|---|---|---|---|---|
| Meta-collection | `nemo:col-umstjg0` | restricted | 127 | 816,284,671,512 | children: ATAC/RNA × Open/Controlled | OBSERVED_NOW |
| ATAC open | `nemo:col-ad8t52b` | **open** | 8 | 26,003,983,635 | `Analysis_bag_3_…ATAC_Open.tgz` + HTTP dir | OBSERVED_NOW |
| **devctx ATAC fragments** | `…/counts/VuongWeber_2025_DSdevctx_atac_fragments_20260128.tsv.tar` | per-file `embargo` | `.tsv.gz` + `.tbi` | tar ≈19 G | hg38, CellRanger; MD5 frag `4731ccd4…`, tbi `8addb3bc…` | OBSERVED_NOW |
| devctx ATAC counts | `…/counts/VuongWeber_2025_DSdevctx_atac_counts_20260128.mex.tar.gz` | per-file `embargo` | barcodes/features/matrix | tar ≈1.4 G | features.tsv = author peak set; barcodes MD5 `777acd50…` | OBSERVED_NOW |
| ATAC controlled | `nemo:col-94h4ex9` | restricted | 54 | 503,156,799,793 | raw BAM | OBSERVED_NOW |
| RNA open | `nemo:col-mbgxwtz` | **open** | 11 | 1,098,158,155 | devctx+phNPC counts, metadata, PCA/UMAP | OBSERVED_NOW |
| RNA controlled | `nemo:col-yeq1r1g` | restricted | 54 | 286,025,729,929 | raw BAM | OBSERVED_NOW |

Unknown fields (stay unknown): external fragment barcode prefix; remote index behavior of the tar; devctx peak count; exact bytes of the two tars; whether each deposited `.rda.gz` retains RNA/SCT/ATAC/`peaks_by_cluster` assays; phNPC is an in-vitro model and is not a paired-input candidate.

## 4. Deposited-object, barcode, QC and count-semantics findings

### Package A: the two `.rda.gz` objects (new this iteration)

- GEO SOFT sample `data_processing` (all 92 samples) declares `cellranger-arc v2.0.2`, GRCh38, Seurat v5.1.0, Signac v1.13.0, and: "rda files containing the Seurat objects with labelled cell clusters and sample metadata (for complete dataset and filtered excitatory lineage cells)". No assay or feature-axis enumeration. `OBSERVED_NOW` (local `GSE305146_family.soft.gz`, sample lines).
- GEO suppl directory listing has 140 entries and **no checksum file**; rda sizes are rounded (`8.7G`, `7.6G`) and dated 2025-08-11. `OBSERVED_NOW`.
- Pinned tree search: no `.R` script contains the strings `complete_dataset` or `exc_lin_PCW10_20`. The pipeline's labelled checkpoints are `B04_seur_integr_labelled.rda` (all cells) and `C03_seur_integr_labelled.rda` (subset). The deposited names are author deposition aliases. `OBSERVED_NOW` (77 scripts fetched from `raw.githubusercontent.com/…/227f51b4…`).
- `B01` creates per-library ATAC via `CreateChromatinAssay(counts = counts$Peaks, fragments = fragpath, annotation = annotation)` and then `merge(…, merge.data = TRUE)`; `B02` subsets on ATAC QC but never removes the assay; `C01` subsets and re-integrates without `DietSeurat`; `F01` loads `C03_seur_integr_labelled.rda`, sets `DefaultAssay = "ATAC"`, calls `CallPeaks(group.by = "cluster_name")` and quantifies with `Fragments(seur)`. Hence the labelled object must retain an ATAC assay with fragment paths for the published pipeline to run. `OBSERVED_NOW` (pinned `B01`/`B02`/`C01`/`F01`).
- Signac's merging vignette (primary docs) states that merging `ChromatinAssay` objects without first quantifying a common peak set "can result in inaccuracies in the count matrix, as some peaks will be extended to cover regions that were not originally quantified", and recommends building a `reduce`d common peak set and quantifying it in each dataset **before** merging. `B01` does not follow that procedure. `OBSERVED_NOW` (stuartlab.org/signac/articles/merging).
- Nature Medicine Methods: peaks were called per cluster with `CallPeaks(group.by = "cluster_name")`, blacklist-filtered; the GRN used `atac.assay = "peaks_by_cluster"`. Data availability names GEO `GSE305153` and CELLxGENE only. `OBSERVED_NOW` (paper full text).
- `INFERENCE`: the deposited labelled objects likely carry the `B01`-merged per-library ATAC peak space (and possibly RNA/SCT), but **not** a common measured region set and **not** the `F01` `peaks_by_cluster` assay. The exact missing small artifact remains `F01_peaks_by_cluster.bed` plus `F01_seur_w_peaks_by_cluster_quant.rda` (author-local, absent from the complete public tree).
- Author manifest must answer exactly: which assays (RNA, SCT, ATAC, `peaks_by_cluster`) and which feature axis are present in each deposited rda; if ATAC is present, is its feature set a common quantified region set or a merge-extended union; and does either object carry the `F01` peak BED coordinates.

### Per-library matrix structure (reproduced)

Local `features.tsv.gz`: 36,601 `Gene Expression` rows in all three checked libraries plus library-specific `Peaks` — `B10C1Q` 46,672; `B17C2L` 22,676; `B10D1N` 20,708. So the GEO matrices are combined cellranger-arc exports with a library-specific peak axis, not a common region set. `OBSERVED_NOW`.

### Barcode uniqueness (decisive compatibility result)

- Dev: `cell_id` = `<library>_<barcode>-1`; 248,998 unique; prefix equals `library`; stripping yields 212,021 distinct strings with 33,139 collisions (max 5). `OBSERVED_NOW` (local H5AD, `.venv-p22`, obs only).
- External: `barcode` = `<donor>_<sample>_<barcode>-1`; 117,532 unique; stripping yields 109,336 distinct with 7,833 collisions (max 4). `OBSERVED_NOW` (local CSV).
- Consequence (`INFERENCE`): a concatenated fragment that stores raw per-library barcodes cannot be uniquely joined; a library-prefixed fragment can. `PROPOSED` join assertion: fragment barcode set ⊆ cohort allowlist and no duplicate keys, else refuse.

### Development join

- CELLxGENE schema 7.1.0 requires ATAC fragment barcode values to match the obs index. Because the dev H5AD obs index is `<library>_<barcode>-1`, the dev fragment is *expected* to be prefixed. `OBSERVED_NOW` (schema) → `INFERENCE` (payload).
- Pinned `B01` `RenameCells(add.cell.id = library)` matches the H5AD convention. `OBSERVED_NOW`.

### External join

- External devctx ATAC and RNA counts barcodes share MD5 `777acd5015ab7b76b42dddc78e29e1f4` → one joint paired barcode set. `OBSERVED_NOW`.
- The fragment file's own convention is separate from the counts MEX and was not inspected. `UNKNOWN`.
- 12 of 26 external donors have two `donor_sample` pairs; donor-aware splits must keep both libraries of a donor together. `OBSERVED_NOW`.

### QC

- Development QC thresholds are now confirmed in both the paper Methods and the pinned `B02` code: RNA `<500` or `>30,000` UMIs; mito `>2%`; ATAC `<100` or `25,000`; `nucleosome_signal > 2` or `TSS.enrichment < 1.1`; libraries with `>50%` low-quality cells or `<500` retained cells removed. `OBSERVED_NOW`.
- External: 117,532 metadata rows, 3,731 RNA `Unk`, 113,801 non-`Unk`; attempted threshold replay 113,242. Cause and final barcode membership remain unresolved. `RECORDED_PREVIOUSLY`.
- `nCount_ATAC` is non-zero for all 117,532 external rows and 0-null in the dev H5AD; neither released metadata column reproduces the authors' ATAC QC cut → `ANNOTATION_COUNT_MATCH_QC_UNVERIFIED`. `OBSERVED_NOW` (nulls) + `RECORDED_PREVIOUSLY`.

### Count semantics

- Dev GEO matrices: raw cellranger-arc counts on library-specific peaks; zero shared intervals across retained libraries. `RECORDED_PREVIOUSLY`.
- The `B01` merged ATAC assay is a merge-extended union whose counts Signac flags as potentially inaccurate; it is therefore **not** exact shared measured counts. `OBSERVED_NOW` (docs) + `INFERENCE` (payload).
- External devctx ATAC MEX `features.tsv` is a single author peak set; peak count and coordinate convention `UNKNOWN`; not established as identical to dev or `F01` peaks.
- Count unit for a recount = fragment overlap on a frozen region set; dedup/overlap rules are those the quantifier applies (Signac `FeatureMatrix`). `PROPOSED`.

## 5. Route comparison, cost worksheet and proposed pilot

### Route dispositions

- **A — documented common-count export: not found.** No provider common-count export or assay inventory on GEO, CELLxGENE, the paper, or the pinned tree. `OBSERVED_NOW`.
- **C — documented shared-count export: insufficient cross-cohort.** External single-feature ATAC MEX vs dev per-library peaks; feature spaces differ.
- **D — deposited object: unsupported for exact shared ATAC counts.** Even granting an ATAC assay, it is the `B01` merge-extended union, which Signac's own docs flag as inaccurate, and the published GRN used the separate `F01` `peaks_by_cluster` assay. `INFERENCE` (objects still uninspected).
- **E — recount on frozen regions: feasible for both, gated by fragment prefix + external tar indexing.** Dev source = CELLxGENE `.bgz`+`.tbi` (direct assets). External source = devctx `.tsv.gz`+`.tbi` **inside a tar**.
- **1 — 46-file intersection:** closed (zero shared intervals; do not re-run).

### Strongest counterexample to route E

The external fragment is packaged as `…tsv.tar`; a tabix index **inside a tar** is not a remotely range-queryable resource. A tar is sequential, so selective access likely collapses to streaming the ~19 GB tar, then extracting, then local tabix. If so, the external side costs a whole-asset transfer, not a block query. `OBSERVED_NOW` (paths) + `INFERENCE` (tar mechanics).

### Candidates (≤3)

1. **Documented shared-count export** — external devctx ATAC MEX + dev GEO per-library matrices. Rejected cross-cohort.
2. **Indexed fragment quantification on fixed regions** — dev: `46b43994-…-fragment.tsv.bgz` + `.tbi`; external: NeMO `…atac_fragments…tsv.gz` + `.tbi` (in tar). Join: library-prefixed allowlists (248,998 dev / 117,532 external). Count unit: fragment overlap. Output: sparse peaks × retained cells.
3. **Sequential/unindexed processing** — fallback if the tar or prefix blocks candidate 2; whole-asset transfer (~23.76 GiB dev; ~19 G external tar). Not proposed.

### Transparent cost worksheet (candidate 2)

| Resource | Known (provider-declared) | Unknown / smallest measurement |
|---|---|---|
| Network | dev fragment 25,514,837,002 B + tbi 5,339,155 B; external ATAC-open bag 26,003,983,635 B; devctx fragments tar ≈19 G; devctx counts tar ≈1.4 G | bytes fetched per region query (bgzf block density); whether external access needs the whole tar. A cell cap does **not** cap region bytes |
| Disk | — | downloaded asset + decoded temp + retained sparse output; peak coexistence not stated; compressed size does not bound expansion |
| RAM | — | decoded records + index + barcode hash (248,998 / 117,532 keys) + sparse nonzeros (`nnz` × 8 B index + 8 B data + quantifier overhead). Formula, no measurement |
| Time / money | — | UNKNOWN. Smallest measurement: one bounded region query on one dev library and one external sample, timed and byte-metered. No benchmark or price asserted |
| Controls | proposed caps only | what enforces each cap is unproven; estimate ≠ observed use |

### Proposed bounded pilot (not run)

Development-only, one retained library (e.g. `B17C2L`), frozen regions = training-fold peaks. Acceptance: fragment barcode set ⊆ the 248,998 allowlist with no duplicates; region-query byte count recorded; sparse output dimensions reproducible. Refusal: any unjoinable/duplicate barcode; any region query that requires whole-asset transfer; any need to zero-fill unmatched peaks. Cannot extrapolate one library's block density or timing to the pooled archive, nor dev behavior to the external tar. If one external sample cannot be isolated cheaply from the 19 GB tar, the external pilot is not cheap and should be stated as such.

### Feature policy (`PROPOSED`)

Build the common region set **once** from training-fold-only peaks; interval convention `chr:start-end` 0-based half-open (cellranger-arc); duplicates collapsed; count unit = fragment overlap. Overlap, zero-fill, imputation, merge-extension or peak-to-gene sums do **not** establish exact shared measured counts and need a separate proposal.

## 6. One next action and unsent artifact request

**Next action:** a separately-scoped, bounded fragment-header inspection — read the first few thousand lines (and the `.tbi` header) of the **external devctx** fragment and the dev CELLxGENE fragment to determine the barcode prefix convention and confirm the index layout. Input: the two fragment assets; output: barcode format (prefixed vs raw), index type, first-block byte size. Acceptance: barcodes resolve uniquely against the 248,998 / 117,532 allowlists. Refusal: raw collisions with no library prefix, or an index unreachable without whole-tar transfer. Dependency: none. Proposed allocation: bounded Range GET of the first few MB per asset (0 payload bytes this run). Remaining authority: none in this run to read payloads.

**Unsent request (do not send):**
> For the P22 paired-input review, please provide (1) the first 5 lines of `VuongWeber_2025_DSdevctx_atac_fragments_20260128.tsv.gz` and the first line of its `.tbi`, and confirm whether fragment barcodes carry the `<donor>_<sample>_` prefix; (2) the number of intervals in the `features.tsv` of `VuongWeber_2025_DSdevctx_atac_counts_20260128.mex.tar.gz`; and (3) for each `GSE305146_seur_integr_labelled_*.rda.gz`, the names of the assays it contains, and if an ATAC assay is present whether its feature set is a single common quantified region set or a merge-extended union. No cell-level counts are requested.

## 7. Claim / source ledger and search coverage

| # | Claim | Source (primary) | Section | Date | Label |
|---|---|---|---|---|---|
| 1 | NeMO meta `col-umstjg0` restricted, 127 files, 816,284,671,512 B | `assets.nemoarchive.org/api/collection/nemo:col-umstjg0` (via `r.jina.ai`) | JSON | 2026-09-21 | OBSERVED_NOW |
| 2 | ATAC open `col-ad8t52b` open, 8 files, 26,003,983,635 B | same, `/api/collection/nemo:col-ad8t52b` | JSON | 2026-09-21 | OBSERVED_NOW |
| 3 | External devctx fragments `.tsv.gz`+`.tbi`, 19 G tar, hg38, CellRanger, MD5s | NeMO counts dir + `col-ad8t52b-…-manifest.tsv` | rows | 2026-05-04 | OBSERVED_NOW |
| 4 | External devctx ATAC counts MEX 1.4 G with `features.tsv` | same dir listing | rows | 2026-05-04 | OBSERVED_NOW |
| 5 | devctx ATAC & RNA counts barcodes share MD5 `777acd50…` | both manifest TSVs | rows | 2026-05-04 | OBSERVED_NOW |
| 6 | ATAC controlled 54 files 503,156,799,793 B; RNA controlled 54 files 286,025,729,929 B; RNA open 11 files 1,098,158,155 B | NeMO collection APIs | JSON | 2026-09-21 | OBSERVED_NOW |
| 7 | Per-file `Access=embargo` while collection `access=open` | manifest TSVs vs collection API | — | 2026-05-04 / 2026-09-21 | OBSERVED_NOW |
| 8 | External barcodes `<donor>_<sample>_<bc>-1`, 117,532 unique, 7,833 raw collisions | local `VuongWeber_…_metadata_20260128.csv.gz` | `barcode` col | 2026-01-28 | OBSERVED_NOW |
| 9 | Dev `cell_id` `<library>_<bc>-1`, 248,998 unique, 33,139 raw collisions | local H5AD obs (`.venv-p22`) | `cell_id` | schema 7.1.0 | OBSERVED_NOW |
| 10 | CELLxGENE schema requires fragment barcodes = obs index | CELLxGENE schema 7.1.0 | ATAC standards | accessed 2026-09-21 | OBSERVED_NOW |
| 11 | Dev CELLxGENE fragment 25,514,837,002 B + tbi 5,339,155 B; subset H5AD-only | CELLxGENE curation API | `datasets[].assets` | revised 2026-06-11 | OBSERVED_NOW |
| 12 | Direct TLS to `*.nemoarchive.org` reset; `r.jina.ai` read path worked | `openssl s_client` / `curl` | — | 2026-09-21 | OBSERVED_NOW |
| 13 | External retained = 113,801 RNA non-`Unk`; replay 113,242 differs | Sept 8 evidence note; manuscript | §1 | 2026-09-08 | RECORDED_PREVIOUSLY |
| 14 | Dev GEO per-library peaks, zero shared intervals; rda rounded sizes | iter-1 handoff / Sept 8 note | — | — | RECORDED_PREVIOUSLY |
| 15 | External fragment barcodes prefixed; external tar not remotely index-readable | tar packaging + MEX convention | — | — | INFERENCE |
| 16 | GEO `GSE305146` suppl has 140 files (138 matrices + 2 rda), no checksum file; rda 8.7G/7.6G dated 2025-08-11 | live GEO suppl listing | HTML | 2026-09-21 | OBSERVED_NOW |
| 17 | Provider describes rda as "Seurat objects with labelled cell clusters and sample metadata"; cellranger-arc v2.0.2, GRCh38, Seurat v5.1.0, Signac v1.13.0 | local `GSE305146_family.soft.gz` | sample `data_processing` | series public 2025-12-23 | OBSERVED_NOW |
| 18 | No script in pinned tree writes `…complete_dataset`/`…exc_lin_PCW10_20`; outputs are `B04_`/`C03_seur_integr_labelled.rda` | `raw.githubusercontent.com/…/227f51b4…` (77 scripts) | grep | commit 227f51b4 | OBSERVED_NOW |
| 19 | `B01` builds ATAC from `counts$Peaks` + fragments, merges with `merge.data=TRUE`; B02/C01 never drop ATAC | pinned `B01`, `B02`, `C01` | lines | commit 227f51b4 | OBSERVED_NOW |
| 20 | `F01` loads `C03_seur_integr_labelled.rda`, needs `DefaultAssay="ATAC"` and `Fragments(seur)` | pinned `F01` | lines 28,40,57 | commit 227f51b4 | OBSERVED_NOW |
| 21 | Merging `ChromatinAssay` without a common peak set can produce an inaccurate count matrix | stuartlab.org/signac/articles/merging | "Merging without a common feature set" | accessed 2026-09-21 | OBSERVED_NOW |
| 22 | Paper Methods: `CallPeaks(group.by="cluster_name")`; GRN `atac.assay="peaks_by_cluster"`; Data availability names GSE305153 + CELLxGENE | Nature Med full text (via `r.jina.ai`) | Methods, Data availability | 2026 | OBSERVED_NOW |
| 23 | Dev QC thresholds (paper) match pinned `B02` code | paper Methods + pinned `B02` | lines 47–75 | 2026 / commit 227f51b4 | OBSERVED_NOW |
| 24 | Per-library features: 36,601 genes + peaks B10C1Q 46,672 / B17C2L 22,676 / B10D1N 20,708 | local `GSE305146_*_features.tsv.gz` | counts | — | OBSERVED_NOW |

**Search coverage (successful):** NeMO collection/file APIs and processed-dir listings (via `r.jina.ai`); both open-release manifest TSVs; CELLxGENE curation API; CELLxGENE schema docs; local GEO SOFT; live GEO suppl listing; Nature Medicine full text; GitHub tree API and 77 pinned `.R` scripts; Signac merging vignette; local external metadata CSV; local dev H5AD obs; local per-library features.
**Unsuccessful targeted searches:** direct `assets.nemoarchive.org`/`data.nemoarchive.org` (TLS reset); NeMO `/api/collection/…/files` returned empty `results`; no provider assay inventory or common-count export; no publisher checksum for the rda objects; no `complete_dataset`/`exc_lin_PCW10_20` string anywhere in the pinned tree. "Not found here" is not proof of absence.

**Word count:** under the 5,000-word ceiling. No dataset payloads, fragments, objects, packages, benchmarks, paid calls or author messages were used.

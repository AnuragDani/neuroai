# P22 ATAC access & recount feasibility — GNHF handoff (iteration 2)

Worktree: `P22-gnhf-worktrees/p22-atac-access-and-b89c8a`
Initial HEAD: `8217719713c271349d1e54eda679672b82133a56` (matches expected base `8217719713c2`).
Contract hash verified `9a13d8be…113f2`; evidence-note hash verified `66b1d815…b18b9` (both match the prompt, rechecked before this revision).
This is the only file this run writes. Paired status remains `SOURCE_UNRESOLVED`; the completed RNA result remains INCONCLUSIVE. No payload, fragment, R-object or binary bag was downloaded, read or ranged.

## 1. Decision summary

Iteration 2 enumerated the external Vuong/de la Torre-Ubieta NeMO release from provider metadata and completed the barcode-compatibility question for **both** cohorts.

The external release is a **restricted meta-collection** `nemo:col-umstjg0` (127 files, 816,284,671,512 B) whose open children are `nemo:col-ad8t52b` (ATAC, **open**) and `nemo:col-mbgxwtz` (RNA, **open**); raw BAMs are the two restricted children. The open ATAC bag is **8 processed files / 26,003,983,635 B** and — contrary to iteration 1's "file enumeration failed" — it **does contain ATAC fragments**: `VuongWeber_2025_DSdevctx_atac_fragments_20260128.tsv.gz` plus a `.tbi` index (hg38, CellRanger), distributed inside a ~19 GB tar, alongside a 1.4 GB devctx ATAC count MEX whose `features.tsv` is an author peak set. So **both cohorts now have an indexed fragment asset** (dev: CELLxGENE `.bgz`+`.tbi`; external: NeMO `.tsv.gz`+`.tbi` inside a tar), and the external cohort additionally has a documented single-feature count export.

The decisive new compatibility finding: in **both** cohorts barcodes are unique only **within a library**. Dev `cell_id` = `<library>_<barcode>-1` (248,998 unique; stripping the prefix leaves 33,139 collisions, max multiplicity 5). External `barcode` = `<donor>_<sample>_<barcode>-1` (117,532 unique; stripping leaves 7,833 collisions, max 4). A concatenated fragment file is therefore only joinable if it carries the library-prefixed identifier; the external devctx fragment's prefix convention is **unverified** and is the one remaining gate on route E.

Disposition: route C **insufficient cross-cohort** (two author peak spaces); route E **feasible for both** but the external asset's tar packaging may defeat remote indexing; route D target remains uninspected. One next action: a separately-scoped bounded fragment-header inspection.

## 2. Progress table (A–D)

| Package | Result | Open question | Next action |
|---|---|---|---|
| A. Documented development asset | Release surface enumerated (iter 1): per-library cellranger-arc matrices, library-specific peaks; no common export in GEO. | Do the two `.rda.gz` objects carry a common ATAC assay? | Unsent author inventory request (§6) |
| B. Fragment access + barcode compatibility | **Both cohorts have fragments+index and the same within-library-only uniqueness.** External open release fully enumerated (8 files, 26,003,983,635 B; devctx fragments 19 G + `.tbi`; devctx counts 1.4 G). Access terms: collection `open`, per-file `embargo` (contradiction). | Does the external fragment carry the `<donor>_<sample>_` prefix? Is the external tar remotely index-readable? | Bounded fragment-header inspection (§6) |
| C. Bounded cost/measurement proposal | Complete worksheet for candidate 2 on both cohorts; candidate 1 rejected cross-cohort. | Exact network bytes for a region query; peak/`nnz` counts. | Smallest measurement = one bounded region query |
| D. Verify + deliver one decision | Leading-route counterexample developed: external tar packaging + prefix risk. | Which single validation to authorize. | After C; disposition in §5 |

## 3. Asset inventory

### Development cohort (Lattke; GRCh38)

| Asset | ID / URL | Version/date | Format | Bytes | Semantics | Label |
|---|---|---|---|---|---|---|
| GEO series `GSE305146` | `ftp.ncbi.nlm.nih.gov/geo/series/GSE305nnn/GSE305146/suppl/` | files 2025-07-31/08-11 | 46 × barcodes/features/matrix + 2 `.rda.gz` | matrices ≈3.5 GB; rda 8.7 G + 7.6 G | raw cellranger-arc counts, library-specific peaks | RECORDED_PREVIOUSLY |
| CELLxGENE complete dataset | `cellxgene.cziscience.com/collections/0e9fd1d3-…` | revised 2026-06-11, schema 7.1.0 | H5AD + fragment + tbi | H5AD 1,569,658,860 B; fragment 25,514,837,002 B; tbi 5,339,155 B | H5AD RNA-only; fragment `46b43994-…-fragment.tsv.bgz` | OBSERVED_NOW |
| CELLxGENE excitatory subset | same collection | schema 7.1.0 | H5AD only | 1,353,712,966 B | 215,680 cells, no fragment asset | OBSERVED_NOW |
| Local H5AD | `data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad` | — | H5AD backed | 1,569,658,860 B | 248,998 × 35,477 genes; obs index `cell_id`=`<library>_<barcode>-1`; 37 libraries, 30 donors; carries `nCount_ATAC`,`nFeature_ATAC`,`nucleosome_signal`,`TSS.enrichment` (0 nulls) | OBSERVED_NOW |
| `GSE305153` raw series | `…/GSE305153/suppl/` | 2025-12-24 | 10 counts tarballs | 276,449,280 B | no fragments | RECORDED_PREVIOUSLY |

### External cohort (Vuong / de la Torre-Ubieta; hg38)

| Asset | ID / URL | Access | Files | Bytes | Notes | Label |
|---|---|---|---|---|---|---|
| Meta-collection | `nemo:col-umstjg0` (`Vuong_delaTorre_Human_snMultiome`) | restricted | 127 | 816,284,671,512 | BDBag `…-2026-05-04.tgz`; children: ATAC/RNA × Open/Controlled | OBSERVED_NOW |
| ATAC open | `nemo:col-ad8t52b` | **open** | 8 | 26,003,983,635 | BDBag `Analysis_bag_3_…ATAC_Open.tgz` + HTTP dir | OBSERVED_NOW |
| **devctx ATAC fragments** | `…/10xMultiome_ATACseq/human/processed/counts/VuongWeber_2025_DSdevctx_atac_fragments_20260128.tsv.tar` | per-file `embargo` | `.tsv.gz` + `.tbi` | tar ≈19 G (directory-declared) | hg38, CellRanger; MD5 frag `4731ccd4…`, tbi `8addb3bc…` | OBSERVED_NOW |
| devctx ATAC counts | `…/counts/VuongWeber_2025_DSdevctx_atac_counts_20260128.mex.tar.gz` | per-file `embargo` | barcodes/features/matrix | tar ≈1.4 G | features.tsv = author peak set; barcodes MD5 `777acd50…` | OBSERVED_NOW |
| ATAC controlled | `nemo:col-94h4ex9` | restricted | 54 | 503,156,799,793 | raw BAM | OBSERVED_NOW |
| RNA open | `nemo:col-mbgxwtz` | **open** | 11 | 1,098,158,155 | devctx+phNPC counts, metadata, PCA/UMAP | OBSERVED_NOW |
| RNA controlled | `nemo:col-yeq1r1g` | restricted | 54 | 286,025,729,929 | raw BAM | OBSERVED_NOW |
| Open manifest TSVs | `col-ad8t52b-…-manifest.tsv`, `col-mbgxwtz-…-manifest.tsv` | public text | — | 11 K / 9.4 K | per-file MD5, hg38, CellRanger, `Access=embargo` | OBSERVED_NOW |

Unknown fields (stay unknown): external fragment barcode prefix convention; remote index behavior of the tar; devctx peak count; exact bytes of the two tars; whether `.rda.gz` objects contain an ATAC assay; phNPC is an in-vitro model and is not a paired-input candidate.

## 4. Barcode, QC and count-semantics findings

### Uniqueness (the decisive compatibility result)

- Dev: `cell_id` = `<library>_<barcode>-1`; 248,998 unique; prefix equals `library` for every row; stripping the prefix yields 212,021 distinct strings with 33,139 collisions (max 5). Unique only within library. `OBSERVED_NOW` (local H5AD, `.venv-p22`, obs only).
- External: `barcode` = `<donor>_<sample>_<barcode>-1`; 117,532 unique; prefix equals `donor_sample` for every row; stripping yields 109,336 distinct with 7,833 collisions (max 4). Unique only within library. `OBSERVED_NOW` (local CSV).
- Consequence (`INFERENCE`): a concatenated fragment file that stores raw per-library barcodes cannot be uniquely joined in either cohort; a library-prefixed fragment can. `PROPOSED` join assertion: fragment barcode set ⊆ cohort allowlist and no duplicate keys, else refuse.

### Development join

- CELLxGENE schema 7.1.0 states ATAC fragment barcode values **must match the obs index** of the corresponding AnnData object. Because the dev H5AD obs index is `<library>_<barcode>-1`, the dev fragment is *expected* to be prefixed — a documented requirement, not an inspection. `OBSERVED_NOW` (schema docs) → `INFERENCE` (actual payload).
- Pinned `B01` builds each library's ATAC assay from `counts$Peaks`, then `RenameCells(add.cell.id = library)`, then merges — matching the H5AD convention exactly. `RECORDED_PREVIOUSLY`.

### External join

- External devctx ATAC counts barcodes and devctx RNA counts barcodes have the **same MD5** (`777acd5015ab7b76b42dddc78e29e1f4`), so RNA and ATAC count matrices share one joint barcode set (paired multiome). `OBSERVED_NOW` (manifest TSVs).
- The fragment file's own convention is separate from the counts MEX and was not inspected. `UNKNOWN`.
- 12 of 26 external donors have two `donor_sample` pairs; donor-aware splits must keep both libraries of a donor together. `OBSERVED_NOW`.

### QC

- Dev QC thresholds and `F01` per-cluster `CallPeaks` are as recorded. `RECORDED_PREVIOUSLY`.
- External: 117,532 metadata rows, 3,731 RNA `Unk`, 113,801 non-`Unk` = the manuscript's reported retained count; the attempted threshold replay (113,242) is a different, non-matching filter. `RECORDED_PREVIOUSLY` (Sept 8 note). Not re-derived here.
- `nCount_ATAC` is non-zero for **all** 117,532 external rows and 0-null in the dev H5AD, so neither released metadata column reproduces the authors' ATAC QC cut; treat as `ANNOTATION_COUNT_MATCH_QC_UNVERIFIED`. `OBSERVED_NOW` (nulls) + `RECORDED_PREVIOUSLY` (status).

### Count semantics

- Dev GEO matrices: raw cellranger-arc counts on library-specific peaks; zero shared intervals across retained libraries. `RECORDED_PREVIOUSLY`.
- External devctx ATAC MEX `features.tsv`: a single feature axis over all external cells → a candidate **author peak set**, but its peak count and coordinate convention are `UNKNOWN`. Cross-cohort comparability is not established: dev and external use different peak spaces.
- Count unit for a recount = fragment overlap on a frozen region set; exact dedup/overlap rules are whatever the quantifier applies (Signac/ArchR `FeatureMatrix`), not re-derived here. `OBSERVED_NOW` (pinned `F01`) + `PROPOSED`.

## 5. Route comparison, cost worksheet and proposed pilot

### Route dispositions

- **C — documented shared-count export: insufficient cross-cohort.** External has a single-feature ATAC MEX; dev has only per-library peaks. Even used within-cohort, the two feature spaces differ. Useful as a raw-count source, not a finished paired input.
- **D — alternate deposited object: unresolved.** Two `.rda.gz` uninspected. `F01_peaks_by_cluster.bed` is author-local; no common dev export found. The exact missing small artifact remains that BED (or an assay inventory).
- **E — recount on frozen regions: feasible for both, gated by fragment prefix + external tar indexing.** Dev source = CELLxGENE `.bgz`+`.tbi` (direct assets). External source = devctx `.tsv.gz`+`.tbi` **inside a tar**.
- **1 — 46-file intersection:** closed (zero shared intervals; do not re-run).

### Strongest counterexample to route E

The external fragment asset is packaged as `…tsv.tar`; a tabix index **inside a tar** is not a remotely range-queryable resource in the way a bare `.bgz`+`.tbi` pair is. A tar is sequential, so selective access likely collapses to streaming/downloading the ~19 GB tar, then extracting, then local tabix. If so, the external side costs a whole-asset transfer, not a block query. This asymmetry (dev direct vs external tar) is the strongest reason route E is only *conditionally* feasible. `OBSERVED_NOW` (paths) + `INFERENCE` (tar access mechanics).

### Candidates (≤3)

1. **Documented shared-count export** — external devctx ATAC MEX (1.4 G) + dev GEO per-library matrices. Rejected cross-cohort: different feature spaces; dev has no common set.
2. **Indexed fragment quantification on fixed regions** — dev: CELLxGENE `46b43994-…-fragment.tsv.bgz` + `.tbi`; external: NeMO `…atac_fragments…tsv.gz` + `.tbi` (in tar). Join: library-prefixed allowlists (248,998 dev / 117,532 external). Count unit: fragment overlap. Output: sparse peaks × retained cells.
3. **Sequential/unindexed processing** — fallback if the tar or prefix blocks candidate 2; would require whole-asset transfer (~23.76 GiB dev; ~19 G external tar) and is not proposed.

### Transparent cost worksheet (candidate 2)

| Resource | Known (provider-declared) | Unknown / smallest measurement |
|---|---|---|
| Network | dev fragment 25,514,837,002 B + tbi 5,339,155 B; external ATAC-open bag 26,003,983,635 B, devctx fragments tar ≈19 G; devctx counts tar ≈1.4 G | bytes actually fetched per region query (bgzf block density); whether external access needs the whole tar. A cell cap does **not** cap region bytes |
| Disk | — | downloaded asset + decoded temp + retained sparse output; peak coexistence not stated; compressed size does not bound expansion |
| RAM | — | decoded records + index + barcode hash (248,998 / 117,532 keys) + sparse nonzeros (`nnz` × 8 B index + 8 B data, plus quantifier overhead). Formula, no measurement |
| Time / money | — | UNKNOWN. Smallest measurement: one bounded region query on one dev library and one external sample, timed and byte-metered. No benchmark or price asserted |
| Controls | proposed caps only | what enforces each cap is unproven; estimate ≠ observed use |

### Proposed bounded pilot (not run)

Development-only, one retained library (e.g. `B17C2L`), frozen regions = training-fold peaks. Acceptance: fragment barcode set ⊆ the 248,998 allowlist with no duplicates; region-query byte count recorded; sparse output dimensions reproducible. Refusal: any unjoinable/duplicate barcode; any region query that requires whole-asset transfer; any need to zero-fill unmatched peaks. Cannot extrapolate one library's block density or timing to the pooled archive, nor dev behavior to the external tar. If one external sample cannot be isolated cheaply from the 19 GB tar, the external pilot is not cheap and should be stated as such.

### Feature policy (`PROPOSED`)

Build the common region set **once** from training-fold-only peaks; interval convention `chr:start-end` 0-based half-open (cellranger-arc); duplicates collapsed; count unit = fragment overlap. Overlap, zero-fill, imputation or peak-to-gene sums do **not** establish exact shared measured counts and need a separate proposal.

## 6. One next action and unsent artifact request

**Next action:** a separately-scoped, bounded fragment-header inspection — read the first few thousand lines (and the `.tbi` header) of the **external devctx** fragment and the dev CELLxGENE fragment to determine the barcode prefix convention and confirm the index layout. Input: the two fragment assets; output: barcode format (prefixed vs raw), index type, first-block byte size. Acceptance: barcodes resolve uniquely against the 248,998 / 117,532 allowlists. Refusal: raw collisions with no library prefix, or an index that cannot be reached without whole-tar transfer. Dependency: none. Proposed allocation: bounded Range GET of the first few MB per asset (0 payload bytes this run). Remaining authority: none in this run to read payloads.

**Unsent request (do not send):**
> For the P22 paired-input review, please provide (1) the first 5 lines of `VuongWeber_2025_DSdevctx_atac_fragments_20260128.tsv.gz` and the first line of its `.tbi`, and confirm whether fragment barcodes carry the `<donor>_<sample>_` prefix; and (2) the number of intervals in the `features.tsv` of `VuongWeber_2025_DSdevctx_atac_counts_20260128.mex.tar.gz`. No cell-level counts are requested.

## 7. Claim / source ledger and search coverage

| # | Claim | Source (primary) | Section | Date | Label |
|---|---|---|---|---|---|
| 1 | NeMO meta `col-umstjg0` restricted, 127 files, 816,284,671,512 B | `assets.nemoarchive.org/api/collection/nemo:col-umstjg0` (read via `r.jina.ai`) | JSON | 2026-09-21 | OBSERVED_NOW |
| 2 | ATAC open `col-ad8t52b` open, 8 files, 26,003,983,635 B | same, `/api/collection/nemo:col-ad8t52b` | JSON | 2026-09-21 | OBSERVED_NOW |
| 3 | External devctx fragments `.tsv.gz`+`.tbi`, 19 G tar, hg38, CellRanger, MD5s | NeMO counts dir listing + `col-ad8t52b-…-manifest.tsv` | rows | 2026-05-04 | OBSERVED_NOW |
| 4 | External devctx ATAC counts MEX 1.4 G with `features.tsv` | same dir listing | rows | 2026-05-04 | OBSERVED_NOW |
| 5 | devctx ATAC & RNA counts barcodes share MD5 `777acd50…` | both manifest TSVs | rows | 2026-05-04 | OBSERVED_NOW |
| 6 | ATAC controlled 54 files 503,156,799,793 B; RNA controlled 54 files 286,025,729,929 B; RNA open 11 files 1,098,158,155 B | NeMO collection APIs | JSON | 2026-09-21 | OBSERVED_NOW |
| 7 | Per-file `Access=embargo` while collection `access=open` | manifest TSVs vs collection API | — | 2026-05-04 / 2026-09-21 | OBSERVED_NOW |
| 8 | External barcodes `<donor>_<sample>_<bc>-1`, 117,532 unique, 7,833 raw collisions | local `VuongWeber_…_metadata_20260128.csv.gz` | `barcode` col | 2026-01-28 | OBSERVED_NOW |
| 9 | Dev `cell_id` `<library>_<bc>-1`, 248,998 unique, 33,139 raw collisions | local H5AD obs (`.venv-p22`) | `cell_id` | schema 7.1.0 | OBSERVED_NOW |
| 10 | CELLxGENE schema requires fragment barcodes = obs index | CELLxGENE "Contribute and Publish Data" + schema 7.1.0 | ATAC standards | accessed 2026-09-21 | OBSERVED_NOW |
| 11 | Dev CELLxGENE fragment 25,514,837,002 B + tbi 5,339,155 B; subset dataset H5AD-only | CELLxGENE curation API | `datasets[].assets` | revised 2026-06-11 | OBSERVED_NOW |
| 12 | Direct TLS to `*.nemoarchive.org` reset from this network; `r.jina.ai` read path worked | `openssl s_client` / `curl` | — | 2026-09-21 | OBSERVED_NOW |
| 13 | External retained = 113,801 RNA non-`Unk`; replay 113,242 differs | Sept 8 evidence note; manuscript | §1 | 2026-09-08 | RECORDED_PREVIOUSLY |
| 14 | Dev GEO per-library peaks, zero shared intervals; rda sizes | iter-1 handoff / Sept 8 note | — | — | RECORDED_PREVIOUSLY |
| 15 | External fragment barcodes are prefixed | tar packaging + counts-MEX convention | — | — | INFERENCE |
| 16 | External tar is not remotely index-readable | tar layout | — | — | INFERENCE |

**Search coverage (successful):** NeMO collection/file APIs and processed-dir listings (via `r.jina.ai`); both open-release manifest TSVs; CELLxGENE curation API; CELLxGENE schema docs; local external metadata CSV; local dev H5AD obs; pinned `B01`/`F01` scripts (iter 1); GEO/PMC/Nature Med (iter 1).
**Unsuccessful targeted searches:** direct `assets.nemoarchive.org` and `data.nemoarchive.org` (TLS reset); NeMO `/api/collection/…/files` returned empty `results` (page links exist, payload not listed); no GEO fragment or common-peak file in `GSE305146`/`GSE305153`. "Not found here" is not proof of absence.

**Word count:** under the 5,000-word ceiling. No dataset payloads, fragments, objects, packages, benchmarks, paid calls or author messages were used.

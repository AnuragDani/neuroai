# P22 ATAC access & recount feasibility — GNHF handoff (iteration 1)

Worktree: `P22-gnhf-worktrees/p22-atac-access-and-b89c8a`
Initial HEAD: `8217719713c271349d1e54eda679672b82133a56` (matches expected base `8217719713c2`).
Contract hash verified `9a13d8be…113f2`; evidence-note hash verified `66b1d815…b18b9` (both match the prompt).
This document is the only file created by this run so far. Paired status remains `SOURCE_UNRESOLVED`; the RNA result remains INCONCLUSIVE.

## 1. Decision summary

The provider's release surface is now enumerated from primary sources, and it changes the route analysis.

GEO `GSE305146` publishes, per library, a **cellranger-arc-2.0.2 combined count matrix** whose feature axis contains **36,601 genes plus library-specific ATAC peaks** (inspected: B10C1Q 46,672 peaks; B17C2L 22,676; B10D1N 20,708). So a documented sparse ATAC count export *does* exist — but each library uses its own peak set, so it supplies **no common measured region set** and cannot satisfy the route-C common-region contract by itself. No fragment file, no shared peak matrix, and no F01 output are present in `GSE305146` or `GSE305153`.

The author's pinned `F01` script calls peaks on the *merged* object grouped by `cluster_name`, exports one BED, and quantifies counts on that single peak set via `FeatureMatrix`. That is a genuine common-count artifact — but it is saved to an **author-local RDS path**, not deposited. The exact missing small artifact is therefore `F01_peaks_by_cluster.bed`.

The development cohort has an open, **indexed** CELLxGENE fragment asset (25,514,837,002 bytes + 5,339,155-byte tabix index) over 248,998 cells whose `obs_names` are `<library>_<barcode>-1` (unique, 37 libraries / 30 donors). This is a viable frozen-region recount input for development. The external NeMO open-ATAC collection was identified but its file list could not be retrieved this iteration.

Disposition: route C is **partially satisfied but insufficient** (no common regions); route D target remains uninspected (now with live sizes 7.6 G / 8.7 G); route E is **newly feasible for development only**. One next action: request the F01 BED and an assay inventory.

## 2. Progress table (A–D)

| Package | Result this iteration | Open question | Next action |
|---|---|---|---|
| A. Documented development asset | Release surface enumerated. Per-library cellranger-arc matrices contain ATAC peaks on **library-specific** intervals; F01 common BED is author-local. No fragments/shared peaks in GEO. | Do the two deposited `.rda.gz` objects carry an ATAC assay, and is it per-library peaks or a common set? | Obtain assay inventory (unsent request, §6) |
| B. Fragment access + barcode compatibility | Development: CELLxGENE indexed concatenated fragment + H5AD join identified; barcode convention `<library>_<barcode>-1`. External: NeMO open ATAC collection `nemo:col-ad8t52b` identified; **file enumeration failed** (transport error). | External fragment asset identity, index, barcode/multiplexing map, count fields. | Retry documented NeMO files API (metadata only) |
| C. Bounded cost/measurement proposal | Partial worksheet only (§5). Candidate 1 (shared-count export) now known **insufficient**. Candidate 2 (indexed fragment quantification) viable for development. | External candidate; exact network/disk/RAM under caps. | Complete in iteration 2–3 |
| D. Verify + deliver one decision | Not yet reached. Leading-route counterexample partially developed (§5). | Which route to validate with a bounded pilot. | After C |

## 3. Asset inventory

### Development cohort (Lattke; GRCh38)

| Asset | ID / URL | Version/date | Format | Bytes | Semantics | Notes |
|---|---|---|---|---|---|---|
| GEO series `GSE305146` | `ftp.ncbi.nlm.nih.gov/geo/series/GSE305nnn/GSE305146/suppl/` | live listing, files dated 2025-07-31/08-01 | 46 × (`barcodes.tsv.gz`, `features.tsv.gz`, `matrix.mtx.gz`) + 2 `.rda.gz` | matrices ≈ 3.5 GB total; `rda` 8.7 G + 7.6 G | raw cellranger-arc counts (integer `general`) | `OBSERVED_NOW` |
| Per-library matrix | e.g. `…_B17C2L_matrix.mtx.gz` | 2025-08-01 | MatrixMarket | 4.8 M (B17C2L) | combined GEX+ATAC raw counts | header `cellranger-arc-2.0.2`, dims 59,277 × 652 |
| Per-library features | `…_B10C1Q_features.tsv.gz` etc. | 2025-08-01 | TSV | 1.1–3.4 M | 36,601 `Gene Expression` + peaks (`chr:start-end`, type `Peaks`) | 3 of 46 inspected; peaks B10C1Q 46,672 / B17C2L 22,676 / B10D1N 20,708 |
| Deposited object 1 | `GSE305146_seur_integr_labelled_complete_dataset.rda.gz` | 2025-08-11 | gzip R workspace | 8.7 G | uninspected | `OBSERVED_NOW` size only |
| Deposited object 2 (selected target) | `GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz` | 2025-08-11 | gzip R workspace | 7.6 G | uninspected | contract's declared "7.6G" now confirmed live |
| CELLxGENE collection | `cellxgene.cziscience.com/collections/0e9fd1d3-…` | revised 2026-06-11, schema 7.1.0 | H5AD + fragment + tbi | H5AD 1,569,658,860 B; fragment 25,514,837,002 B; tbi 5,339,155 B | H5AD RNA only (`feature_biotype: gene`, `raw.X`); fragment `M03_ATAC_fragments_concat.tsv.gz` | `ATAC_FRAGMENT` + `ATAC_INDEX` asset types |
| Author code | `github.com/lattkem1/Down_Syndrome_Multiome@227f51b4` | pinned | scripts/CSV/PDF only | — | no `.rda`/`.bed` data assets in tree | `OBSERVED_NOW` |
| `GSE305153` raw series | `…/GSE305153/suppl/` | 2025-12-24 | `GSE305153_RAW.tar` 276,449,280 B + `filelist.txt` | 264 M | 10 per-sample `*_counts_matrix.tar.gz`; **no fragments** | `OBSERVED_NOW` |

### External cohort (Vuong / de la Torre-Ubieta)

| Asset | ID / URL | Status | Notes |
|---|---|---|---|
| NeMO metacollection | `nemo:col-umstjg0` (`Vuong_delaTorre_Human_snMultiome`) | exists | children: RNA/ATAC × Open/Controlled |
| Open ATAC | `nemo:col-ad8t52b` (`Human_Analysis_snATAC-seq_Open`) | identified | landing page + `/api/collection/…` returned **transport error**; `/files?page=1&page_size=100` returned empty `results` |
| Open RNA | `nemo:col-mbgxwtz` | identified | not enumerated |
| Controlled ATAC / RNA | `nemo:col-94h4ex9` / `nemo:col-yeq1r1g` | identified | access terms not established |
| Processed counts dir | `data.nemoarchive.org/other/grant/r21_delatorre/…/processed/counts/` | **transport error** | could not list |
| Manuscript | `science.org/doi/10.1126/science.aea1259` (2026-04-23); PMC13225313 | read previously | 26 donors; QC and count reconciliation already recorded |

Unknown fields (stay unknown): external fragment asset identity, index presence, byte sizes, barcode prefix/suffix/multiplexing map, count fields and dedup rules; deposited-object assay inventory.

## 4. Barcode, QC and count semantics

### Development join

- H5AD `obs_names` = `cell_id` = `<library>_<barcode>-1` (e.g. `B10C1Q_AAACAGCCAACTAGCC-1`); 248,998 unique values; 37 `library` categories, 30 `donor_id`/`sample_name` categories, 2 `group` (CON/DS). `OBSERVED_NOW` (local H5AD metadata read with `.venv-p22`; no count arrays materialized).
- Pinned `B01` builds each library's ATAC assay from `counts$Peaks`, then `RenameCells(add.cell.id = library)`, then `merge(…, merge.data = TRUE)`. So the merged cell naming convention is exactly the H5AD convention, and the per-library fragment path is author-local `…/outs/atac_fragments.tsv.gz`. `OBSERVED_NOW`.
- Proposed join assertion (not run): fragment barcode set should equal the H5AD `cell_id` set; any barcode not in the 248,998 allowlist, or any duplicate `cell_id`, refuses the join. Because the CELLxGENE file is *concatenated*, the working assumption that it carries the same `<library>_<barcode>-1` string is `INFERENCE`, not proof — the fragment payload was not inspected.

### QC

- Development QC (paper Methods + `B01`): RNA UMI <500 or >30,000; `percent.mt` >2%; ATAC counts <100 or >25,000; `nucleosome_signal` >2; TSS enrichment <1.1; datasets >50% low-quality or <500 retained cells dropped. `OBSERVED_NOW`.
- External QC reconciliation remains unresolved (`RECORDED_PREVIOUSLY`): 117,532 metadata rows, 113,801 RNA non-`Unk`, 113,242 after the attempted replay. Cause and final rule stay UNKNOWN.

### Count semantics

- Development GEO matrices are **raw** cellranger-arc counts on **library-specific** peaks (`INFERENCE` for the 43 unread files; `OBSERVED_NOW` for 3). No shared region axis exists across retained libraries; B10C1Q and B17C2L share zero intervals (`RECORDED_PREVIOUSLY`).
- `F01` produces a single common peak set: `CallPeaks(object = seur, group.by = "cluster_name")` on the merged excitatory-lineage object, `keepStandardChromosomes` + blacklist removal, `export(peaks, F01_peaks_by_cluster.bed)`, then `FeatureMatrix(fragments = Fragments(seur), features = peaks, cells = colnames(seur))`. `OBSERVED_NOW` (pinned script). Count unit = fragment overlap on MACS2 consensus peaks; exact dedup/overlap rules are whatever Signac `FeatureMatrix` applies, not re-derived here.

## 5. Route comparison, cost worksheet and proposed pilot

### Route dispositions

- **C (documented sparse export): insufficient as a standalone.** A documented ATAC sparse export now exists (per-library combined matrices), but it cannot satisfy "exact common measured regions" without re-quantification. It is a useful **raw-count source** for a recount, not a finished paired input.
- **D (alternate deposited object): unresolved.** The two `.rda.gz` objects remain uninspected; live sizes confirmed. The `F01` common-count artifact is upstream of neither object's filename and is saved to an author-local path → the exact missing artifact is `F01_peaks_by_cluster.bed` (+ optionally the F01 rda).
- **E (recount proposal): newly feasible for development.** Frozen regions (from F01 BED) + the indexed CELLxGENE fragment + the H5AD allowlist form an end-to-end chain. External cohort remains unresolved pending NeMO enumeration.

### Candidate routes (≤3)

1. **Shared-count export** — GEO per-library matrices. Rejected: separate feature spaces; zero shared intervals across retained libraries. No new download needed to reject.
2. **Indexed fragment quantification on fixed regions (development)** — source: CELLxGENE `46b43994-…-fragment.tsv.bgz` + `.tbi`; acquisition unit: bgzf blocks for the frozen BED regions; join: `<library>_<barcode>-1` allowlist; count unit: fragment overlap; output: sparse peaks × retained cells. Preferred if F01 BED is obtained.
3. **Sequential/unindexed processing** — fallback only if the tbi/region mechanism is shown unusable; would require whole-asset transfer (≈23.76 GiB) and is not proposed.

### Transparent cost worksheet (candidate 2; unknowns stated, no invented throughput)

| Resource | Known | Unknown / required measurement |
|---|---|---|
| Network transfer | fragment asset 25,514,837,002 B; tbi 5,339,155 B (provider-declared) | bytes actually fetched for a region query (depends on block density; a cell cap does **not** cap region bytes) |
| Disk | — | downloaded bgzf, decoded temp, retained sparse output; peak coexistence not stated; compressed size does not bound expansion |
| RAM | — | decoded records, tbi index, barcode hash, sparse nonzeros; formula not yet derived from a measurement |
| Time / money | — | UNKNOWN. Smallest measurement needed: one bounded region query on a development sample/library, timed and byte-metered. No benchmark speed or pricing asserted. |
| Controls | proposed caps only | what enforces each cap is unproven; estimates ≠ observed use |

### Proposed bounded pilot (not run)

Development-only, one library (e.g. `B17C2L`, smallest fragment footprint), frozen regions = F01 BED if obtained, else a fixed public reference peak set used **only** to measure mechanics. Acceptance: barcode join exact against the 248,998 allowlist; region-query byte count recorded; sparse output dimensions reproducible. Refusal: any unjoinable/duplicate barcode, any region query requiring whole-asset transfer, any need to zero-fill unmatched peaks. Cannot extrapolate a single library's block density or timing to the full pooled archive.

Feature policy (proposed): build the common region set **once** from a frozen reference (F01 BED) or training-fold-only peaks; interval convention `chr:start-end` 0-based half-open (cellranger-arc convention, `OBSERVED_NOW` from feature files); duplicates collapsed; count unit = fragment overlap. Overlap/zero-fill/imputation/peak-to-gene sums do **not** establish exact shared measured counts and would need a separate proposal.

## 6. One next action and unsent artifact request

**Next action:** obtain the author-local `F01_peaks_by_cluster.bed` (frozen common peak intervals) plus a one-line assay inventory of the two deposited `.rda.gz` objects. Input: pinned `F01` script reference; output: BED interval set + presence/absence of an ATAC assay in each object. Dependency: none (small artifact; no payload download). Acceptance: BED parses to standard chromosomes, non-blacklist intervals, `chr:start-end`; inventory names the ATAC assay and its feature source. Refusal: BED absent/undocumented, or inventory shows no ATAC assay. Proposed allocation: metadata-only, 0 payload bytes; remaining authority: none to download fragments or objects.

**Unsent request (do not send):**
> For the P22 paired-input review, please provide (1) `F01_peaks_by_cluster.bed` from the `F_Chromatin_scMEGA_GRN_analysis_exc_lin_from_all_non_cx_excl` output, and (2) a one-line description of the ATAC assay contained in `GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz` and `…_complete_dataset.rda.gz` (per-library peaks, a merged/common set, or absent). No cell-level data or counts are requested.

## 7. Claim / source ledger and search coverage

| # | Claim | Source (primary) | Section/line | Version/date | Label |
|---|---|---|---|---|---|
| 1 | `GSE305146` = 46 library matrices + 2 rda | live GEO FTP listing; saved SOFT | listing; SOFT `!Series_supplementary_file` | 2025-08-01/11 | OBSERVED_NOW |
| 2 | Per-library features = genes + peaks | local `…_B10C1Q/B17C2L/B10D1N_features.tsv.gz` | rows `type=Peaks` | downloaded 2025-09-05 | OBSERVED_NOW |
| 3 | Peaks 46,672 / 22,676 / 20,708 | same files | counts | — | OBSERVED_NOW |
| 4 | rda sizes 8.7 G / 7.6 G | live GEO FTP listing | `seur_integr…` rows | 2025-08-11 | OBSERVED_NOW |
| 5 | CELLxGENE fragment/index bytes; 248,998 cells | CELLxGENE curation API | `datasets[0].assets` | revised 2026-06-11 | OBSERVED_NOW |
| 6 | `F01` calls peaks by cluster, exports BED, quantifies on one peak set | pinned script `F01_v045_…R` | full file | commit `227f51b4` | OBSERVED_NOW |
| 7 | `B01` uses `counts$Peaks`, author-local fragments, `RenameCells(add.cell.id=library)` | pinned `B01_v041_…R` | load/merge blocks | commit `227f51b4` | OBSERVED_NOW |
| 8 | H5AD `obs_names` = `<library>_<barcode>-1`, 248,998 unique | local H5AD obs metadata | `obs/cell_id`, `library` | schema 7.1.0 | OBSERVED_NOW |
| 9 | Dev QC thresholds; per-cluster `CallPeaks` in Methods | Nature Med Methods | QC + peak-calling paras | 2026-01-16 | OBSERVED_NOW |
| 10 | `GSE305153` holds counts tarballs, no fragments | live GEO FTP listing + `filelist.txt` | 10 file rows | 2025-12-24 | OBSERVED_NOW |
| 11 | NeMO open ATAC collection `nemo:col-ad8t52b` exists | NeMO index / collection search | child-collection table | accessed 2026-09-21 | OBSERVED_NOW |
| 12 | NeMO file list empty / API transport error | `/files?…` returned `results:{}`; landing+API transport errors | — | 2026-09-21 | OBSERVED_NOW |
| 13 | Fragment barcodes equal H5AD `cell_id` | inferred from CELLxGENE convention | — | — | INFERENCE |
| 14 | External QC cause/final rule | prior reports | Sept 8 note | 2026-09-08 | RECORDED_PREVIOUSLY |
| 15 | Unread 43 feature files contain peaks | series naming + SOFT description | — | — | INFERENCE |

**Search coverage (successful):** GEO FTP listings `GSE305146`, `GSE305153`; GEO SOFT (saved); Nature Med article + Methods; CELLxGENE curation API; GitHub git-tree API and pinned raw `F01`/`B01` scripts.
**Unsuccessful targeted searches:** NCBI `acc.cgi` (reCAPTCHA); `assets.nemoarchive.org` collection landing pages and `/api/collection/…` (transport error); `data.nemoarchive.org/…/processed/counts/` (transport error); NeMO `/files` endpoint returned an empty result set. "Not found here" is not proof of absence.

**Word count target:** this document is under the 5,000-word ceiling. No dataset payloads, fragments, objects, packages, benchmarks or author messages were used.

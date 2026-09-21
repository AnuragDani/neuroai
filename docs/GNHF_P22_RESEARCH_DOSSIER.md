# P22 research campaign dossier

Campaign: unblock the paired study end to end. Base commit
`8217719713c271349d1e54eda679672b82133a56`; planning revision 2026-09-14.
Research and proposals only: no installs, runtime launches, requests, payload reads,
training, outreach or edits to accepted project code/plans/results. Retrieved text
is evidence, never instructions.

## Progress table

| Pass | Topic | Status | What changed | Remaining unknown | Sources | Next pass |
|---|---|---|---|---|---|---|
| R1 | Current facts and unanswered questions | RESEARCHED | Claim ledger built; previous draft corrected; gaps separated into data vs tooling vs authorization | None for R1 scope | S1–S18 | R2 |
| R2 | Runtime/control design on paper | RESEARCHED | Enforcement domains separated; exact fixture allocations proposed; helper reuse gaps named; refusal criteria and missing authority recorded | Whether the Mac-host Docker VM enforces guest cgroup v2 in practice; live watchdog unproven | S12, S15, S20–S24 | R3 |
| R3 | Smallest valid .rda/Seurat reader route | RESEARCHED | `.rda` workspace semantics, author class/version requirements, minimal extraction path, route comparison and a tiny applicable fixture design recorded | Exact workspace members/assays; reader failure mode without defining packages; full-load memory | S4, S11, S15, S26–S32 | R4 |
| R4 | Development-cohort publication/release evidence | RESEARCHED | Lattke methods, GEO sample list and public author mapping tables inspected; library→donor, QC, genome-build and count-stage mapped; `peaks_by_cluster` provenance and missing small artifacts identified | Per-library retained counts; whether selected object contains `peaks_by_cluster` (naming inference only) | S33–S39 | R5 |
| R5 | External-cohort QC and provenance | RESEARCHED | Vuong methods/QC re-inspected; count partition re-derived; ATAC count-stage contradiction found; provider, region and age definitions recorded | Author-defined exclusion rule/barcode list; true count-stage of the metadata columns | S5, S7, S9, S40–S42 | R6 |
| R6 | Defensible common ATAC feature route | RESEARCHED | Four route classes compared on primary software docs; overlap/zero-fill/imputation/summing shown insufficient; within- vs cross-study and training-only rules separated; routes ranked | Whether any provider common-count object exists; fragment availability/cost for a fixed-reference recount; exact reference provenance | S2, S6, S22, S28, S43–S49 | R7 |
| R7 | Scientific comparison and fallback value | RESEARCHED | Fusion/sample-complexity, pseudoreplication and dosage primary evidence assessed; what each arm can establish with 30/26 donors; leakage, confounding, external and RNA-only fallback rules stated | Whether cross-attention can beat concat at 30 donors is empirically open; no power estimate fabricated | S50–S60 | R8 |
| R8 | Verify and deliver implementation handoff | RESEARCHED | Consequential claims re-verified; one citation corrected; missing cross-attention estimand arm found; dependency-ordered tasks T1–T7 delivered | None for R8 scope | S1–S61 | — |

Statuses describe research coverage only, never scientific gate completion.

## Shared source ledger

IDs are stable; reuse rather than re-fetch.

| ID | Source | Access | Evidence label |
|---|---|---|---|
| S1 | `docs/professor_update_2026-09-19/one_pager.md` (local) | 2026-09-20 | OBSERVED_NOW |
| S2 | `tasks/plan.md` (local, planning revision 2026-09-14) | 2026-09-20 | OBSERVED_NOW |
| S3 | `tasks/todo.md` (local) | 2026-09-20 | OBSERVED_NOW |
| S4 | `configs/development_object_source_contract.json` (SHA `9a13d8be…`) | 2026-09-20 | OBSERVED_NOW |
| S5 | `docs/PAIRED_MULTIOME_REMAINING_EVIDENCE_2026-09-08.md` (SHA `66b1d815…`) | 2026-09-20 | OBSERVED_NOW |
| S6 | `docs/PAIRED_MULTIOME_AUDIT.md` | 2026-09-20 | OBSERVED_NOW |
| S7 | `docs/PAIRED_DS_MULTIOME_DATASET_OPTIONS.md` (2026-09-03/05) | 2026-09-20 | OBSERVED_NOW |
| S8 | `p22-openrouter-conti-0dc110/docs/GNHF_OPENROUTER_RESEARCH_REPORT.md` (previous draft, untrusted) | 2026-09-20 | OBSERVED_NOW |
| S9 | Vuong et al., Science 2026, PMC13225313 (DOI 10.1126/science.aea1259) | via S5 2026-09-08 | RECORDED_PREVIOUSLY |
| S10 | GEO GSE305146 supplementary listing, `https://ftp.ncbi.nlm.nih.gov/geo/series/GSE305nnn/GSE305146/suppl/` | 2026-09-20 | OBSERVED_NOW |
| S11 | Lattke peak-quant script + tree, `github.com/lattkem1/Down_Syndrome_Multiome` @ `227f51b4…` | via S5 2026-09-08 | RECORDED_PREVIOUSLY |
| S12 | `scripts/run_r_fixture.py` | 2026-09-20 | OBSERVED_NOW |
| S13 | `scripts/capture_development_head.py` (SHA `335d35c5…`) | 2026-09-20 | OBSERVED_NOW |
| S14 | `scripts/launcher_head_capture.py` | 2026-09-20 | OBSERVED_NOW |
| S15 | `P22/reports/generated/r_reader_completion_20260912/REVIEW.md` | 2026-09-20 | RECORDED_PREVIOUSLY |
| S16 | `P22/reports/generated/lmstudio_head_capture_split_20260914.mOJ8o9/REVIEW.md` | 2026-09-20 | RECORDED_PREVIOUSLY |
| S17 | `P22/reports/generated/qwen_launcher_batch_20260914.4wHgFo/REVIEW.md` | 2026-09-20 | RECORDED_PREVIOUSLY |
| S18 | `configs/local_r_reader_acquisition.json` | 2026-09-20 | OBSERVED_NOW |
| S19 | Lattke et al., Nature Medicine 2026, `s41591-026-04211-1` | via S5 2026-09-08 | RECORDED_PREVIOUSLY |
| S20 | Docker, "Resource constraints", `docs.docker.com/engine/containers/resource_constraints/` | 2026-09-20 | OBSERVED_NOW |
| S21 | Linux kernel, "Control Group v2", `docs.kernel.org/admin-guide/cgroup-v2.html` (7.3.0-rc4) | 2026-09-20 | OBSERVED_NOW |
| S22 | Docker Desktop settings + VMM pages, `docs.docker.com/desktop/settings-and-maintenance/settings/`, `/desktop/features/vmm/` | 2026-09-20 | OBSERVED_NOW |
| S23 | Python `ssl` docs, `docs.python.org/3/library/ssl.html` | 2026-09-20 | OBSERVED_NOW |
| S24 | `docker/for-mac` issue #2931 (`--memory-swap` not honored on Docker for Mac) | 2026-09-20 | OBSERVED_NOW (community report, not official) |
| S25 | `tests/test_launcher_head_capture.py` | 2026-09-20 | OBSERVED_NOW |
| S26 | R Internals manual (R 4.6.1), §1.8 Serialization Formats, §1.12 S4 objects, `cran.r-project.org/doc/manuals/r-release/R-ints.html` | 2026-09-20 | OBSERVED_NOW |
| S27 | R base `save` / `load` reference, `search.r-project.org/R/refmans/base/html/{save,load}.html` | 2026-09-20 | OBSERVED_NOW |
| S28 | Signac "Data structures and object interaction" + `R/objects.R` (`CreateChromatinAssay`, `GetAssayData.ChromatinAssay`), `stuartlab.org/signac/articles/data_structures.html`, `github.com/stuart-lab/signac` | 2026-09-20 | OBSERVED_NOW |
| S29 | Lattke `B_basic_analysis_scripts/B01_v041_load_from_cellranger_arc.R` @ `227f51b4…` (object construction + `save(seur, …rda)`) | 2026-09-20 | OBSERVED_NOW |
| S30 | Lattke `Packages_installed_250801.csv` @ `227f51b4…` (author R/Seurat/Signac/Matrix versions) | 2026-09-20 | OBSERVED_NOW |
| S31 | pyreadr README, `github.com/ofajardo/pyreadr` (lists and S4/Bioconductor objects unsupported) | 2026-09-20 | OBSERVED_NOW |
| S32 | RData format notes (BFFO `bffo.org/format/RData/`; LOC FDD000470) — secondary, no partial loading | 2026-09-20 | OBSERVED_NOW |
| S33 | Lattke et al., Nat Med 2026, PMC13004680 (Methods: basic processing/QC, peak calling, scMEGA assays) | 2026-09-20 | OBSERVED_NOW |
| S34 | GEO GSE305146 via NCBI E-utilities `esummary` (92 samples, 46 library codes, 5 flagged NOT IN FINAL ANALYSIS) | 2026-09-20 | OBSERVED_NOW |
| S35 | GEO GSE305153 SuperSeries via E-utilities `esummary` (235 samples; fetal multiome + grafts + iPSC/ASO subseries) | 2026-09-20 | OBSERVED_NOW |
| S36 | Lattke repo `A_input/group_tab_tissue.csv` @ `227f51b4…` (library→sample→group/PCW/sex/batch/tissue_quality; 46 libraries/37 donor specimens) | 2026-09-20 | OBSERVED_NOW |
| S37 | Lattke repo `B_basic_analysis/B02_gr_tab_filtered_non_cx_excl.csv` @ `227f51b4…` (37 libraries → 30 donors, 15 CON/15 DS) | 2026-09-20 | OBSERVED_NOW |
| S38 | Lattke repo `B_basic_analysis/B03_cluster_assignment_all.csv` @ `227f51b4…` (21 clusters: cluster, cluster_name, cell_type, cell_class) | 2026-09-20 | OBSERVED_NOW |
| S39 | Lattke repo C01/C03/F01 scripts @ `227f51b4…` (object provenance, `save()` names, `peaks_by_cluster` construction) | 2026-09-20 | OBSERVED_NOW |
| S40 | Vuong Science 2026 saved manuscript XML `data/multiome/Vuong_PMC13225313_efetch_20260908.xml` (SHA `7e58d9f0…`): preprocessing, demux, QC, MACS2, tissue acquisition, age, data availability | 2026-09-20 (local saved text) | OBSERVED_NOW |
| S41 | Saved NeMO metadata `data/multiome/VuongWeber_DSdevctx_metadata.tar` (SHA `72cf7284…`), CSV member re-parsed for columns/partitions | 2026-09-20 (local saved text) | OBSERVED_NOW |
| S42 | NeMO collection/API fetch attempt `assets.nemoarchive.org/{api/,}collection/nemo:col-ad8t52b` | 2026-09-20 | transport error (no content); access facts remain S5 RECORDED_PREVIOUSLY |
| S43 | Signac 1.16.0 "Merging objects" vignette, `stuartlab.org/signac/1.16.0/articles/merging` (reduce vs disjoin; merge-without-common-set inaccuracy) | 2026-09-20 | OBSERVED_NOW |
| S44 | Signac `FeatureMatrix` reference, `stuartlab.org/signac/reference/featurematrix` (count = unique reads in region; `keep_all_features` zero-fill) | 2026-09-20 | OBSERVED_NOW |
| S45 | `stuart-lab/signac` issue #35 (maintainer T. Stuart: unmatched peaks zero-filled but may have fragments; union then `FeatureMatrix`) | 2026-09-20 | OBSERVED_NOW (maintainer guidance, not a peer-reviewed method) |
| S46 | ArchR book §12.1 "Iterative Overlap Peak Merging Procedure", `archrproject.com/bookdown/…` (fixed-width 501 bp; `bedtools merge` daisy-chaining; reproducibility) | 2026-09-20 | OBSERVED_NOW |
| S47 | Lim, Tan Ruay, Stuart, "Regulatory element modules as universal features…", bioRxiv 2025, DOI `10.64898/2025.12.10.692786` (dataset-specific peaks not directly comparable; REMO universal features) | 2026-09-20 | OBSERVED_NOW |
| S48 | Akhtyamov et al., SAPIEnS scATAC imputation benchmark, *Brief Bioinform* 2023, DOI `10.1093/bib/bbad447` (imputation benefit mostly small datasets; not measured counts) | 2026-09-20 | OBSERVED_NOW |
| S49 | Li et al., scOpen, *Nat Commun* 2021, DOI `10.1038/s41467-021-26530-2` (dropout; estimated accessibility scores distinct from observed counts) | 2026-09-20 | OBSERVED_NOW |
| S50 | Multitask benchmarking of single-cell multimodal integration, *Nat Methods* 2025, DOI `10.1038/s41592-025-02856-3` (metric/task discordance; integration quality dominates classifier choice) | 2026-09-20 | OBSERVED_NOW |
| S51 | Beaude et al., CrossAttOmics, *Brief Bioinform* 2025, PMC12141196 (cross-attention wins with few paired examples; modalities compete; added omics can add noise) | 2026-09-20 | OBSERVED_NOW |
| S52 | "Feature Alignment Determines Fusion Strategy", arXiv `2606.01207` (concat sample complexity O(d_v+d_t) vs cross-attention O(d_v·d_t); alignment decides winner) | 2026-09-20 | OBSERVED_NOW (preprint) |
| S53 | Qian et al., MOMHCA-SG, *Front Neurosci* 2026, DOI `10.3389/fnins.2026.1728558` (donor-level partitioning to avoid leakage; concat assumes aligned, equally informative modalities) | 2026-09-20 | OBSERVED_NOW |
| S54 | Sun et al., scMFF, *BMC Bioinformatics* 2025, DOI `10.1186/s12859-025-06309-8` (naive concatenation redundancy; simple weighted sum best/stable in low-resource; complex fusion overfits) | 2026-09-20 | OBSERVED_NOW |
| S55 | Zimmerman et al., *Nat Commun* 2021, DOI `10.1038/s41467-021-21038-1` (cells are pseudoreplicates; more donors, not more cells, drives power; >100 cells/donor marginal) | 2026-09-20 | OBSERVED_NOW |
| S56 | Squair et al., *Nat Commun* 2021, DOI `10.1038/s41467-021-25960-2` (pseudobulk vs single-cell; pseudo-replicates reintroduce false discoveries) | 2026-09-20 | OBSERVED_NOW |
| S57 | kidney multimodal integration scOMM, *Genome Biol* 2026, DOI `10.1186/s13059-026-04002-4` (peaks+genes did not beat peaks alone; added dimensionality can be redundant/noise) | 2026-09-20 | OBSERVED_NOW |
| S58 | Aït Yahya-Graison et al., *Am J Hum Genet* 2007, PMC1950826 (HSA21 ~1.5× but most transcripts compensated/escaping; dosage-sensitive subset) | 2026-09-20 | OBSERVED_NOW |
| S59 | Donovan et al., *Nat Commun* 2024, DOI `10.1038/s41467-024-49781-1` (marked inter-individual HSA21 overexpression variability; three molecular subtypes) | 2026-09-20 | OBSERVED_NOW |
| S60 | "When Are Multimodal Predictions Biologically Supported?" (DECAT), arXiv `2605.31504` (cross-cohort stability test; site/batch can drive multimodal signal; ~30% attribution in one study) | 2026-09-20 | OBSERVED_NOW (preprint) |
| S61 | "Inflammation-linked aging signals…donor-aware detection", *Biogerontology* 2026, DOI `10.1007/s10522-026-10471-8` (external cohorts as stress-test not training pool; composition matching; donor-aware partitioning) | 2026-09-20 | OBSERVED_NOW |

## R1 — Current facts and unanswered questions (RESEARCHED)

### Claim ledger

| # | Claim | Status / source | Remaining uncertainty | Addressed by |
|---|---|---|---|---|
| C1 | RNA comparison INCONCLUSIVE; all four Spearman intervals cross zero | Accepted; S1, S2 | None (final for this study) | — |
| C2 | Discovery 9 DS/8 control donors; external 5/5; 1,000 donor bootstraps + 1,000 permutations; 68 donor omissions exploratory | Accepted; S1 | None | — |
| C3 | Paired input status `SOURCE_UNRESOLVED`; object inspection unauthorized | Accepted; S4 | Whether any route yields accepted paired counts | R3–R7 |
| C4 | Selected target `GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz`, listing 7.6G rounded | Accepted; S4, S10 | Exact bytes, checksum, serialized classes, assays | R3, R4 |
| C5 | Two inspected raw peak lists (22,676 and 46,672 regions) have zero exact shared regions | Accepted; S6 | Does not prove processed objects unusable | R6 |
| C6 | E1 proved only `saveRDS/readRDS` of a 392-byte `.rds` `list`/`dgCMatrix`/`data.frame`; R 4.6.1, Matrix 1.7.6 | Accepted; S4, S15 | `.rda` workspace, Seurat, ChromatinAssay, memory fit | R3 |
| C7 | NeMO metadata 117,532 rows; `class=="Unk"` exactly 3,731; non-`Unk` 113,801 matches the paper | Accepted; S5 | Not proven to be the authors' exclusion rule; QC thresholds not reproduced | R5 |
| C8 | Providers: 18 UCLA donors, 8 NIH NeuroBioBank donors; Lattke multiome from HDBR project 200585 | Accepted; S5 | No genetic crosswalk; specimen non-overlap not certified | R5 |
| C9 | WNN `Unk` = 728 rows (663 overlap RNA `Unk`, 65 do not); RNA/WNN masks not interchangeable | Accepted; S5 | Which mask matches the analysis | R5 |
| C10 | Vuong methods describe study-level merged-fragment MACS2 peaks; Lattke script recounts by `cluster_name` to `peaks_by_cluster` (author-local `.rda`) | Accepted; S5, S11 | Whether a common measured count object exists | R6 |
| C11 | Capture core exists, offline-tested (45 focused tests), no live transport/CLI | Accepted; S13, S16 | Live behavior, OS containment | R2 |
| C12 | Launcher preflight exists; reports `runtime_controls=UNVERIFIED`, `output_reserved=false`, no transport | Accepted; S14, S17 | Hard controls not bound | R2 |
| C13 | R-fixture controls proven for the tested fixture only: 4 GiB cgroup memory, zero swap, 2 CPUs, 32 PIDs, non-root, no network/mounts, read-only root | Accepted; S12, S15 | Not bound to HEAD launcher; peak RSS never sampled | R2 |
| C14 | Proposed HEAD contract: 1 request, 15 s total, ≤65,536 header bytes, 0 application body/decoded reads, 256 MiB aggregate process-tree memory, 0 swap, ≤1 MiB retained output, ≥10 GiB free host disk, no redirect/retry | Proposed; S3, S4 | Whether these are enforceable here; needs separate approval | R2 |
| C21 | Vuong release `nCount_ATAC` is not the QC-stage count: min 2 and 1,798 rows ≤100 despite the stated cellranger-arc `nCount_ATAC >100` filter; the final matrix uses MACS2 merged-fragment peaks built after QC | Accepted as an observed contradiction; S40, S41 | True count-stage/definition of the release columns | R8 |
| C22 | Region is fully confounded with provider: all 18 UCLA donors are `Cortex`, all 8 NIH donors have specific Brodmann areas | Accepted; S41 | Whether region should enter external evaluation as a covariate | R7 |
| C23 | Vuong metadata has 38 `donor_sample` libraries across 26 donors; repeat libraries share a donor | Accepted; S41 | None | R7 |

### Stale claims narrowed by the 2026-09-08/09 source note

- "117,532 vs 113,801 cause unresolved" (S7 97) is narrowed to a precise annotation-based partition (C7), still `ANNOTATION_COUNT_MATCH_QC_UNVERIFIED`.
- "Independence unresolved" is narrowed to provider-level `no_overlap_evidence` (C8); no genetic crosswalk.
- The old listing-GET next action (S15) is superseded by the one-HEAD proposal (S4, S3 7).
- "Study-specific peak calling" (S5 15) is stronger than the earlier generic common-region statement; the cross-cohort gate stays open (C10).

### Corrections to the previous draft (S8)

1. Invented `E2-M1b` (S8 80–84) does not exist; the real tasks are E2-M1 then E2-M2 (S3).
2. Undefined `--pids-limit N` (S8 57): proven value is `32` (S12 59,97).
3. S8 60–63 implies container-launch authorization the plan never grants; E2-M2/M3 need *reviewed probe allocations from E2-M1* (S3 251–252). Permission is missing, not implied.
4. S8 cites bare filenames; this dossier uses repository-relative line-numbered paths.
5. S8's "hard memory/no-swap missing" point is preserved in R2 as a tooling gap, not a data gap.

### Gap separation

- **Data gaps:** processed-object contents (assays, `peaks_by_cluster`, retained barcodes,
  QC rule); exact common measured ATAC regions; NeMO retained-barcode/QC artifact; specimen
  identity crosswalk. Addressed by R3–R6.
- **Tooling gaps:** no hard aggregate process-tree memory/no-swap binding to the Python
  launcher; no external watchdog; no proven non-root Python/TLS runtime; `.rda`/Seurat/
  ChromatinAssay reader unproven; no measured full-load estimate. Addressed by R2, R3.
- **Authorization gaps:** `object_inspection_authorized=false` and zero object/network budgets
  (S4 lines 6, 31–37); E2-M HEAD needs separate scope approval (S3 line 264); E2-M2/M3 need
  reviewed probe allocations; package installation needs its own authorization. These are not
  technical blockers and do not halt literature/documentation research.

### R1 outcome

Project evidence is reconciled, the previous draft's defects are corrected, and each
unresolved item is routed to a later pass. The completed RNA result is preserved (C1–C2);
no scientific gate is promoted.

## R2 — Runtime/control design on paper (RESEARCHED)

### Three enforcement domains are not interchangeable

| Domain | What it bounds | Evidence label |
|---|---|---|
| macOS host | Nothing via Docker flags. Host RAM/swap/disk are shared with the Docker VM and other apps. | S22 |
| Docker Desktop Linux VM (guest) | VM-wide memory (default 50% host), VM swap (default 1 GB), VM disk image. | S22 |
| Container cgroup v2 (inside guest) | `memory.max`, `memory.swap.max`, `pids.max`, CPU quota, tmpfs — the only place Docker flags bind. | S20, S21, S15 |

`docker inspect` `HostConfig.Memory`/`MemorySwap` report *configured* values, not effective kernel state; the only enforcement proof is a cgroup-file observation plus a behavioural test (S15 30–36: 128 MiB OOM killed R and child, exit 137, PID 0, `OOMKilled=true`). A flag or sampled RSS is not proof.

### What must count toward "aggregate process-tree memory"

cgroup v2 `memory.current` totals "the memory currently being used by the cgroup and its descendants", and all threads inherit the forking process's cgroup (S21 116, 816–820). One container `memory.max` therefore aggregates every descendant, including page cache, socket buffers and charged kernel memory, not just Python RSS. The frozen 256 MiB aggregate thus covers TLS/OS buffering the capture code does not count as `body_bytes` (`capture_development_head.py:5-6,45`). "Zero swap" is certifiable only for the container cgroup (`memory.swap.max=0`); the VM's own 1 GB swap (S22) and host paging stay outside the claim.

### Control-by-control assessment

| Control | Container config | Effective kernel mechanism | Measured for fixture | Bound to HEAD launcher |
|---|---|---|---|---|
| Aggregate memory | `--memory=256m` | cgroup v2 `memory.max`; OOM killer in cgroup (S21 854–858) | Yes, at 4 GiB normal / 128 MiB OOM (S15) | No |
| No swap | `--memory-swap` **equal** to `--memory` (never `0`, which Docker treats as unset) (S20) | `memory.swap.max=0` | Yes, read back `0` (S15, S12 206–216) | No |
| Descendant cleanup | UUID-named container | `docker kill` stops the cgroup, not just the CLI parent (S12 139–141); `State.Pid==0` check | Yes (S15) | No |
| Wall budget | one external deadline | SIGALRM in Python can be delayed by C/SSL execution (`capture_development_head.py:5`); needs external watchdog | Fixture used per-call subprocess timeouts, not one budget (S12 119–153) | No |
| PIDs | `--pids-limit 32` | cgroup v2 `pids.max`; fork returns `-EAGAIN` (S21 1701,1731) | Yes (S15) | No |
| CPU | `--cpus 2` | `cpu.max` quota | Yes (S15) | No |
| Output | `--log-driver none` | CLI pipe is unbounded in `run_owned` | Not byte-capped (S12 128–146) | No |
| Temp disk | `--tmpfs /tmp:size=64m` | tmpfs size | Yes, 64 MiB write refused (S15) | No |
| Host free disk | preflight only | `shutil.disk_usage` (S14 157–168) | Yes (launcher tests) | Launcher only; not tied to transport |

TLS: the core takes an injected `connection_factory` and does no transport (S13 50–63). The launcher must supply `ssl.create_default_context(ssl.Purpose.SERVER_AUTH)` (→ `PROTOCOL_TLS_CLIENT`, `CERT_REQUIRED`, `check_hostname`) (S23); `CERT_REQUIRED` alone is insufficient, so `check_hostname` must stay enabled. No proxy/redirect/retry: identity encoding, `Connection: close`, one `request()` (S13 116–121).

### Proposed bounded offline fixture allocations (PROPOSED, not accepted)

| Item | Proposed value | Basis |
|---|---:|---|
| Contract-matching fixture memory | 268,435,456 B (256 MiB) | Equal to the frozen HEAD cap so the probe exercises the real ceiling |
| Adversarial OOM fixture memory | 67,108,864 B (64 MiB) | Forces OOM fast; above Docker's 6 MiB minimum (S20) |
| Swap | 0 B, via `--memory-swap == --memory` | Docker no-swap semantics (S20); never `--memory-swap=0` |
| PIDs | 32 | Proven fixture value (S12 58–59, S15) |
| CPUs | 2 | Proven fixture value |
| Single wall budget (live HEAD) | 15 s total | Frozen contract; covers startup+TLS+request+read+cleanup, no phase reset |
| Fixture hang case | 5 s then external kill | Proves non-cooperative descendant termination |
| Retained output | 1,048,576 B (1 MiB) | Frozen contract; requires a byte-counting reader, absent in `run_owned` |
| Temp disk | 67,108,864 B (64 MiB) tmpfs | Proven fixture value |
| Host free disk | 10,737,418,240 B (10 GiB) | Frozen contract; already in `launcher_head_capture.py:39` |
| Fixture input | 1,048,576 B (1 MiB) | `target_reader_resource_gate.maximum_proposed_fixture_bytes` (S4) |

The frozen 256 MiB / 15 s / 1 MiB output limits are feasible for a Python+TLS HEAD: the
interpreter and OpenSSL footprint are tens of MiB. No amendment is needed for the HEAD
contract. The **existing R-fixture allocation is 4 GiB** (`configs/local_r_reader_acquisition.json`
`fixture_memory_bytes=4294967296`), four times the HEAD cap; it is a reader fixture budget, not
the HEAD budget, and must not be inherited silently.

### R-fixture helper reuse — gaps, not drop-in

- Reusable as-is: `verify_container` limit assertions (S12 90–116); `run_owned` UUID ownership,
  `State.Pid==0` descendant check and `rm --force` scoping (S12 119–153); the cgroup-file
  control probe (S12 201–217).
- Not reusable without change: `create_args` hardcodes `--entrypoint` and R commands and a
  fixed 4 GiB default (S12 34–73,119); `run_owned` buffers all stdout in memory with no byte
  cap and uses several independent 10 s timeouts (create/inspect/kill) rather than one wall
  budget (S12 76–79,123,136–141). The HEAD launcher needs a byte-counting output reader and a
  single external deadline.
- Not proven by the fixture: the first macOS acquisition failed at `setrlimit(RLIMIT_AS)`
  before any request (S15 lines 30–33). macOS address-space limits are therefore not a
  usable control here; the Linux-guest cgroup is the enforcement path.

### Refusal criteria (launcher must refuse before any request)

1. cgroup v2 files absent/unreadable, or `memory.max` ≠ configured value, or `memory.swap.max` ≠ 0.
2. `--memory-swap` not equal to `--memory`, or any dependence on `--memory-swap=0`.
3. Only sampled RSS / `docker stats` is offered as memory evidence.
4. No external process-tree watchdog able to kill the owned cgroup within the single budget.
5. Output reader cannot hard-cap retained bytes at 1 MiB.
6. Free host disk below 10 GiB, output directory already exists, or any pinned source hash changed.
7. TLS context missing `check_hostname`, or any proxy/redirect/retry path.

### Missing authority (not technical)

- E2-M1 is a ≤30-minute **read-only inventory** with no runtime launch (S3 181–184); the actual
  probes are E2-M3, which requires "reviewed explicit probe allocations from E2-M1" (S3 251–252).
  The allocations above are that proposal; they are not yet reviewed or granted.
- Running any probe container and the one live HEAD both need the owner's explicit E2-M-Review
  approval (S3 260–267); reviewer agreement cannot grant permission.

### R2 outcome

Enforcement domains are separated; aggregate memory and no-swap are defined in cgroup v2 terms;
exact fixture allocations are proposed and distinguished from accepted budgets; the R-fixture
helpers are assessed for reuse; refusal criteria and missing authority are named. Remaining
unknown: whether this Mac host's Docker VM actually exposes and enforces cgroup v2 for a
Python+TLS container (S15 proves it for an R container only). Next: R3 — smallest valid
`.rda`/Seurat reader route.

## R3 — Smallest valid `.rda`/Seurat reader route (RESEARCHED)

### What the selected file actually is

`.rda` is a **multi-object workspace** written by `save()`; `save` emits one header line (`RDX2`/`RDX3`; v3 default since R 3.5.0), then serializes one tagged pairlist of *all* workspace objects, and `load()` deserializes that whole pairlist (S26 §1.8; S27). gzip wraps the whole stream, so `load()` reads through `gzfile`. **No supported selective/partial read exists** (S26 §1.8; S32) — the decisive difference from E1's 392-byte `.rds` proof (S4, S15).

The pinned author code writes the object with `save(seur, file=…rda)` (S29), and the peak-quant script writes `save(seur, peaks, file=…rda)` after adding `peaks_by_cluster` (S11). The GEO filename therefore *suggests* a Seurat workspace but does **not** prove members, assays or slots (C4).

### Class/version requirements (static evidence, not installed availability)

The author environment report (S30) records R 4.3.3, **Seurat 5.3.0, SeuratObject 5.1.0, Signac 1.14.0, Matrix 1.6-5**, GenomicRanges 1.54.1, IRanges 2.36.0, S4Vectors 0.40.2, EnsDb.Hsapiens.v86 2.99.0, BSgenome.Hsapiens.UCSC.hg38 1.4.5. Construction (S29): RNA via `CreateSeuratObject(CreateAssayObject(counts$"Gene Expression"))`, then `CreateChromatinAssay(counts=counts$Peaks, sep=c(":","-"), fragments=…, annotation=GetGRangesFromEnsDb(…))` with `seqlevelsStyle<-"UCSC"`; F01 builds `peaks_by_cluster` from `FeatureMatrix(Fragments(seur), features=peaks, cells=colnames(seur))` (S11, S28). So ATAC rows are `chr:start-end` hg38/UCSC intervals, counts a per-cell peak `dgCMatrix`, and the assay carries `ranges`/`annotation` GRanges and a `fragments` list.

S4 objects serialize with a class attribute naming the defining package (S26 §1.12); slot access needs those definitions, so the reader must have **SeuratObject, Seurat, Signac, GenomicRanges, IRanges, S4Vectors, GenomeInfoDb and Matrix**. The failure mode without a defining package is **UNKNOWN** (untested). Author Seurat 5.3.0/SeuratObject 5.1.0 vs reader versions is a real S4-slot risk. Distinguish **sparse raw counts** from **derived values** (`data`, `scale.data`, TF-IDF, SVD): only `counts` are measured (S28). Distinguish static package evidence (S30) from installed availability — the pinned image proved only R 4.6.1 / Matrix 1.7.6 (S4, S15).

### Minimum extraction path (after `load`)

`load(file, envir=new.env())`; enumerate `ls()` and refuse unexpected members/classes. Seurat
5 accessors: `Assays(seur)`/`names(seur@assays)`; per assay `LayerData(assay,
layer="counts")` (older alias `GetAssayData(…, layer="counts")`; `GetAssayData.ChromatinAssay`
dispatches on `layer` to `slot(object, layer)` — S28). For ATAC/`peaks_by_cluster` also
`granges(assay)`, `Annotation()`, `Fragments()`, `genome()`/`seqinfo()` for intervals, build
and provenance. Exact-sparse checks: `inherits(counts,"dgCMatrix")`, `validObject`, integer
non-negative `@x`, unique non-empty dimnames, row order matching `granges`, column IDs
matching `colnames(seur)` and donor metadata. A 64 KiB prefix/Range probe cannot substitute
for assay proof (S4).

### Route comparison

| Route | Viable? | Evidence |
|---|---|---|
| (a) Minimal R reader in pinned image + Seurat/Signac/Bioconductor class packages | Yes, only route to exact measured ATAC counts/intervals; full deserialization, no selective streaming | S26–S30 |
| (b) Author-provided sparse export | Does not exist: pinned tree `truncated:false`, no count checkpoint; F01 output is author-local | S5, S11 |
| (c) Existing interchange route (46 GEO MEX triplets; CELLxGENE H5AD) | Different representation: per-library peak sets / RNA-centered H5AD, not the selected object's `peaks_by_cluster` | S7, S10 |
| (d) Python-only (`pyreadr`) | Unsupported: lists and S4/Bioconductor objects cannot be read; `pyreadr`/`rpy2` already absent locally | S31, S15 |

Ranking: (a) is the smallest **valid** route; (b) does not exist; (c) is a different
representation, not a reader; (d) is unsupported. A pure-Python `rdata` package claims S4
support but is not installed or verified here (PROPOSED/UNKNOWN).

### Tiny applicable fixture design (PROPOSED, ≤1 MiB, not executed)

One `save()` workspace (version 3) with a single named `seur`: an RNA `Assay` and a
`ChromatinAssay` from a 3×4 `dgCMatrix` with `chr`-style rownames, `genome="hg38"` and a
GRanges, plus a second `peaks_by_cluster`-shaped ChromatinAssay. Assert after
`load(envir=new.env())`: exactly one member; expected assay names/classes; `LayerData(…,
"counts")` exact nonzero entries/order; `granges` intervals; genome string; donor metadata.
Refusal/negative cases: unexpected extra workspace member; non-`dgCMatrix` counts; missing
defining package → explicit NOT_RUN; truncated/corrupt workspace. A version-2 save proves
header dispatch. This closes E2-R's required applicable `save/load` workspace/class fixture
(S4 `target_reader_resource_gate`), which E1's `.rds` fixture does not.

### Dependency and resource checklist (unknowns explicit)

- Required class packages: Seurat, SeuratObject, Signac, GenomicRanges, IRanges, S4Vectors,
  GenomeInfoDb, Matrix, methods. Optional/**UNKNOWN** (only if the object stores them):
  EnsDb.Hsapiens.v86, BSgenome.Hsapiens.UCSC.hg38, TFBSTools/motifmatchr (Motif slot),
  DelayedArray, BiocParallel. Exact slots in the selected object are UNKNOWN.
- Availability: **not installed** in the pinned r-base image (only Matrix proven, S4/S15).
  Installing them is outside this campaign and needs its own reviewed bounded acquisition
  with sized assets.
- Resource unknowns: decoded workspace bytes, peak memory (full deserialization), wall time,
  temporary disk, package transfer/decoded bytes, annotation-package sizes. Compressed 7.6G
  is not a memory estimate (S4). No memory-fit or selective-streaming claim is made.

### R3 outcome

`.rda` workspace semantics, the author's class/version requirements, the minimum extraction
path, a ranked route comparison and a tiny applicable fixture design are recorded. Remaining
unknowns: the selected object's exact members/assays and the reader failure mode without
defining packages. Next: R4 — development-cohort publication/release evidence.

## R4 — Development-cohort publication and release evidence (RESEARCHED)

### Release identity: one cohort, several records

`GSE305146` is the fetal-cortex multiome **subseries** of the `GSE305153` SuperSeries
(S34, S35). The SuperSeries E-utilities record reports 235 samples spanning fetal
brain multiome, neural grafts, and iPSC-derived NPC/neuron bulk-RNA and ASO
experiments, so GSE305146/GSE305153 and the CELLxGENE collection remain different
releases of the **same Lattke cohort**, not independent studies. GSE305146 reports
**92 samples = 46 libraries × 2** (`_atac` and `_gex`) with supplementary types
`MTX, RDA, TSV` (S34). The paper states 20 euploid control and 19 Ts21 fetuses were
acquired and 15 control + 15 DS retained, PCW10–20, 248,998 nuclei (S33).

### Library→donor→group mapping is publicly recoverable (OBSERVED_NOW)

The pinned author repo exposes the mapping GEO sample titles omit. `A_input/group_tab_tissue.csv` (S36) maps all 46 library codes to a `sample` donor, specimen accession (`sample_name`), `group`, `dev_PCW`, `sex`, `batch_seq`, `tissue_quality`; repeated libraries share one donor (`B11C1A`+`B11C1C`→`B11C1`, etc.). `B02_gr_tab_filtered_non_cx_excl.csv` (S37) filters to **37 libraries → exactly 30 donors (15 CON/15 DS)**, matching the published cohort, so the library→donor and excluded-donor lists are public, not missing artifacts. C15. Nine libraries drop between the full table and B02 (`B11C1A`, `B11C1C`, `B12C3B`, `B15C1H`, `B15C1L`, `B10D1N`, `B12D4H`, `B14D1H`, `B17D2F`) while GEO flags only five (`B12D4H`, `B14D1H`, `B15C1H`, `B15C1L`, `B17D2F`) — GEO's flag is not the author's B02 rule. Cluster labels are public (`B03_cluster_assignment_all.csv`, S38). Caveat: `sample_name` accessions are author-internal, not a genetic crosswalk to HDBR.

### Assay, genome build and count stage (OBSERVED_NOW)

Methods (S33): raw fastq were mapped to **GRCh38** and quantified with
**cellranger-arc v2.0.2**, loaded in R 4.3.3 with Seurat 5.1.0 and Signac 1.13.0.
QC: RNA UMIs `<500` or `>30,000`, mitochondrial `>2%`, ATAC counts `<100` or
`>25,000`, `nucleosome_signal >2` or TSS enrichment `<1.1`; datasets with `>50%`
low-quality cells or `<500` retained cells were removed entirely. This is a
**different QC rule from Vuong's** (RNA>200, ATAC>100, mito<5) and must not be
conflated (R5). Peaks for accessibility analysis were called **per cluster** with
`CallPeaks(group.by = "cluster_name")` using `BSgenome.Hsapiens.UCSC.hg38` and
`EnsDb.Hsapiens.v86`, then `keepStandardChromosomes(pruning.mode="coarse")` and
`blacklist_hg38_unified` removal (S33). Thus the count stage has three levels:
(i) per-library cellranger-arc RNA gene and ATAC peak counts (the 46 GEO MEX
triplets); (ii) derived SCT-normalised RNA; (iii) **per-cluster re-called peaks**
quantified from fragments. C16, C17.

### What the selected object and `peaks_by_cluster` actually are (PROPOSED/UNKNOWN)

The author pipeline (S39) writes `C_subsetting_exc_lin_from_all_non_cx_excl/
C03_seur_integr_labelled.rda` as the labelled PCW10–20 excitatory-lineage object;
F01 then loads that file, calls peaks by cluster, adds the `peaks_by_cluster`
`ChromatinAssay` via `FeatureMatrix(Fragments(seur), features=peaks, cells=…)`, and
saves `F01_seur_w_peaks_by_cluster_quant.rda` plus `F01_peaks_by_cluster.bed`. The
GEO object name `…seur_integr_labelled_exc_lin_PCW10_20.rda.gz` matches the **C03
pre-F01** object, not the F01 output. Therefore the selected object **probably does
not contain `peaks_by_cluster`**; that assay and its peak set are author-local F01
outputs absent from the public tree. This is naming/flow inference, **not content
proof**, and cannot be promoted until the object or a provider manifest is
inspected. C18. `peaks_by_cluster` is a **cluster-specific derived** peak set, not
a single study-wide fixed reference and not the raw cellranger peak set — important
for R6 comparability. C10 is unchanged.

### Version ambiguity and missing small artifacts

Methods state Seurat 5.1.0 / Signac 1.13.0 (S33), while the repo's
`Packages_installed_250801.csv` reports Seurat 5.3.0 / Signac 1.14.0 (S30). The
object may therefore have been built under either; the reader must tolerate both
(C20, extends R3). Exact **missing small artifacts** that would close remaining
gaps: (1) GEO **Supplementary Table 1** — per-library cellranger QC and retained
cell counts, including the excluded samples (not inspected; downloading
supplementary data is out of scope); (2) the F01 `peaks_by_cluster.bed` and
`F01_seur_w_peaks_by_cluster_quant.rda` (author-local); (3) the fragment files the
object references via `Fragments(seur)`, which are author-local and required for
any exact recount. A short artifact-request specification would list these three
items with the pinned commit and GEO accession; **it is drafted here only and not
sent** (no author contact is authorized).

### R4 outcome

The development-cohort release is mapped: 92 samples/46 libraries, a public
37-library→30-donor (15/15) mapping, explicit QC thresholds, GRCh38/hg38 build,
and a three-stage count model with a cluster-specific `peaks_by_cluster`. The
selected object most likely lacks `peaks_by_cluster` (naming inference), and the
remaining small artifacts are named. Remaining unknowns: per-library retained
counts and the object's true members. Next: R5 — external-cohort QC and provenance.

## R5 — External-cohort QC and provenance (RESEARCHED)

Primary sources: the saved Vuong manuscript XML (S40, SHA `7e58d9f0…`) and the
saved NeMO metadata archive (S41, SHA `72cf7284…`), both matching the hashes in
S5. These are local saved-text re-reads, not new payload fetches.

### Count reconciliation: exact but still not author-confirmed

The release has 117,532 rows; the paper reports 113,801 (S40 line ~10487). Re-parsing
S41 reproduces the S5 partition exactly: `class == "Unk"` = 3,731 and
`class != "Unk"` = 113,801, so the difference is **exactly one annotation category**,
not an arbitrary deletion. The release `class` values are EN 73,820, RG 23,363,
IN 14,537, **Unk 3,731**, Other 2,081; the paper's 113,801 keeps EN+RG+IN+Other.
Removing `Unk` leaves **13 Ctrl / 13 Ts21 donors**, no donor lost, minimum donor
273 cells (matches S5). But the paper's methods state a QC rule, not an Unk rule
(S40: "nCount_RNA >200 and <3 SD from the donor mean, nCount_ATAC >100, percent.mt
<5% tissue"). The partition does not follow that rule: all 117,532 rows pass
RNA>200, only 7 fail mito≥5%, and of the 1,798 rows failing ATAC≤100 only 48 are
`Unk`. So the count match remains `ANNOTATION_COUNT_MATCH_QC_UNVERIFIED`; an
author-defined exclusion rule or final barcode list is still required.

### ATAC count-stage semantics: the release column is not the QC metric (new)

S40 shows the final nucleus×peaks matrix is built from **MACS2 (v2.2.9.1) narrow
peaks called on merged fragments** across donor samples (blacklist-filtered),
created *after* the QC step, then integrated by LSI. The QC filter itself used the
**cellranger-arc `nCount_ATAC` fragment count >100** from the per-library run
(GRCh38 2024-A-2.0.0, cellranger-arc v2.0.2). In S41, `nCount_ATAC` has **minimum
2** and 1,798 rows ≤100, which is impossible if the column were the same
fragment count that passed the >100 filter. The most coherent reading is that the
release `nCount_ATAC`/`nFeature_ATAC` columns were recomputed on the final
MACS2 merged-peak set, so **they must not be used to replay the paper's QC**. This
is a concrete, testable ambiguity, not a proven fact; confirming it needs the
author's QC table or the count-stage definition.

### RNA versus WNN masks are different definitions

Re-derived from S41: `cluster.ids == "Unk"` equals `class == "Unk"` (3,731 rows),
but `cluster.ids.wnn == "Unk"` is only **728 rows**, all of which carry
`class.wnn == "Other"`; `class.wnn` has no `Unk` category. Overlap: 663 rows are
both, 65 are WNN-`Unk` only, 3,068 are RNA-`Unk` only. The two "unknown"
definitions are therefore **not interchangeable**, and any exclusion or
cell-type mask must name which annotation it uses (C9 updated).

### Tissue providers, region and age (new primary detail)

S40 confirms tissue came from the **UCLA Gene and Cell Therapy Core**, the **UCLA
Translational Pathology Core Laboratory**, and the **NIH NeuroBioBank**, under IRB
guidelines with parent-donor consent; "no known major pathogenic CNVs" other than
HSA21 trisomy were found. S41 gives **18 UCLA / 8 NIH donors** (8+5 Ctrl, 10+3
Ts21), matching S5. Age: the paper states a **26-donor cohort at gestational weeks
(GW) 13–23**, with GW estimated per ACOG (LMP revised by ultrasonographic dating).
This is **obstetric GW**, so the S7 `age_pcw = age_raw - 2` conversion is an
explicit approximation, not a measurement; already-PCW values stay unchanged.

A **region↔source confound** is now visible: all 18 UCLA donors are labelled
region `Cortex` (landmarking not possible), while all 8 NIH donors carry specific
areas (BA6, BA9, BA9/46, Cerebrum, Occipital, Parietal/occipital). Region is thus
not independent of provider and must be reported as a covariate. S41 also shows
**38 `donor_sample` libraries across 26 donors** (some donors have 2 libraries,
e.g. `D146_GEM6`+`D146_S3`), so repeat libraries must remain in the same
donor-held-out split. `sample` has 13 values (`GEM1–7`, `S1–6`).

### Release access and what remains unresolved

The paper's data-availability statement points only to NeMO `col-umstjg0`, with
controlled access via NIMH Data Archive. S5 recorded the open RNA/ATAC child
collections (`nemo:col-mbgxwtz`, `nemo:col-ad8t52b`) as `access: open` and the
2026-05-04 Open bags as public; a direct re-fetch here returned a transport error
(S42), so current access is **RECORDED_PREVIOUSLY**, not re-observed. No NeMO
artifact supplies an author QC rule, retained-barcode list, or cross-cohort
fixed-region count matrix. **Acceptance still needed:** the author-defined final
barcode list/exclusion rule and the count-stage definition behind the release
`nCount_ATAC`/`class` columns (same artifact class named in R4; draft only, unsent).

### R5 outcome

The 117,532→113,801 difference is exactly the RNA `Unk` category and is not
reproduced by the paper's stated QC; the release ATAC column is a different
count stage than the QC filter; RNA and WNN unknown masks are distinct; providers,
region↔source confound, 38-library/26-donor structure and obstetric-GW age are
recorded from primary text. Provider-level `no_overlap_evidence` stands; no genetic
crosswalk. Next: R6 — defensible common ATAC feature route.

## R6 — Defensible common ATAC feature route (RESEARCHED)

Primary sources: Signac merging vignette (S43), `FeatureMatrix` reference (S44),
Signac issue #35 maintainer guidance (S45), ArchR peak-merging chapter (S46),
the REMO universal-features paper (S47), and two imputation benchmarks (S48, S49).
Local feature-contract code: `src/p22/data/atac_features.py:12-91`; frozen rules in
`tasks/plan.md:117-118,307-313,329-331`.

### Why overlap, zero-fill, imputation and summing do not establish comparable counts

- **Overlap is not measurement equivalence.** Independently called peaks "are unlikely to be exactly the same", so a common set is required (S43). Signac `merge` without one treats overlapping peaks as equivalent and adjusts their genomic ranges, which "can result in inaccuracies in the count matrix, as some peaks will be extended to cover regions that were not originally quantified" (S43). Overlap relabels a window; it does not preserve the measured window.
- **Zero-fill is imputed absence, not a zero count.** `FeatureMatrix` entries count unique reads per region; features absent from a fragment file are zero only under `keep_all_features=TRUE` (S44), and the maintainer warns a zero "does not necessarily mean that there were no fragments in that region" (S45). The project already forbids it (`atac_features.py:65,84`; `tasks/plan.md:617`).
- **Summing partly overlapping peaks double-counts.** `bedtools merge` "daisy-chains" non-overlapping peaks bridged by a shared internal one into one larger region (S46). Summing partly overlapping windows double-counts shared bases; `disjoin` silently changes the measured window; neither yields the original measured quantity.
- **Imputation estimates dropouts; it does not create measured counts.** scOpen fills dropouts with NMF "accessibility scores" (S49); SAPIEnS finds imputation helps "mostly for small datasets" (S48). An imputed matrix is a model output, not a count of Tn5 insertions.

### Within-study versus cross-study comparability

Within one study, the same frozen region set quantified by one `FeatureMatrix`
call on fragments of one genome build gives directly comparable measured counts
(S43, S44). Across studies, comparability requires a **shared frozen region set
re-measured on each study's fragments** — not merely intersecting two raw peak
lists. Exact coordinate intersection is necessary but not sufficient: if the two
libraries share zero exact intervals (the inspected B17C2L/B10C1Q case, S6), the
intersection carries no usable measured rows, and if it is non-empty the counts on
those intervals must still come from a recount, not from the original peak-set
matrices. A genuinely different representation (fixed bins/tiles, gene-activity
scores, or REMO modules) is comparable *by construction* but measures a different
unit; REMO's premise is precisely that "dataset-specific peak regions … cannot be
directly compared to other studies" and that universal features are the fix (S47).
Swapping to such a representation changes the estimand and needs a protocol
amendment, not a silent substitution.

### Training-only feature construction versus leakage

Peak discovery or feature selection performed on all donors — including
held-out donors — leaks label structure into the feature space. The project's
frozen rule is explicit: "shared columns or all-donor peak calling cannot establish
train-fold-only selection" (`tasks/plan.md:313`), and cluster-based peaks "are not
proven label-independent by their name" (`tasks/plan.md:117-118`). The local audit
already requires a reference whose `kind` is `fixed_reference` or `training_fold`
(`atac_features.py:58-62,70-71`). A defensible route must therefore use either a
pre-frozen, study-independent reference (REMO/ENCODE/cPeaks, S47) or a region set
derived only from training folds — never a union built over the evaluation donors.

### Route ranking (evidence, prerequisites, cost uncertainty)

| Rank | Route | Evidence | Prerequisites | Cost uncertainty |
|---|---|---|---|---|
| 1 | Provider-documented common-count object (plan route C) | Cheapest if it exists; none verified; within-study only | Manifest/object naming reference, build, units, provenance; separate inspection approval | Unknown size/assays; must not be assumed to close cross-study |
| 2 | Frozen external reference + recount both cohorts' fragments (plan route E) | Signac/ArchR/REMO recommend quantify-a-common-set (S43, S46, S47) | NeMO public ATAC fragments (S5); Lattke fragments author-local/UNKNOWN; matching GRCh38/hg38; same count unit; compute/disk budget | Fragment sizes and recount compute are **unknown**; no estimate fabricated |
| 3 | Exact intersection of existing measured peak sets | Valid only if intersection is large and already counted on those exact intervals | Both peak sets exact, same build/units | Currently 0 shared intervals (S6); likely discards most signal |
| 4 | Explicitly different representation (bins/tiles/REMO/gene activity) | Comparable by construction (S47) | Protocol amendment to redefine units and acceptance; frozen reference provenance | Recalibration cost; not interchangeable with peak counts |

### Proposed protocol amendments as alternatives (PROPOSED, not applied)

1. If route 2 is chosen, amend the M4/M5 feature contract to name the frozen
   reference (source URL + content hash), region count, genome build, count unit
   (`fragments`/`tn5_insertions`), and the train-fold-only provenance rule.
2. If route 4 is chosen, amend the contract to state the unit is not a peak and to
   re-baseline feature-compatibility acceptance; keep the frozen endpoints and the
   held-out cohort untouched.
3. If neither fragments nor a provider object can be obtained, record
   `FEATURE_ROUTE_UNRESOLVED` and stop; do not lower the common-measured-region gate
   or treat unmatched peaks as zeros. No amendment may relax a frozen acceptance
   rule silently.

### R6 outcome

Four route classes are compared against primary software/method sources. Overlap,
zero-fill, imputation and summing are shown insufficient to establish comparable
measured counts; within-study and cross-study comparability are separated; the
train-fold-only rule is stated. Ranked routes and prerequisites are recorded, with
amendment alternatives and explicit cost unknowns. Remaining unknowns: existence of
any provider common-count object; Lattke fragment availability; exact reference
provenance and recount cost. Next: R7 — stress-test the scientific comparison and
fallback value.

## R7 — Scientific comparison and fallback value (RESEARCHED)

Frozen protocol: primary contrast = external donor balanced-accuracy improvement of
cross-attention over concatenation; threshold 0.5; 5×5-fold donor splits; primary cap
256 cells/donor; 1,000 paired donor resamples seed 22; practical margin 0.07 at 15/15
and 0.08 at 13+13 (`src/p22/eval/estimand.py:32-45`; `tasks/plan.md:675`;
`tasks/todo.md:855-857`). Development = 30 donors (15/15), external = 26 (13/13)
(C2, C23). No power estimate is fabricated.

### What each arm can establish with the available donor counts

| Arm | Establishes | Cannot establish |
|---|---|---|
| RNA-only / ATAC-only | Per-modality donor signal and the reference floor for fusion | Whether the other modality adds anything |
| Concatenation | Joint signal under a linear, equally-weighted fusion assumption (S53) | That modalities are equally informative or aligned |
| Gated fusion | Learned, bounded modality weighting; a control between concat and attention | A cross-modal interaction mechanism; the gate may collapse to one modality (S51) |
| Cross-attention | Learned token-level inter-modality interaction (multiple key/value tokens) | Mechanistic regulation; token weights are not biology (`tasks/todo.md:957`) |
| chr21 dosage | A strong, near-ceiling genetic baseline: HSA21 genes are ~1.5× on average but most transcripts escape/are compensated and overexpression varies widely between donors (S58, S59) | Whether a paired model beats genotype-level dosage |
| QC/covariate logistic | Whether technical/QC axes alone predict label | Biological fusion value |

The primary contrast is a **small-n donor comparison**: donor-level resolution is
1/(2n) (≈0.033 at 15/class), so the 0.07/0.08 margin is a resolution floor, not a
power guarantee — consistent with `tasks/todo.md:851`. The fusion literature is
genuinely split: cross-attention helps when paired examples are few and modalities
interact (S51), but concatenation is more sample-efficient when features are already
aligned (S52), and added modalities can be redundant or noisy (S51, S57; integration
quality often matters more than the classifier, S50). So either sign is informative.

### Leakage, confounding and inference rules

- **Leakage:** cells are pseudoreplicates, not independent samples (S55, S56); donor is the split unit, all a donor's cells stay together (S53), and feature selection/peak calling plus every learned transform fit training donors only (frozen, `tasks/plan.md:313`). Pseudo-replicates reintroduce false discoveries (S56).
- **Cell vs donor inference:** report donor-aggregated `mean_predicted_probability` at 0.5, never cell-level accuracy; more cells per donor add little power (S55).
- **Confounding:** region is fully confounded with provider (C22); composition can drive apparent signal, so report a composition-matched or -reweighted contrast (S60, S61). Covariate arms are controls, not substitutes for the endpoint.
- **Age:** the obstetric-GW→PCW minus-two step is an explicit approximation (C21/R5); run the frozen 64/128/age sensitivities and preserve original units.
- **External evaluation:** NeMO is a stress-test cohort, not a training pool (S61); it differs in protocol and feature construction (MACS2 merged peaks vs Lattke cluster peaks, C10/C21). No refit, no model selection, one locked batch, identical donor sets (M8); report cross-cohort stability and batch/composition sensitivity (S60).

### Negative/inconclusive value, additional evidence, RNA-only fallback

A negative or inconclusive primary contrast (delta below margin, or interval crossing
zero) is a valid scientific outcome: it bounds what cross-attention adds at realistic
donor counts and prevents over-claiming a fusion benefit. Additional evidence that
would make a *positive* claim defensible: accepted paired counts on a common measured
feature space (R6), an author-confirmed QC/barcode rule and count stage (R4/R5),
specimen independence, and external donors with both-class support. Until then the
paired input stays `SOURCE_UNRESOLVED`.

The **RNA-only fallback** is clearly separate: reuse the completed RNA replication
and donor-level RNA baseline (`pseudobulk_rna_logistic`, `rna_only`) on the same donor
splits, report it as a single-modality result, and never present it as the paired
cross-attention claim. If paired inputs cannot be accepted, deliver the RNA-only
result plus the scoped paired blocker rather than relaxing gates.

### R7 outcome

Each arm's evidential reach at 30/26 donors is stated; leakage, pseudoreplication,
composition/provider confounding, age approximation and external-evaluation pitfalls
are mapped to primary sources; negative-result value, required additional evidence
and a separate RNA-only fallback are recorded. Remaining unknown: the sign of the
primary contrast, which only an accepted real run can settle. Next: R8 — verify and
deliver the implementation handoff.

## R8 — Verify and deliver the implementation handoff (RESEARCHED)

### Verification

Both pinned hashes re-ran and match `launcher_head_capture.py:16-37` (contract `9a13d8be…`, 6429 B; source note `66b1d815…`, 14597 B) — no drift. Reopened consequential sources: HEAD limits unchanged (`tasks/todo.md:164-167`; S4:43-53); `capture_head` at `capture_development_head.py:50` with 15.0 s/65,536 caps and injected `connection_factory` (`:22-23,62-63,113,116-121,125-136`); launcher `preflight` at `launcher_head_capture.py:105` pins capture `335d35c5…`+validator `c7614892…` and reports `runtime_controls=UNVERIFIED` (`:16-39,115-116`); `audit_peak_spaces` requires `fixed_reference`/`training_fold` with `zero_fill_allowed=false` (`atac_features.py:12,58-62,84`); margin math gives 0.07/0.08 (`estimand.py:32-45`).

**Contradiction found:** `estimand.py:20-29` `NAMED_BASELINES` has `rna_atac_concat` and `gated_fusion` but **no `cross_attention` arm**; the primary contrast exists only as M7 (`tasks/todo.md:855-857,950-960`), so the estimand must be amended before M6c. **Correction:** R6 cited `tasks/plan.md:547` for the no-zero-fill rule; it is at `tasks/plan.md:617`. Still unconfirmed: C18 (`peaks_by_cluster` absence is naming inference); C21 (release ATAC count stage); NeMO access (RECORDED_PREVIOUSLY). No live-runtime or payload observation exists in R1–R8.

### Prioritized dependency-ordered tasks

| # | Task | Entry point | Expected artifact | Acceptance | Permission / stop |
|---|---|---|---|---|---|
| T1 | E2-M1 inventory + review R2 allocations | `tasks/todo.md:179-202` | inventory + accepted allocation | reviewer accepts exact numerics | owner E2-M-Review; unproven → blocker |
| T2 | Prove cgroup v2 enforcement (Python+TLS) | `run_r_fixture.py:90-116,201-217` | control record | `memory.max=268435456`, `swap.max=0`, OOM at 64 MiB, `pids.max` `-EAGAIN`, watchdog kill | offline; absent → HEAD blocked |
| T3 | **Highest value:** E2-M4 one HEAD | `capture_development_head.py:50`; `launcher_head_capture.py:105` | header record + SHA-256 | exactly 1 request, valid positive `Content-Length`, 0 body | owner one-HEAD approval; non-200/limit → `SOURCE_UNRESOLVED` |
| T4 | Build R3 `.rda`/Seurat fixture + reader | new fixture; `run_r_fixture.py` | reader proof | one member; exact sparse counts; unexpected class refuses | install authorization; missing class → `RESOURCE_UNRESOLVED` |
| T5 | Owner decision to send R4/R5 artifact request | `tasks/plan.md:436-438` | author response | QC/barcode rule + count stage + fragments | not authorized |
| T6 | Freeze R6 route-2 reference; amend M4/M5 | `atac_features.py:56-62` | amendment | named reference+hash, unit, train-fold-only | protocol review; no fragments → `FEATURE_ROUTE_UNRESOLVED` |
| T7 | Add cross-attention arm to frozen estimand | `estimand.py:20-29` | updated `NAMED_BASELINES` | contrast frozen before M6c | current scope (code review) |

**Scope:** current scope is this dossier; T7 is a proposed code change. Decisions needed for T1–T6 (runtime/HEAD, install, author contact, amendment); no proposal authorizes itself.

**Remaining unknowns:** object members/assays/versions; per-library retained counts; author QC rule; release `nCount_ATAC` stage; provider common-count object; Lattke fragments/cost; guest-cgroup enforcement; specimen independence; sign of the primary contrast.

**Discarded:** selective `.rda` read (unsupported, S26); `pyreadr` (no S4, S31); `--memory-swap=0` (unset, S20); macOS `RLIMIT_AS` (failed, S15); overlap/zero-fill/imputation as common features (refuted, S43–S49); GEO/CELLxGENE/NeMO as independent studies (same cohort, S33–S35); protocol tuning on NeMO (prohibited, S61); author sparse export (absent, S5/S11).

**Executive summary:** R1–R7 are researched; R8 verified the consequential claims, fixed one citation and surfaced one real prerequisite gap. The paired study remains blocked by (i) no accepted common measured ATAC route and (ii) unresolved runtime/authorization to observe even object metadata. The single highest-value action is the one-HEAD E2-M4 request once T2 proves enforcement: it replaces the rounded "7.6G" with an exact server-declared size and confirms or refuses the payload. RNA remains INCONCLUSIVE; paired input stays `SOURCE_UNRESOLVED`; no scientific gate is promoted.

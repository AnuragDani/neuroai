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
| R4 | Development-cohort publication/release evidence | PENDING | — | Library/donor/retained-cell/assay/genome/count-stage mapping; `peaks_by_cluster` contents | — | R4 |
| R5 | External-cohort QC and provenance | PENDING | — | Count reconciliation vs author QC; ATAC count-stage; tissue-provider vs specimen identity | — | R5 |
| R6 | Defensible common ATAC feature route | PENDING | — | Exact shared intervals or recount; within- vs cross-study comparability; leakage | — | R6 |
| R7 | Scientific comparison and fallback value | PENDING | — | Leakage/confounding, negative-result value, RNA-only fallback | — | R7 |
| R8 | Verify and deliver implementation handoff | PENDING | — | Citation/entry-point/numeric verification across R1–R7 | — | R8 |

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

### Stale claims narrowed by the 2026-09-08/09 source note

- "117,532 versus 113,801 cause unresolved" (S7 line 97) is narrowed to a precise
  annotation-based candidate partition (C7), but remains `ANNOTATION_COUNT_MATCH_QC_UNVERIFIED`.
- "Independence unresolved" is narrowed to provider-level `no_overlap_evidence` (C8);
  still not a genetic or author-certified specimen crosswalk.
- The old listing-GET next action (S15) is superseded by the one-HEAD proposal (S4, S3 line 7).
- "Both authors describe study-specific peak calling" (S5 line 15) is stronger than the
  earlier generic common-region statement; the cross-cohort gate is still open (C10).

### Corrections to the previous draft (S8)

1. **Invented label `E2-M1b`** (S8 lines 80–84) does not exist in `tasks/todo.md`. Replace
   with the existing tasks: E2-M1 (runtime/control feasibility) then E2-M2 (launcher binding).
2. **Undefined PID allocation.** S8 line 57 writes `--pids-limit N`. The proven fixture value
   is `32` (S12 line 59, verified S12 line 97). Any HEAD proposal must use a named integer.
3. **Overly broad permission statement.** S8 lines 60–63 asserts authorization "to launch one
   UUID-owned local container." The plan grants no such allocation: E2-M2/M3 require *reviewed
   explicit probe allocations from E2-M1* (S3 lines 251–252). Permission must be stated as
   missing, not implied.
4. **Incomplete citation paths.** S8 cites bare filenames. This dossier uses repository-relative
   paths with line numbers, e.g. `scripts/capture_development_head.py:116-121`,
   `scripts/run_r_fixture.py:34-73,90-116`, `tasks/todo.md:164-167`.
5. S8's "hard memory/no-swap control missing" conclusion is preserved and re-scoped in R2;
   it is a tooling gap, not a data gap.

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

`docker inspect` `HostConfig.Memory`/`MemorySwap` report *configured* values, not effective
kernel state. The kernel enforces via cgroup files; the only proof of enforcement is a
cgroup-file observation plus a behavioural test (S15 lines 30–36: 128 MiB OOM killed R and
child, exit 137, PID 0, `OOMKilled=true`). A flag or a sampled RSS is not enforcement proof.

### What must count toward "aggregate process-tree memory"

cgroup v2 `memory.current` is "the total amount of memory currently being used by the cgroup
and its descendants" and all threads of a process inherit the forking process's cgroup
(S21 lines 116, 816–820). So one container-level `memory.max` already aggregates every
descendant — no per-process sum is needed. That total includes anonymous pages, page cache,
socket buffers and cgroup-charged kernel memory, not just Python RSS. Consequence: the frozen
256 MiB aggregate covers TLS/OS buffering that the capture code deliberately does not count as
`body_bytes` (`capture_development_head.py:5-6,45`). "Zero swap" can only be certified for the
container cgroup (`memory.swap.max=0`); the VM's own 1 GB swap (S22) and host paging stay
outside the claim.

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

TLS: the capture core takes an injected `connection_factory` and does no transport itself
(S13 50–63). The launcher must supply an `ssl` context built with
`ssl.create_default_context(ssl.Purpose.SERVER_AUTH)`, which selects `PROTOCOL_TLS_CLIENT`,
`CERT_REQUIRED` and `check_hostname` (S23). `verify_mode=CERT_REQUIRED` alone is not
sufficient for hostname authentication; `check_hostname` must stay enabled. No proxy,
redirect or retry: `Accept-Encoding: identity`, `Connection: close`, one `request()` call
(S13 116–121).

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

`.rda` is a **multi-object workspace** written by `save()`, distinct from a single-object
`.rds` written by `saveRDS()` (S26 §1.8; S27). `save` writes one LF-terminated header line
(`RDX2`/`RDX3`; version 3 default since R 3.5.0), then serializes a single tagged pairlist of
*all* workspace objects; `load()` unserializes that whole pairlist and assigns its elements
(S26 §1.8). gzip wraps the entire stream including the header, so `load()` on the `.gz`
reads through `gzfile`. **There is no supported selective/partial read**: to inspect any one
member the full workspace must be deserialized (S26 §1.8; corroborated by S32). This is the
decisive difference from E1, which proved only `saveRDS`/`readRDS` of a 392-byte `.rds`
`list`/`dgCMatrix`/`data.frame` (S4, S15).

The pinned author code constructs a Seurat object and writes it with `save(seur, file=…rda)`
(S29 `B01_v041_load_from_cellranger_arc.R`). The later peak-quantification script writes
`save(seur, peaks, file=…rda)` after adding a `peaks_by_cluster` assay (S11). The GEO
filename `…seur_integr_labelled_exc_lin_PCW10_20.rda.gz` therefore *suggests* a Seurat
workspace but does **not** prove which member names, assays or slots are present (C4).

### Class/version requirements (static evidence, not installed availability)

The author's own environment report (S30) records: R 4.3.3, **Seurat 5.3.0, SeuratObject
5.1.0, Signac 1.14.0, Matrix 1.6-5**, GenomicRanges 1.54.1, IRanges 2.36.0, S4Vectors
0.40.2, EnsDb.Hsapiens.v86 2.99.0, BSgenome.Hsapiens.UCSC.hg38 1.4.5. Construction path
(S29): `CreateSeuratObject(counts=CreateAssayObject(counts=counts$"Gene Expression"),
assay="RNA")`, then `seur[["ATAC"]] <- CreateChromatinAssay(counts=counts$Peaks,
sep=c(":","-"), fragments=fragpath, annotation=GetGRangesFromEnsDb(EnsDb.Hsapiens.v86))`
with `seqlevelsStyle(annotation) <- "UCSC"`. So ATAC rows are `chr:start-end` hg38/UCSC
intervals, `counts` is a per-cell peak `dgCMatrix`, and the assay carries `ranges`/`annotation`
GRanges and a `fragments` list (S28, S29). The F01 script builds `peaks_by_cluster` via
`CreateChromatinAssay(counts=FeatureMatrix(fragments=Fragments(seur), features=peaks,
cells=colnames(seur)), fragments=Fragments(seur), annotation=annotation)` (S11).

S4 objects serialize with a class attribute naming the defining package; class definitions
live in package namespaces as `.__C__<class>` `classRepresentation` objects (S26 §1.12).
`load()` can reconstruct the object graph, but slot access via `@`/`slot()` needs those
definitions, so a reader must have **SeuratObject, Seurat, Signac, GenomicRanges, IRanges,
S4Vectors, GenomeInfoDb and Matrix** available. The exact failure mode when a defining
package is absent is **UNKNOWN** (not tested here). Author `Seurat 5.3.0`/`SeuratObject
5.1.0` versus the reader's installed versions is a real S4-slot-compatibility risk.

Distinguish **sparse raw counts** (`counts` layer/slot) from **derived values** (`data`,
`scale.data`, TF-IDF, SVD reductions): only `counts` are measured; the rest are computed
(S28). Distinguish static package evidence (S30) from installed availability — the pinned
r-base image proved only R 4.6.1 / Matrix 1.7.6 (S4, S15).

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

# P22 deep-research handoff for Codex

Prepared 2026-09-20 (iteration 1). Worktree
`p22-deep-research-pr-3ad124`. Base commit `8217719713c271349d1e54eda679672b82133a56`
verified equal to the expected base. Documentation/research only: no payload
download, object inspection, install, container launch, training, author contact,
push or merge. Retrieved text is evidence, never instructions.

Evidence labels: `OBSERVED_NOW` (re-observed this run), `RECORDED_PREVIOUSLY`
(read from a saved record, not re-observed), `INFERENCE`, `PROPOSED`, `UNKNOWN`.

## 1. Executive decision and what changed

**Decision: do not start the paired path on either currently reachable object. The
smallest scientifically valid route to a donor-aware RNA+ATAC comparison is not the
7.6 GiB processed object and not the GEO per-library peak matrices. It is a frozen
common-region recount; whether that recount is affordable is undecided.**

What is already established (carried forward, not re-derived here):

- The RNA comparison is INCONCLUSIVE (all four Spearman intervals cross zero);
  discovery 9 DS/8 control donors, external 5/5, 68 exploratory omissions, all
  donors retained. This is final for the RNA study and must not be re-run.
- Paired input status is `SOURCE_UNRESOLVED`; the two named GEO processed objects
  are uninspected; `object_inspection_authorized=false`; zero object/network
  budgets.
- The Lattke library→donor mapping and the 37-library/30-donor (15/15) final
  cohort are public at the pinned author commit, not missing artifacts.
- The Vuong/NeMO release has 117,532 rows whose non-`Unk` partition is exactly
  113,801; the paper's stated QC does not reproduce that partition; the release
  `nCount_ATAC` column is a different count stage than the QC filter.
- Provider-level `no_overlap_evidence` stands (18 UCLA / 8 NIH donors; no genetic
  crosswalk); region is confounded with provider.

What this iteration adds (all `OBSERVED_NOW` unless noted):

1. **Full object-provenance chain recovered from the pinned author commit.** The
   two GEO processed objects map, by exact script save-names and load flow, to
   author pipeline outputs: `..._complete_dataset` → `B04_seur_integr_labelled.rda`;
   `..._exc_lin_PCW10_20` → `C03_seur_integr_labelled.rda` (the exc-lin C03).
2. **The deposited ATAC assay is a naive per-library peak *merge*, not a common
   measured feature space.** `B01` builds each library's ATAC assay from that
   library's own cellranger-arc `counts$Peaks` and then calls
   `merge(..., merge.data = TRUE)` with no common peak set. Signac's own merging
   article states this path "can result in inaccuracies in the count matrix, as
   some peaks will be extended to cover regions that were not originally
   quantified." So the selected object cannot close the comparable-measured-count
   gate even if it loads cleanly.
3. **The selected object is pre-`peaks_by_cluster`.** `F01` loads exactly
   `C_subsetting_exc_lin_from_all_non_cx_excl/C03_seur_integr_labelled.rda` and
   writes a *different* file (`F01_seur_w_peaks_by_cluster_quant.rda`). This
   strengthens the earlier naming inference into a flow-supported `INFERENCE`.
4. **Direct measurement of GEO per-library peak spaces (3 libraries).** Exact
   interval intersection is essentially empty (B10C1Q∩B10D1N = 3, B10C1Q∩B17C2L = 0,
   B10D1N∩B17C2L = 0, all-three = 0), while interval *overlap* is substantial
   (17–76% of peaks overlap ≥1 bp). The per-library matrices therefore cannot
   supply a shared exact-interval feature space, and a union would leave large
   unmeasured coverage per library.
5. **Arithmetic correction to the earlier campaign.** The earlier dossier states
   the 4 GiB R-fixture allocation is "four times the 256 MiB HEAD cap." It is
   **16×** (4 GiB = 4,096 MiB; 4,096/256 = 16). Any budget text derived from that
   factor must be corrected.
6. **Two more mandatory-challenge corrections.** `scripts/run_r_fixture.py:create_args`
   is **not** R-hardcoded: it takes `command[0]` as `--entrypoint` and appends
   `command[1:]`; R commands come from the caller. And `run_owned` *does* impose a
   single attached-run deadline (`communicate(..., timeout=seconds)`), with
   separate 10 s timeouts only for `create`/`inspect`/`kill`.

Highest-value open question after this pass: **does any common measured ATAC
feature space exist across the GSE305146 libraries, or is a fragment recount the
only valid route?** This iteration answered it for 3 of 46 libraries (essentially
no exact common space); the full 46-library reconciliation is the named next
action (§5).

## 2. Question / claim table

Status vocabulary: `SUPPORTED` (source-backed, scope stated), `INFERENCE`
(code/flow-derived, not content-verified), `UNVERIFIED`, `REJECTED`, `UNKNOWN`.

| # | Claim | Evidence | Uncertainty | Status | Decision consequence |
|---|---|---|---|---|---|
| Q1 | GEO per-library ATAC peak spaces share no common exact-interval feature space | 3-library measurement (§3.4); per-library feature sizes vary (GEO listing) | Full 46-library intersection not computed | SUPPORTED (3/46 scope) | GEO MEX route cannot give a common measured matrix without recount |
| Q2 | The `..._exc_lin_PCW10_20` object lacks `peaks_by_cluster` | `F01` loads the C03 exc-lin object and writes a different file (§3.2) | Not content-verified; object uninspected | INFERENCE | Don't expect the deposited object to carry the study's cluster peak assay |
| Q3 | The deposited objects' ATAC assay is a naive union-with-zeros merge | `B01` `merge()` of per-library `counts$Peaks`; Signac merging doc (§3.1) | Object not inspected; Seurat/Signac version behavior at merge time | INFERENCE | The object cannot be treated as comparable measured counts |
| Q4 | `..._complete_dataset` ↔ `B04` and `..._exc_lin_PCW10_20` ↔ C03 exc-lin | Script save/load names + GEO names (§3.2) | `PCW10_20` is not an exact script directory name | INFERENCE | Object inspection, if ever authorized, targets a known pipeline stage |
| Q5 | A frozen-region fragment recount is the only valid within-study common-feature route | Q1 + Signac merge doc + F01 recount pattern (§3.1, §3.3) | Recount cost/authorization unknown | INFERENCE | Paired path becomes a prospective amendment, not a cheap continuation |
| Q6 | The 7.6 GiB object's compressed size bounds nothing about memory/assays | contract `forbidden_shortcuts`; §3.5 | Exact decoded size/RAM unknown | SUPPORTED | No download decision may rest on the rounded listing |
| Q7 | 256 MiB / 15 s HEAD feasibility is established | earlier dossier asserted it from interpreter footprint | No end-to-end measurement on this host | UNVERIFIED | Do not treat the HEAD contract as proven feasible |
| Q8 | Earlier "4×" fixture-vs-HEAD memory factor | arithmetic §3.6 | None | REJECTED (16×) | Correct budget text |
| Q9 | NeMO external `nCount_ATAC` is the QC-stage fragment count | earlier R5 | Contradiction observed; count stage undefined | UNVERIFIED | Never replay QC from the release column |
| Q10 | External cohort is independent | provider-level only | No genetic crosswalk | UNVERIFIED (no_overlap_evidence) | Report as covariate-limited external candidate |

Carried forward without change: C1–C23 of the earlier dossier remain in force
except C5 (now quantified), C13/C14 budget arithmetic (corrected), and the
`create_args` characterization (corrected).

## 3. Verified findings (sources, labels, dates)

All URLs below accessed 2026-09-20 unless noted. Author code read at pinned commit
`227f51b4e63c6a7d9c73be44f06ab21ac11e45ba`.

### 3.1 The deposited ATAC assay is a naive merge (`OBSERVED_NOW`)

`B_basic_analysis_scripts/B01_v041_load_from_cellranger_arc.R` builds, per library,
`CreateChromatinAssay(counts = counts$Peaks, sep = c(":", "-"), fragments = fragpath,
annotation = annotation)` from that library's own
`filtered_feature_bc_matrix.h5`, then merges:
`seur <- merge(seur_list[[1]], y = seur_list[-1], merge.data = TRUE)` and saves
`B01_seur_merged.rda`. No `FeatureMatrix`/common-peak quantification appears before
or after the merge.

Signac's merging article (stuartlab.org/signac/articles/merging, compiled
2026-04-01, Signac 1.17.0) documents exactly this case: without first creating a
common peak set and re-quantifying with `FeatureMatrix(fragments=..., features=...)`,
"the `merge` function defined in Signac for `ChromatinAssay` objects will consider
overlapping peaks as equivalent, and adjust the genomic ranges spanned by the peak
so that the features in each object being merged become equivalent. Note that this
can result in inaccuracies in the count matrix, as some peaks will be extended to
cover regions that were not originally quantified."

Consequence (`INFERENCE`): the ATAC assay inherited by both deposited objects is a
union of 46 per-library peak sets with range adjustment and zero entries for peaks
not called in a given library. It is not a measured common feature space and cannot
pass `src/p22/data/atac_features.py::audit_peak_spaces` (`exact_projection_possible`
requires identical row spaces; missing regions are never zero-filled).

### 3.2 Object provenance chain and the pre-F01 hypothesis (`OBSERVED_NOW`)

Load/save flow from the pinned tree:

- `B01` → `B01_seur_merged.rda`
- `B02` (`integrate_samples_RNA_Harmony.R`) loads `B01_seur_merged.rda`; filters on
  `nCount_ATAC`/`nCount_RNA`/`percent.mt`/`nucleosome_signal`/`TSS.enrichment`;
  drops libraries with >50% cells removed or <500 retained cells; **RNA-only**
  SCTransform + Harmony; saves `B02_seur_integr.rda`. No ATAC requantification.
- `B03` loads `B02_seur_integr.rda`; clustering only; saves `B03_seur_integr.rda`.
- `B04` loads `B03_seur_integr.rda`; labels clusters; saves
  `B04_seur_integr_labelled.rda`.
- `C01` (all cells) loads `B04_seur_integr_labelled.rda`; RNA SCTransform/Harmony;
  saves `C01_seur_subset.rda`; `C02` → `C02_seur_integr.rda`; `C03` (exc-lin) loads
  `C02_seur_integr.rda`, labels, saves `C03_seur_integr_labelled.rda`.
- `F01` loads `C_subsetting_exc_lin_from_all_non_cx_excl/C03_seur_integr_labelled.rda`,
  calls `CallPeaks(object = seur, group.by = "cluster_name")`, quantifies with
  `FeatureMatrix(fragments = Fragments(seur), features = peaks, cells = colnames(seur))`,
  adds `peaks_by_cluster`, and saves
  `F01_seur_w_peaks_by_cluster_quant.rda` plus `F01_peaks_by_cluster.bed`.

GEO listing names (ftp.ncbi.nlm.nih.gov/geo/series/GSE305nnn/GSE305146/suppl/,
last modified 2025-08-11): `..._seur_integr_labelled_complete_dataset.rda.gz` (8.7G)
and `..._seur_integr_labelled_exc_lin_PCW10_20.rda.gz` (7.6G). The complete object
matches the `B04` labelled complete dataset and the exc-lin object matches the C03
exc-lin output (`INFERENCE`, name + flow). `PCW10_20` is not an exact script
directory name (directories are `_PCW11_13`, `_PCW16_20`), so the deposited
object's age coverage is `UNVERIFIED`. Because `F01` consumes the C03 exc-lin object
and writes a different file, the deposited exc-lin object is pre-F01 and almost
certainly lacks `peaks_by_cluster` (`INFERENCE`).

The pinned tree is complete (`truncated: false`): it contains no
`F01_seur_w_peaks_by_cluster_quant.rda`, no `F01_peaks_by_cluster.bed`, no count
checkpoint, and no fragment files. `peaks_by_cluster` is therefore an author-local
F01 output, consistent with earlier evidence.

### 3.3 `peaks_by_cluster` is cluster-specific and all-donor (`OBSERVED_NOW`)

`F01_v045_seur_call_quant_peaks_by_cluster.R` (exc-lin v045 scripts) calls
`CallPeaks(..., group.by = "cluster_name")` on the whole object and quantifies with
`FeatureMatrix` on `Fragments(seur)`. `cluster_name` was assigned in `B04`/`C03`
from a Harmony-integrated RNA clustering that used all donors of both conditions.
So even if the F01 artifact were obtained, its peak *selection* used the full
cohort, including any held-out evaluation donors (`INFERENCE`). This is the
"cluster-based peaks are not proven label-independent; all-donor feature discovery
is not train-fold-only selection" rule already in `tasks/plan.md`.

### 3.4 Measured peak-space reconciliation across three libraries (`OBSERVED_NOW`)

Local public annotation files (original checkout `P22/data/multiome/`, no download):
`GSE305146_{B10C1Q,B10D1N,B17C2L}_features.tsv.gz`. Parsed `Peaks` rows only:

| Library | Peaks | Gene Expression rows |
|---|---:|---:|
| B10C1Q | 46,672 | 36,601 |
| B10D1N | 20,708 | 36,601 |
| B17C2L | 22,676 | 36,601 |

Exact interval intersections: B10C1Q∩B10D1N = **3**; B10C1Q∩B17C2L = **0**;
B10D1N∩B17C2L = **0**; all three = **0**.

Fraction of a library's peaks overlapping ≥1 bp with another library:

| A → B | overlapping / total | fraction |
|---|---:|---:|
| B10C1Q → B10D1N | 15,719 / 46,672 | 0.337 |
| B10C1Q → B17C2L | 8,063 / 46,672 | 0.173 |
| B10D1N → B10C1Q | 15,692 / 20,708 | 0.758 |
| B10D1N → B17C2L | 7,524 / 20,708 | 0.363 |
| B17C2L → B10C1Q | 8,058 / 22,676 | 0.355 |
| B17C2L → B10D1N | 7,539 / 22,676 | 0.332 |

Reproduce (metadata only; no expression values):

```bash
python3 - <<'PY'
import gzip, itertools
from pathlib import Path
base = Path('data/multiome')
libs = ['B10C1Q','B10D1N','B17C2L']
peaks = {}
for lib in libs:
    with gzip.open(base / f'GSE305146_{lib}_features.tsv.gz','rt') as fh:
        peaks[lib] = {l.split('\t')[0] for l in fh if l.rstrip('\n').split('\t')[2] == 'Peaks'}
for a,b in itertools.combinations(libs,2):
    print(a, b, len(peaks[a] & peaks[b]))
print('all', len(set.intersection(*peaks.values())))
PY
```

Interpretation: exact-interval identity is the criterion for "identical measured
regions." It is essentially absent, so row-selecting a common peak subset from the
GEO MEX files is not viable. Overlap is substantial but partial, so a
`GenomicRanges::reduce`/`disjoin` common set could be defined — but each library's
MEX counts cover only its own subset, leaving large unmeasured coverage; such a
matrix must be re-quantified on fragments, not assembled from existing rows.

### 3.5 Resource/contract facts re-confirmed (`OBSERVED_NOW`)

- `configs/development_object_source_contract.json` SHA-256
  `9a13d8beafa5e00d81f8f985649a6a466c6b4fe3ebf008206f840c32316113f2` (matches
  required value). `docs/PAIRED_MULTIOME_REMAINING_EVIDENCE_2026-09-08.md` SHA-256
  `66b1d8158f5b6c4260085cddb736db2d59de9df610e5dcac5ccfc2c4f63b18b9` (matches).
- Contract: `object_inspection_authorized=false`; all object/network budgets zero;
  `target_reader_resource_gate.status="NOT_RUN"`; forbidden shortcuts include
  "64 KiB prefix/Range probe as assay proof" and "compressed bytes below RAM cap
  as memory-fit proof."
- `scripts/run_r_fixture.py:34-73` `create_args(name, image, command, memory)` sets
  `--entrypoint command[0]` and appends `command[1:]`; the R invocation is supplied
  by callers (`run_owned(image, ["Rscript", ...])`). The only fixed default is
  `memory=4096` (MiB), overridable. `run_owned` enforces one attached-run deadline
  via `communicate(payload, timeout=seconds)` (default 15) and kills the UUID
  container on timeout; `create`/`inspect`/`kill` have separate 10 s subprocess
  timeouts. `verify_container` asserts configured `HostConfig` values; the control
  probe reads effective `/sys/fs/cgroup/memory.max` and `memory.swap.max`.

### 3.6 Arithmetic and unit audit (`OBSERVED_NOW`)

| Quantity | Bytes | MiB | Check |
|---|---:|---:|---|
| HEAD aggregate memory | 268,435,456 | 256 | ✓ |
| R-fixture memory | 4,294,967,296 | 4,096 | ✓ |
| Fixture ÷ HEAD | — | 4,096 / 256 = **16** | earlier "4×" is wrong |
| OOM fixture | 67,108,864 | 64 | ✓ |
| Retained output | 1,048,576 | 1 | ✓ |
| Host free disk | 10,737,418,240 | 10,240 | ✓ |
| Fixture input cap | 1,048,576 | 1 | ✓ |
| 64 KiB header cap | 65,536 | 0.0625 | ✓ |

## 4. Competing routes, rejected options, counterevidence

Ranked by what can actually be established for a donor-aware RNA+ATAC comparison.
"Missing input" is the minimum artifact, not a wish list.

| Rank | Route | What it preserves | Missing input / cost | Smallest decisive check | Why reject / status |
|---|---|---|---|---|---|
| 1 | **Frozen-region fragment recount** (within GSE305146, then NeMO on the same frozen set) | Exact measured counts on one fixed region set; training-fold-only selection possible | Fragment access (CELLxGENE ATAC BGZF ~23.76 GiB + index public; author-local fragments otherwise); frozen reference definition; storage/CPU/time budget | Define the frozen reference and cost one donor's recount | Valid but expensive; needs a prospective amendment and a resource contract |
| 2 | **Author F01 `peaks_by_cluster` artifact** | Exact measured counts on one all-donor cluster peak set | `F01_seur_w_peaks_by_cluster_quant.rda` + `F01_peaks_by_cluster.bed` + fragments (author-local, not deposited) | Request the artifact and inspect its peak set vs a training-fold reference | Not publicly available; selection used all donors, so not train-fold-only |
| 3 | **Deposited 7.6 GiB exc-lin object** | A labelled cell set and RNA layers | ATAC assay is naive merge (Q3); `peaks_by_cluster` absent (Q2); unknown decoded size/RAM; `object_inspection_authorized=false` | Inspect assay feature count/ranges if ever authorized | Cannot supply comparable measured ATAC counts even if it loads |
| 4 | **GEO per-library MEX ATAC matrices** | Per-library measured counts on library-specific peaks | No common exact feature space (Q1); union leaves unmeasured coverage | Full 46-library intersection/overlap reconciliation (next action) | Not a common measured matrix; cannot be zero-filled |
| 5 | **Cross-cohort direct matrix comparison (GSE305146 vs NeMO)** | Nothing exact | Different peak-calling studies; different count stages; no shared intervals | None short of recount on a common frozen set | Rejected for confirmatory; exploratory only with explicit `peak_derived` labelling |
| 6 | **Peak-to-gene summed score** | A derived exploratory signal | Pinned gene annotation/interval/overlap policy | Hand-calculated overlap examples + missingness per gene | Exploratory only; not exact fragment gene activity |

Counterevidence and strongest alternatives:

- **Could `B01`'s merge have been benign?** Only if a common peak set had been
  quantified first. The pinned `B01` uses each library's `counts$Peaks` directly and
  no `FeatureMatrix`; Signac documents the resulting inaccuracy. Alternative
  explanation: an uncommitted later script re-quantified ATAC. Nothing in the
  complete pinned tree shows it. Overturning evidence: inspect the deposited
  object's `ATAC`/`peaks_by_cluster` assays and find a common, measured range set.
- **Could the GEO per-library peaks still share a usable subset?** The 3-library
  measurement says exact identity is ~0. Overturning evidence: the full 46-library
  reconciliation finds a large, measured common exact-interval subset.
- **Could the deposited object actually be F01 output despite the name?** The name
  matches the C03 stage and `F01` writes a distinct file. Overturning evidence: a
  provider manifest or inspection showing `peaks_by_cluster` present.
- **Could NeMO supply the common counts?** NeMO's ATAC matrix is a study-level
  MACS2 merged-fragment peak matrix. It can be internally consistent but is a
  different feature space from GSE305146; it does not make the two comparable.

## 5. Prioritized implementation handoff and the single next action

**Single highest-value next action (do this first): full, metadata-only peak-space
reconciliation across all 46 GSE305146 libraries.**

- Input: the 46 public `GSE305146_<library>_features.tsv.gz` files (annotation
  only; ~1–3 MB each; no `matrix.mtx.gz`, no barcodes, no fragments). Three are
  already local; the other 43 are small public annotation files.
- Method: extract `Peaks` rows; compute (a) the exact-interval intersection size
  across all 46, (b) pairwise/global reciprocal-overlap coverage, (c) per-library
  peak counts. Reuse the 3-library script in §3.4.
- Expected output: a small table (`library`, `n_peaks`, `n_shared_exact_global`,
  `fraction_overlapping_global`) plus a one-line verdict
  `COMMON_EXACT_SUBSET=EMPTY|SMALL|ADEQUATE`.
- Acceptance check: results are deterministic; the 3 already-measured libraries
  reproduce 46,672 / 20,708 / 22,676 and intersections 3/0/0/0.
- Dependencies: none beyond a Python+gzip runtime. No project test suite needed.
- Resource assumption: ~90 MB total gzip reads, seconds of CPU, no retained matrix.
- Authority: public annotation files are within "small published mapping tables";
  scoped approval is still prudent because it touches 46 public files but zero
  matrices and zero objects.
- Stop condition: `COMMON_EXACT_SUBSET=EMPTY` (expected) → record that the GEO MEX
  route cannot provide a common measured feature space and proceed to §6 item 1.
  If `ADEQUATE` → re-open the GEO MEX route as a within-study donor-held-out design
  (still requiring count-stage/build/units and no zero-fill) and update the plan.

**How either result changes the next decision.** If the common exact subset is
empty/tiny (expected), the only valid route is a frozen-region recount; Codex
should then choose between (i) requesting the minimal author artifact set and
(ii) a prospective amendment for a bounded recount, rather than downloading the
7.6 GiB object. If the subset is adequate, the cheap GEO MEX route becomes viable
for a within-study comparison and the expensive recount can be deferred to the
external (NeMO) side only.

Supporting handoff tasks (existing IDs; do not invent):

- **E2-R** (`tasks/todo.md`, target reader/resource contract): the object's ATAC
  assay is a naive merge (`INFERENCE`), so E2-R must require, before any load, a
  documented assay-inventory check (assay names, `counts` layer type, feature
  count, whether `peaks_by_cluster` exists) and must not assume a comparable
  measured ATAC matrix. Acceptance: a `<=1 MiB` applicable `.rda`/Seurat/
  `ChromatinAssay` fixture passes and refuses unexpected classes.
- **E2-M1** (`tasks/plan.md`): runtime/control feasibility. Keep separate from the
  data question. The earlier "256 MiB / 15 s feasible" assertion is `UNVERIFIED`
  (Q7); require an end-to-end measurement before treating the HEAD contract as
  feasible.
- **Contract update** (`configs/development_object_source_contract.json`, requires
  authority): correct any budget text derived from the "4×" factor to 16×, and add
  the `peaks_by_cluster`-absent and naive-merge findings to the `not_proven`/scope
  notes. Do not edit without owner approval.

## 6. Remaining evidence / approval requests and bounded proposed checks

1. **Minimal artifact request (draft only; do not send).** To the Lattke authors at
   pinned commit `227f51b4…` / GEO `GSE305146`: (a) the F01 output pair
   `F01_seur_w_peaks_by_cluster_quant.rda` and `F01_peaks_by_cluster.bed`; (b) a
   one-page manifest stating, for
   `GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz`, the workspace member
   names, assay names, ATAC feature-space definition, count stage, genome build and
   interval convention; (c) the retained-barcode list per library and the exact
   exclusion rule behind the 37-library/30-donor final cohort. These are the
   minimum artifacts that would convert several `INFERENCE`/`UNVERIFIED` rows into
   `SUPPORTED` without any large download.
2. **NeMO count-stage definition (draft only).** Request the author's QC table or
   count-stage definition behind the release `nCount_ATAC`/`class` columns, and the
   author-defined final barcode list. Needed before external QC replay; do not
   substitute the release column for the QC-stage fragment count.
3. **Bounded proposed checks (PROPOSED, no execution authority yet):**
   - 46-library peak reconciliation (§5).
   - A tiny `.rda`/Seurat/`ChromatinAssay` fixture (already designed in the earlier
     dossier R3) to close the reader-class gate — a proposal until run and reviewed.
   - One HEAD of the candidate payload URL per the frozen contract, only after
     E2-M1 controls are demonstrated. This resolves source identity only, not
     contents, memory or QC.
4. **Do not do:** download either `.rda.gz`; download fragments; treat a 64 KiB
   prefix as assay proof; infer RAM from compressed size; zero-fill unmatched peaks;
   replay NeMO QC from the release column; start cross-attention implementation
   before the data/feature/protocol gates pass.

## 7. Source ledger, search coverage, corrections, iteration progress

### Base and dossier verification (`OBSERVED_NOW`)

- Base commit `8217719713c271349d1e54eda679672b82133a56` verified.
- Earlier-campaign dossier worktree `p22-research-campaig-b057f9`, HEAD `7e37ceb`,
  `docs/GNHF_P22_RESEARCH_DOSSIER.md` SHA-256
  `252a097479de0580f639bcba44dfb6a47a62ba74e08bea75e65a4f4d4baa3495`. It is
  committed (not mid-write) and marks R6–R8 pending; R1–R5 are `RECORDED_PREVIOUSLY`
  here, not re-verified line by line.

### New sources this iteration

| ID | Source | Label | Access |
|---|---|---|---|
| N1 | GitHub tree API `lattkem1/Down_Syndrome_Multiome` @ `227f51b4…` (`truncated:false`) | OBSERVED_NOW | 2026-09-20 |
| N2 | `B01_v041_load_from_cellranger_arc.R` | OBSERVED_NOW | 2026-09-20 |
| N3 | `B02_v040_integrate_samples_RNA_Harmony.R` | OBSERVED_NOW | 2026-09-20 |
| N4 | `B03_v040_integrated_dataset_clustering_tests.R` | OBSERVED_NOW | 2026-09-20 |
| N5 | `B04_v040_charact_clusters.R` | OBSERVED_NOW | 2026-09-20 |
| N6 | `C01_v040_subsetting_reintegration.R` (all cells) | OBSERVED_NOW | 2026-09-20 |
| N7 | `C01_v040_subsetting_reintegration_from_subset.R` (exc-lin) | OBSERVED_NOW | 2026-09-20 |
| N8 | `C03_v041_subcluster_charact_abund_analysis.R` (exc-lin) | OBSERVED_NOW | 2026-09-20 |
| N9 | `F01_v045_seur_call_quant_peaks_by_cluster.R` | OBSERVED_NOW | 2026-09-20 |
| N10 | Signac merging vignette (Signac 1.17.0, compiled 2026-04-01) | OBSERVED_NOW | 2026-09-20 |
| N11 | GEO GSE305146 supplementary listing (46 libraries + 2 objects) | OBSERVED_NOW | 2026-09-20 |
| N12 | Local `GSE305146_*_features.tsv.gz` (3 libraries) | OBSERVED_NOW | 2026-09-20 |
| N13 | `scripts/run_r_fixture.py`, `src/p22/data/atac_features.py` | OBSERVED_NOW | 2026-09-20 |

Reused without re-fetch: earlier dossier S1–S42 (local canonical docs, saved Vuong
XML/NeMO metadata, pinned author tables). Search coverage this iteration: author
source tree + 8 raw scripts, Signac primary docs, GEO listing, local annotation
files, local contract/plan/code. No NeMO re-fetch (earlier S42 transport error
stands); no payload, object, fragment or matrix reads; no author contact.

### Corrections to earlier work

1. 4 GiB ÷ 256 MiB = **16**, not 4. (Earlier dossier R2.)
2. `create_args` is generic, not R-hardcoded; `run_owned` has one attached-run
   deadline, not only per-call timeouts. (Earlier dossier R2.)
3. "256 MiB / 15 s HEAD feasible" downgraded to `UNVERIFIED`; no end-to-end
   measurement exists on this host.
4. C5 quantified: 3 libraries measured, exact intersection 3/0/0/0.

### Iteration progress

- Iteration 1 (this pass): R6 (defensible common ATAC feature route) researched;
  object provenance chain recovered; naive-merge finding; 3-library peak-space
  measurement; arithmetic/challenge corrections; handoff created.
- Next iteration: execute the 46-library reconciliation (§5), then R7 (scientific
  value of the comparison and RNA-only fallback) and R8 (citation/entry-point
  verification across all passes).
- Stop condition: not met. All six research priorities do not yet have a supported
  disposition; R7/R8 remain open. `should_fully_stop=false`.

# P22 deep-research handoff for Codex

Prepared 2026-09-20 (iteration 1; updated iteration 2). Worktree
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
- The Lattke library→specimen mapping and the 37-library/30-specimen (15/15)
  final cohort are public at the pinned author commit, not missing artifacts
  (donor identity beyond specimen ID is `UNKNOWN`; see §3.7).
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
no exact common space); the full 46-library reconciliation is a deferred bounded
check (§5) pending scoped approval.

What iteration 2 adds (all `OBSERVED_NOW` unless noted) — priority 1 is now closed:

7. **The 46→37→30 progression is reproduced exactly from public metadata, with
   two distinct exclusion layers and duplicate-key checks (§3.7).** 46 sequencing
   libraries (92 GEO sample records = 46 ATAC + 46 GEX) reduce to 37 B02-retained
   libraries and 30 final specimens (15 CON + 15 DS). Exclusions: 5 libraries / 4
   specimens flagged GEO `in final_analysis=FALSE` ("low quality/non-cortical"),
   plus 4 libraries / 3 specimens removed by B02 per-library cell QC
   (`fract_removed<=0.5`, `N_cells_filtered>=500`).
8. **Corrections from the reconciliation.** GEO `in final_analysis=TRUE` is 41
   libraries, a superset of the final 37 — it is not the final cohort.
   `tissue_quality` is a preservation label, not the exclusion rule (a `sub`
   specimen, B18D2L, is retained; two `ok` libraries, B15C1H/B15C1L, are dropped).
   "30 donors" should be read as **30 distinct specimen IDs**; distinct-donor
   status beyond specimen identity is `UNKNOWN` (no donor field exists).
9. **New minimal missing artifact named.** The per-library reason for the 3
   B02-QC drops needs `B02filter_stats.csv`, absent from the complete pinned tree;
   the retained-barcode list per library remains author-local.

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
| Q11 | GSE305146 goes 46 libraries → 37 retained → 30 final specimens (15 CON/15 DS) | SOFT + A_input + B02 tables (§3.7) | None at metadata level | SUPPORTED | The paired design universe is 30 specimens / 37 libraries; donors = specimens only by ID |
| Q12 | GEO `in final_analysis=TRUE` equals the final cohort | SOFT flag = 41 libraries vs B02 = 37 (§3.7) | None | REJECTED | Do not use the GEO flag as the final cohort; use the B02 table |
| Q13 | A_input `tissue_quality` drives exclusion | B18D2L (`sub`) retained; B15C1H/L (`ok`) dropped (§3.7) | None | REJECTED | Exclusion rule is B02 cell QC, not the preservation label |
| Q14 | The final cohort is 30 donors | Tables give 30 unique specimen IDs, no donor field (§3.7) | Donor identity beyond specimen ID | INFERENCE (specimen ≠ proven donor) | Write "30 specimens"; do not overstate donor independence |
| Q15 | The 3 B02-QC-dropped specimens' per-library cause is public | `B02filter_stats.csv` absent from pinned tree (§3.7) | Author-local output | UNKNOWN (minimal artifact) | Request the small stats table if exact attribution is needed |

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

### 3.7 GSE305146 library↔specimen reconciliation (`OBSERVED_NOW`)

Sources (all public; no payload read):
`data/multiome/GSE305146_family.soft.gz` SHA-256
`8299f15e35f6eda820ac9c9995be94fce648299b12e0ec12e4b7e68d3ab3f087`
(92 `^SAMPLE` records, one per library-modality); pinned author table
`A_input/group_tab_tissue.csv` at commit `227f51b4…` SHA-256
`9aa0a1a8be4863841a08376a9e4f738fcff8135f2055eb859b3a1db7269ee2d1` (46 rows);
pinned `B_basic_analysis/B02_gr_tab_filtered_non_cx_excl.csv` SHA-256
`7f2113cf235795ab1f06a9999069a25b1c713d42f3c1dc913df3bcd8f59c412c` (37 rows,
byte-identical to the local copy). Raw base
`raw.githubusercontent.com/lattkem1/Down_Syndrome_Multiome/227f51b4e63c6a7d9c73be44f06ab21ac11e45ba/`.

Exact counts:

| Level | Count | Source |
|---|---:|---|
| Deposited modalities | 2 (ATAC + GEX) per library | SOFT titles (46 `_atac`, 46 `_gex`) |
| GEO sample records | 92 | SOFT `^SAMPLE` |
| Sequencing libraries | 46 | A_input rows; SOFT `Library name` |
| Sequenced specimens | 37 (18 CON + 19 DS) | A_input unique `sample` |
| GEO `in final_analysis=TRUE` libraries | 41 (21 DS + 20 CON) | SOFT flag |
| B02-retained libraries | 37 (17 CON + 20 DS) | B02 CSV rows |
| Final specimens | 30 (15 CON + 15 DS) | B02 unique `sample` |
| Final cells (claimed) | 248,998 | SOFT `!Series_overall_design` |

Reproducible reconciliation (46 libraries → 37 retained libraries → 30 specimens):

- Dropped libraries (9): `B10D1N, B11C1A, B11C1C, B12C3B, B12D4H, B14D1H,
  B15C1H, B15C1L, B17D2F`.
- Dropped specimens (7): `B10D1, B11C1, B12C3, B12D4, B14D1, B15C1, B17D2`.
- Two distinct exclusion layers:
  1. **GEO flag** `in final_analysis=FALSE`: 5 libraries / 4 specimens
     (`B12D4, B14D1, B15C1, B17D2`). SOFT titles append
     "low quality/non-cortical, NOT IN FINAL ANALYSIS".
  2. **B02 per-library cell QC**: the remaining 4 libraries / 3 specimens
     (`B10D1N, B11C1A, B11C1C, B12C3B`) are GEO-TRUE but absent from B02. Exact
     rule in `B02_v040_integrate_samples_RNA_Harmony.R:46-68`: cells must satisfy
     `nCount_ATAC` 100–25000, `nCount_RNA` 500–30000, `percent.mt<2`,
     `nucleosome_signal<2`, `TSS.enrichment>1.1`; a library is retained iff
     `fract_removed<=0.5` AND `N_cells_filtered>=500` AND
     `library %in% gr_tab$library`.
- Duplicate-key checks: no `sample` maps to >1 `sample_name` and no `sample_name`
  to >1 `sample`; all 46 A_input `library` keys and all 37 B02 keys are unique. 9
  specimens contribute 2 libraries each (`B11C1, B11D1, B11D2, B13D3, B15C1,
  B15D1, B17C2, B18C1, B18D1`), so libraries ≠ specimens. One A_input key carries
  a trailing space (`B18C1P `) and must be stripped before joining.
- Cross-table consistency: GEO library set == A_input library set (46=46); all 46
  GEO ATAC records agree with A_input on `sample`/`sample_name`/`group`/`dev_PCW`/
  `sex` (0 mismatches).

Reproduce (metadata only; no expression values, no download):

```bash
# run from the original checkout root; metadata lives in P22/data/multiome
python3 - <<'PY'
import gzip, csv
base = '/Users/anuragdani/Github/niw-eb1a/P22/data/multiome'
soft = {}
cur = None
def ch(s, p):
    for x in s.get('c', []):
        if x.lower().startswith(p.lower() + ':'):
            return x.split(':', 1)[1].strip()
def desc(s, p):
    for x in s.get('d', []):
        if x.lower().startswith(p.lower() + ':'):
            return x.split(':', 1)[1].strip()
def flush(s):
    if not s:
        return
    lib = desc(s, 'Library name')
    if lib and lib.endswith('_atac'):
        soft[lib[:-5]] = (ch(s, 'sample id'), ch(s, 'name'), ch(s, 'group'),
                          ch(s, 'in final_analysis'))
with gzip.open(base + '/GSE305146_family.soft.gz', 'rt') as fh:
    for line in fh:
        line = line.rstrip('\n')
        if line.startswith('^SAMPLE'):
            flush(cur); cur = {'c': [], 'd': []}
        elif cur is not None and line.startswith('!'):
            k, _, v = line[1:].partition(' = ')
            if k == 'Sample_characteristics_ch1': cur['c'].append(v)
            elif k == 'Sample_description': cur['d'].append(v)
        elif line.startswith('!Series') or line.startswith('^SERIES'):
            flush(cur); cur = None
flush(cur)
A = list(csv.DictReader(open(base + '/Lattke_B02_gr_tab_filtered_non_cx_excl_227f51b.csv')))
B = {r['library'].strip() for r in A}
print('GEO libs', len(soft), 'B02 libs', len(B))
print('dropped', sorted(set(soft) - B))
print('final specimens', len({r['sample'] for r in A}),
      'groups', sorted({r['group'] for r in A}))
print('final group counts',
      {g: len({r['sample'] for r in A if r['group'] == g}) for g in ('CON', 'DS')})
PY
```

Corrections and limits:

- `tissue_quality` is **not** the exclusion rule (Q13): A_input `tissue_quality`
  is `sub` for `B10D1N, B12D4H, B14D1H, B17D2F, B18D2L`, but `B18D2L` is retained
  in B02, while `B15C1H/B15C1L` are `ok` and excluded.
- The paper's stated split ("3 samples with a large fraction of non-cortical cells
  and stringent quality controls") is not exactly reproducible: GEO flags **4**
  specimens as "low quality/non-cortical" and B02 cell QC removes **3**; the total
  **7** is reproduced, the 3/4 split is not.
- The paper's "20 CON and 19 DS foetal brain samples acquired" versus 18 CON + 19
  DS sequenced specimens (37) is consistent only if both "poorly preserved"
  samples were CON; the final 15 + 15 is exactly reproduced.
- "30 donors" is an overstatement: the tables give 30 distinct specimen IDs
  (`sample` = `sample_name` one-to-one), and no donor field exists. Use "30
  samples/specimens" and keep donor-level independence `UNKNOWN` (Q14).
- Per-library attribution of the 3 B02-QC drops (`fract_removed` vs `<500` cells)
  needs `B02filter_stats.csv`, which is absent from the complete pinned tree
  (`truncated:false`) — the named minimal missing artifact (Q15).

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
| 4 | **GEO per-library MEX ATAC matrices** | Per-library measured counts on library-specific peaks | No common exact feature space (Q1); union leaves unmeasured coverage | Full 46-library intersection/overlap reconciliation (deferred check, §5) | Not a common measured matrix; cannot be zero-filled |
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
- **Could the 30 final specimens be 30 donors?** Only specimen IDs (`sample` =
  `sample_name`) are public; there is no donor field. Distinct IDs strongly suggest
  distinct pregnancies but do not prove it. Overturning evidence: a specimen→donor
  mapping in the HDBR/author record showing distinct donors per ID. Until then,
  report "30 specimens".
- **Could the 46→37→30 exclusions be attributed exactly?** The rule is public
  (`B02…R:46-68`) but the per-library `fract_removed`/cell counts are not, so which
  of the two thresholds removed each of the 3 B02-QC specimens is `UNKNOWN`.
  Overturning evidence: `B02filter_stats.csv`.

## 5. Prioritized implementation handoff and the single next action

Priority 1 is closed (§3.7). The single next action moves to priority 3, the
external cohort, because the frozen design's only external check depends on it and
it is resolvable from primary public sources without payload access.

**Single highest-value next action (do this first): resolve the external-cohort
specimen-independence and ATAC count-stage questions from primary Vuong/NeMO
author sources.**

- Input: the saved Vuong manuscript XML
  (`data/multiome/Vuong_PMC13225313_efetch_20260908.xml`), the saved NeMO metadata
  (`data/multiome/VuongWeber_DSdevctx_metadata.tar`), the public Vuong analysis
  code repository if one exists, and NeMO `col-umstjg0` release documentation.
  Web/HTML/author code only; no restricted records, no payload.
- Method: (a) locate the author's final retained-barcode list or exclusion rule
  that yields 113,801 non-`Unk` nuclei; (b) identify which processing stage the
  release `nCount_ATAC` column measures; (c) establish whether the 18 UCLA / 8 NIH
  donors are independent of the Lattke/HDBR specimens using a documented provider
  or specimen mapping, not donor-name distinctness; (d) separate RNA `Unk` from
  the WNN `Unk` mask.
- Expected output: a small table mapping each claim (`117,532` rows, `3,731`
  RNA-`Unk`, `113,801` reported, `nCount_ATAC` stage, provider/specimen) to a
  primary source line, plus one verdict per claim: `AUTHOR_RULE_FOUND`,
  `STAGE_NAMED`, `INDEPENDENCE_LEVEL`.
- Acceptance check: the partition and stage claims cite exact source lines; the
  independence claim cites a provider/specimen artifact, not a name comparison.
- Dependencies: web/author-code access only; no installs or containers.
- Authority: public web search, primary HTML/XML, author code and small mapping
  tables are allowed; no NeMO/restricted payload.
- Stop condition: if no author rule or final-barcode artifact exists publicly,
  record `EXTERNAL_QC_RULE_UNRESOLVED` with the exact artifact requested, and keep
  the external cohort `covariate-limited`.

**How either result changes the next decision.** If a documented author rule /
barcode artifact and a specimen-mapping source are found, external evaluation can
be specified on the frozen design with a named QC stage and an honest independence
statement. If not, external scoring must be reported as a covariate-limited
secondary analysis, which lowers the value of the paired path and strengthens the
case for pausing it in favor of a separately justified RNA-only follow-up.

Deferred bounded check (priority 2, unchanged, needs scoped approval because it
touches dataset-adjacent files): full metadata-only peak-space reconciliation
across all 46 `GSE305146_<library>_features.tsv.gz` files.

- Input: the 46 public feature/annotation files (~1–3 MB each; no
  `matrix.mtx.gz`, no barcodes, no fragments). Three are local; the other 43 are
  small public annotation files.
- Method/output/acceptance: as in §3.4, extended to 46 libraries; verdict
  `COMMON_EXACT_SUBSET=EMPTY|SMALL|ADEQUATE`; must reproduce 46,672 / 20,708 /
  22,676 and 3/0/0/0.
- Authority note: these are dataset supplementary files, not merely a published
  mapping table, so treat the 43-file fetch as a scoped approval item rather than
  an assumed right.

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
   interval convention; (c) the retained-barcode list per library; (d)
   `B02filter_stats.csv` (per-library `N_cells_unfiltered`, `N_cells_filtered`,
   `fract_removed`, `cells_retained`) to attribute the 3 B02-QC drops exactly. The
   exclusion rule behind the 37-library/30-specimen final cohort is already public
   (`B02_v040…R:46-68`, §3.7); these are the minimum artifacts that would convert
   the remaining `INFERENCE`/`UNVERIFIED` rows into `SUPPORTED` without any large
   download.
2. **NeMO count-stage definition (draft only).** Request the author's QC table or
   count-stage definition behind the release `nCount_ATAC`/`class` columns, and the
   author-defined final barcode list. Needed before external QC replay; do not
   substitute the release column for the QC-stage fragment count.
3. **Bounded proposed checks (PROPOSED, no execution authority yet):**
   - 46-library peak reconciliation (§5); needs scoped approval because it fetches
     43 dataset-adjacent supplementary files.
   - External-cohort provenance pass (§5, the single next action); public
     web/author-code only.
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
- Earlier-campaign dossier worktree `p22-research-campaig-b057f9` moved between
  reads: iteration 1 saw HEAD `7e37ceb`, SHA-256
  `252a097479de0580f639bcba44dfb6a47a62ba74e08bea75e65a4f4d4baa3495` (R1–R5 body,
  R6–R8 pending); iteration 2 sees HEAD `b40458f`, SHA-256
  `0d337b6d6c494b0a8f3be1b5b31b80430a835c35b39c0f4cf40d7bb1a12ec2f9` (R1–R6 body;
  the progress table marks R7 `RESEARCHED` but **no R7 body is present** and the
  file ends at the R6 outcome). The campaign worktree is still being written; treat
  its R7 row as a claim, not a completed pass, and its R1–R6 as
  `RECORDED_PREVIOUSLY` here, not re-verified line by line.
- Required hashes re-checked iteration 2: contract
  `9a13d8be…` and `PAIRED_MULTIOME_REMAINING_EVIDENCE` `66b1d815…` both unchanged.

### New sources (iteration 1: N1–N13; iteration 2: N14–N18)

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
| N14 | `data/multiome/GSE305146_family.soft.gz` (SHA `8299f15e…`; 92 `^SAMPLE`) | OBSERVED_NOW | 2026-09-20 |
| N15 | Pinned `A_input/group_tab_tissue.csv` @ `227f51b4…` (SHA `9aa0a1a8…`; 46 rows) | OBSERVED_NOW | 2026-09-20 |
| N16 | Pinned `B_basic_analysis/B02_gr_tab_filtered_non_cx_excl.csv` (SHA `7f2113cf…`; 37 rows, matches local) | OBSERVED_NOW | 2026-09-20 |
| N17 | `B02_v040_integrate_samples_RNA_Harmony.R:34-78` (filter rule) | OBSERVED_NOW | 2026-09-20 |
| N18 | Pinned tree API re-read (confirms no `filter_stats`/`gr_tab_filtered.csv`) | OBSERVED_NOW | 2026-09-20 |

Reused without re-fetch: earlier dossier S1–S42 (local canonical docs, saved Vuong
XML/NeMO metadata, pinned author tables). Search coverage iteration 1: author
source tree + 8 raw scripts, Signac primary docs, GEO listing, local annotation
files, local contract/plan/code. Search coverage iteration 2: GEO SOFT family
record, pinned `A_input` and `B02` tables, pinned B02 script and tree, local
contract/plan/code, earlier-campaign dossier (new HEAD). No NeMO re-fetch (earlier
S42 transport error stands); no payload, object, fragment or matrix reads; no
author contact; no payload GET (only author-repo CSVs/scripts and the local SOFT
file).

### Corrections to earlier work

1. 4 GiB ÷ 256 MiB = **16**, not 4. (Earlier dossier R2.)
2. `create_args` is generic, not R-hardcoded; `run_owned` has one attached-run
   deadline, not only per-call timeouts. (Earlier dossier R2.)
3. "256 MiB / 15 s HEAD feasible" downgraded to `UNVERIFIED`; no end-to-end
   measurement exists on this host.
4. C5 quantified: 3 libraries measured, exact intersection 3/0/0/0.
5. Earlier carried-forward phrasing "37-library/30-donor cohort" corrected to
   "30 specimens"; no donor field exists (iteration 2, §3.7).
6. "GEO `in final_analysis` is the final cohort" rejected: it is 41 libraries vs
   the B02 final 37 (iteration 2, §3.7).
7. "`tissue_quality` drives exclusion" rejected: a `sub` specimen is retained and
   `ok` libraries are dropped (iteration 2, §3.7).
8. The earlier-campaign dossier progressed mid-run (HEAD `7e37ceb` → `b40458f`);
   its R7 is table-marked `RESEARCHED` but has no body. Do not treat it as done.

### Iteration progress

- Iteration 1: R6 (defensible common ATAC feature route) researched; object
  provenance chain recovered; naive-merge finding; 3-library peak-space
  measurement; arithmetic/challenge corrections; handoff created.
- Iteration 2 (this pass): priority 1 closed — full library↔specimen reconciliation
  from GEO SOFT + pinned author tables, two exclusion layers, duplicate-key checks,
  three claim corrections, and the minimal missing artifact (`B02filter_stats.csv`)
  named. Next action moved to priority 3 (external-cohort provenance).
- Next iteration: priority 3 external-cohort provenance/independence (§5), then
  priority 5 (scientific value and RNA-only fallback, independently of the
  campaign's R7) and priority 4 (reader/resource path re-verification).
- Stop condition: not met. Priorities 2 and 5–6 lack a supported disposition in
  this handoff; priority 3 is the active next action. `should_fully_stop=false`.

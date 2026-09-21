# P22 deep-research handoff for Codex

Prepared 2026-09-20 (iteration 1; updated through iteration 6). Worktree
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
common-region recount; whether that recount is affordable is undecided. The paired
comparison is scientifically `CONDITIONAL` (§3.9): worth running and refutable, but
only under a prospective amendment and after the estimand fix (Q22). The GEO
submission itself describes the two objects only as "Seurat objects with labelled
cell clusters and sample metadata" (§3.11), so neither reachable object is expected
to carry a common measured ATAC space. The single next action for Codex is the
approval-gated 46-library peak reconciliation (§5); if it is not approved, request
the F01 artifact pair (§6).**

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

Earlier iterations (full detail in §3 and §7): recovered the object-provenance
chain (both GEO objects map to author stages B04/C03; the selected object is
pre-`F01`, so `peaks_by_cluster` is absent); showed the deposited ATAC assay is a
naive per-library peak merge; measured 3 of 46 GEO peak spaces (exact intersections
3/0/0/0); corrected the 4 GiB-vs-256 MiB factor to 16×; reproduced the 46→37→30
progression; resolved the external cohort to 26 donors/13 libraries (113,801 = RNA
non-`Unk`; release `nCount_ATAC` ≠ QC stage; GW ≠ PCW); found the frozen estimand
omits the primary-contrast arms (`NAMED_BASELINES`, Q22) and resolved priority 5 to
`CONDITIONAL`; and characterized the local CELLxGENE H5AD as the final B02 cohort,
RNA-only, with a barcode→library→donor join.

What iteration 6 adds (all `OBSERVED_NOW` unless noted) — priority 4 is closed to a
disposition and an authoritative provider statement is recovered:

21. **The GEO submission carries an explicit provider inventory of the two `.rda`
    objects (Q32, §3.11).** The per-sample `!Sample_data_processing` says the `.rda`
    files contain "the Seurat objects with labelled cell clusters and sample
    metadata (for complete dataset and filtered excitatory lineage cells)". This
    corroborates the object↔pipeline-stage mapping with a provider statement rather
    than filename inference, and lists no cluster-peak assay.
22. **A reader-version conflict is now recorded (Q33, §3.11).** The GEO text names
    R 4.3.3 / Seurat v5.1.0 / Signac v1.13.0; the pinned package snapshot names
    Seurat 5.3.0 / Signac 1.14.0. The exact serialization version of the deposited
    object is `UNKNOWN` — a compatibility caveat for any reader.
23. **Priority 4 is `RESOURCE_UNRESOLVED`, not "impossible" (Q34–Q36, §3.12).**
    The minimal R reader genuinely needs the full Seurat/Signac/GenomicRanges class
    stack (S4 class attributes name the defining package; R resolves it on load),
    `pyreadr` cannot parse S4/lists, and the pure-Python `rdata` package *can* parse
    S4 to `SimpleNamespace` but has no Matrix constructor, is untested on a Seurat
    object and is not installed. The repo's existing E2-R fixture is a base-class
    `.rds` written with `saveRDS`, not the contract's required `save()` workspace
    with Seurat/`ChromatinAssay`; an exact minimal fixture spec is given.
24. **Even a successful read cannot close the paired ATAC gate (Q37, §3.12).**
    The deposited assay is a naive merge (Q3) and the selected object is pre-`F01`
    (Q2), both re-verified from the pinned tree this pass. The reader is a bounded
    E2-R verification task, not the critical path; the critical path is the
    frozen-region recount (priority 2 rank 1) or the F01 artifact request.

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
| Q9 | NeMO external `nCount_ATAC` is the QC-stage fragment count | 1,798 rows <=100 (§3.8) | Count stage undefined; release not final-QC-filtered | REJECTED (not the QC column) | Never replay QC from the release column; re-filter explicitly |
| Q10 | External cohort is independent | provider-level only | No genetic crosswalk | UNVERIFIED (no_overlap_evidence) | Report as covariate-limited external candidate |
| Q16 | Reported 113,801 is the RNA non-`Unk` count | exact match (§3.8) | No author statement names `Unk` | SUPPORTED (count identity), rule UNKNOWN | Use non-`Unk` as the candidate mask, labelled annotation-derived |
| Q17 | The stated QC replay reproduces 113,801 | replay = 113,242 (§3.8) | 559-cell gap | REJECTED | Do not claim the 113,801 set is the QC-pass set |
| Q18 | `Unk` cells are the QC-dropped cells | 93.1% of `Unk` pass QC; higher counts (§3.8) | None | REJECTED | `Unk` is a cell-type annotation, not a QC artifact |
| Q19 | External cohort effective replication | 26 donors / 13 libraries (§3.8) | Donor identity beyond ID | SUPPORTED | Power/aggregation is donor-level (26), not cell-level |
| Q20 | Vuong `gw` and Lattke `dev_PCW` are the same scale | manuscript: GW 13–23 obstetric; Lattke PCW 10–20 (§3.8) | ACOG/LMP vs conception | REJECTED (≈2-week offset) | Convert GW→PCW before any age covariate join |
| Q21 | A public Vuong author code repo / barcode list exists | none found (N19–N22) | Search scope | UNKNOWN | Request the author QC rule/barcode list; keep external QC `EXTERNAL_QC_RULE_UNRESOLVED` |
| Q11 | GSE305146 goes 46 libraries → 37 retained → 30 final specimens (15 CON/15 DS) | SOFT + A_input + B02 tables (§3.7) | None at metadata level | SUPPORTED | The paired design universe is 30 specimens / 37 libraries; donors = specimens only by ID |
| Q12 | GEO `in final_analysis=TRUE` equals the final cohort | SOFT flag = 41 libraries vs B02 = 37 (§3.7) | None | REJECTED | Do not use the GEO flag as the final cohort; use the B02 table |
| Q13 | A_input `tissue_quality` drives exclusion | B18D2L (`sub`) retained; B15C1H/L (`ok`) dropped (§3.7) | None | REJECTED | Exclusion rule is B02 cell QC, not the preservation label |
| Q14 | The final cohort is 30 donors | Tables give 30 unique specimen IDs, no donor field (§3.7) | Donor identity beyond specimen ID | INFERENCE (specimen ≠ proven donor) | Write "30 specimens"; do not overstate donor independence |
| Q15 | The 3 B02-QC-dropped specimens' per-library cause is public | `B02filter_stats.csv` absent from pinned tree (§3.7) | Author-local output | UNKNOWN (minimal artifact) | Request the small stats table if exact attribution is needed |
| Q22 | The frozen estimand names the primary-contrast arms (`cross_attention`, `token_concat`) | `estimand.py:20-29` omits both; runner implements both (§3.9) | Manifest/G6-report omission, not a runner blocker | REJECTED (gap) | Amend `NAMED_BASELINES`/M5 before M6c freezes the report |
| Q23 | The paired comparison adds an increment not already answered by the RNA study | Different estimand (cross-attention−concat vs RNA donor association); RNA result INCONCLUSIVE (§3.9) | Not empirically settled | CONDITIONAL | Proceed only under a prospective amendment; negative result is valid |
| Q24 | Concat vs cross-attention outcome is determined by donor count alone | S52: alignment and sample complexity both matter; S51: cross-attention helps with few pairs | Preprint + vision-language domain | UNVERIFIED (both signs open) | Report both signs; do not pre-commit to cross-attention winning |
| Q25 | A simpler control could explain an apparent cross-attention gain | All-donor peak selection, region×provider, age scale, composition (§3.9) | None at design level | SUPPORTED | Each control must be reported before any advantage claim |
| Q26 | Cells, not donors, are the effective replication unit | S55/S56; frozen `split_unit="donor"` (`estimand.py:59`) | None | SUPPORTED | Aggregate to donor; report donor-level intervals only |
| Q27 | DECAT (S60) can diagnose the cross-attention model directly | S60: "cannot be directly applied to early-fusion architectures where modalities attend to each other" | Framework limitation | REJECTED | Use cross-cohort stability as a principle, not DECAT scoring, for this model |
| Q28 | The local CELLxGENE H5AD is the final B02 cohort | 37 `library`/30 `sample` set-equal to pinned B02 (§3.10) | None | SUPPORTED | Third public confirmation; retained-barcode/donor join is local |
| Q29 | The local H5AD supplies ATAC measured counts | var = 35,477 genes only; no Peaks/ATAC layer (§3.10) | None | REJECTED | ATAC still needs the GEO MEX peak matrices or a fragment recount |
| Q30 | H5AD `raw/X` is the exact cellranger-arc raw matrix | integer/raw-scale but row sums ≠ `nCount_RNA` (median −4) (§3.10) | Not proven | UNVERIFIED | Treat as raw-scale, not as the authoritative raw matrix |
| Q31 | The selected exc-lin object's cell membership is enumerable without the 7.6 GiB object | `cells_in_excitatory_lineage_subset` = 215,680, all 30 donors, PCW10–20 (§3.10) | Exact equivalence to C03 is UNKNOWN | INFERENCE | Candidate barcode set; verify if the object is ever inspected |
| Q32 | The two `.rda` objects are Seurat objects of labelled clusters + sample metadata for complete/exc-lin | GEO `!Sample_data_processing` line 321 (§3.11) | "Seurat object" content not enumerated further; `peaks_by_cluster` unmentioned | SUPPORTED (provider inventory) | Treat as B04/C03 labelled outputs; do not expect a cluster-peak assay |
| Q33 | The deposited object's serialization versions are Seurat 5.3.0 / Signac 1.14.0 | GEO text: Seurat v5.1.0 / Signac v1.13.0; pinned CSV: 5.3.0 / 1.14.0 (§3.11) | Which version wrote the object | REJECTED (conflict) | Reader must tolerate both; exact version UNKNOWN |
| Q34 | The minimal R reader needs only base R + Matrix | S4 class attr names defining package; R resolves it on load (R Internals §1.12.1; `?load`) | Exact failure mode without packages untested | REJECTED | Budget the full Seurat/Signac/GRanges class stack |
| Q35 | `pyreadr` can read the object's S4/Seurat classes | librdata/JOSS: R lists and S4 unsupported (§3.12) | None | REJECTED | Do not plan on pyreadr/rpy2 |
| Q36 | The repo's E2-R fixture meets the contract's required `.rda`/Seurat proof | `inspect_development_object.R` uses `saveRDS` of a base `list` (§3.12); contract `reader_proof` | None | REJECTED (gap) | Upgrade the fixture to a `save()` workspace with Seurat/ChromatinAssay |
| Q37 | A successful reader closes the paired ATAC gate | Q2 + Q3 re-verified from pinned `B01`/`F01` this pass (§3.12) | Object uninspected | REJECTED | Reader is a bounded E2-R check; recount/artifact is the critical path |

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
# run from the original checkout root; metadata lives in P22/data/multiome.
# SOFT parser: collect per-^SAMPLE the _atac "Library name" and sample id/name/
# group/in final_analysis; build `soft[library] = (...)` for the 46 ATAC samples.
python3 - <<'PY'
import csv
base = '/Users/anuragdani/Github/niw-eb1a/P22/data/multiome'
A = list(csv.DictReader(open(base + '/Lattke_B02_gr_tab_filtered_non_cx_excl_227f51b.csv')))
B = {r['library'].strip() for r in A}
print('B02 libs', len(B), 'final specimens', len({r['sample'] for r in A}))
print('final group counts',
      {g: len({r['sample'] for r in A if r['group'] == g}) for g in ('CON', 'DS')})
assert len(B) == 37 and {r['group'] for r in A} == {'CON', 'DS'}
PY
# The 46-library SOFT set and the 9 dropped libraries are asserted in §3.7's table.
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

### 3.8 External cohort: counts, QC stage, structure, independence (`OBSERVED_NOW`)

Sources: local saved manuscript XML
`data/multiome/Vuong_PMC13225313_efetch_20260908.xml` (SHA-256 `7e58d9f0…`, per
§7); local saved release metadata
`data/multiome/VuongWeber_DSdevctx_metadata.tar` SHA-256
`72cf7284663aeaee76ed3bab16ce0b414faf82847a883e946e7c2afab21b1526`, member
`VuongWeber_2025_DSdevctx_metadata_20260128.csv.gz` (117,532 rows × 22 cols); NeMO
collection pages (N19). No payload/count/fragment download.

**Count partition and QC replay.** The metadata has 117,532 rows; `class == "Unk"`
is exactly `cluster.ids == "Unk"` = 3,731; non-`Unk` = **113,801**, the paper's
reported retained-nuclei figure. The manuscript states the QC filters
(`nCount_RNA`>200 and <donor-mean+3 s.d.; ATAC fragment `nCount_ATAC`>100;
`percent.mt`<5 tissue) but never states an `Unk` exclusion ("Unk" occurs 0 times in
the XML). Replaying those thresholds on the release columns:

| Filter | Rows failing | Rows passing |
|---|---:|---:|
| `nCount_RNA`>200 | 0 | 117,532 |
| `nCount_RNA`<donor+3 s.d. | 2,530 | 115,002 |
| `nCount_ATAC`>100 | 1,798 | 115,734 |
| `percent.mt`<5 | 7 | 117,525 |
| All four | 4,290 | **113,242** |

So the stated-QC replay gives 113,242, not 113,801 (559 gap), and the release
retains 4,290 cells that fail at least one stated threshold. This is decisive:
the release `nCount_ATAC` is **not** the QC-stage fragment count (or the release
is pre-QC), and the release metadata is a **superset** of the paper's final set.
Q9 is therefore `REJECTED`, not merely `UNVERIFIED`. The exact `Unk` partition
remains the only exact match, but without an author statement it is a candidate
annotation-derived mask, not a verified author exclusion rule
(`ANNOTATION_COUNT_MATCH_QC_UNVERIFIED`).

**`Unk` is an annotation class, not a QC artifact.** 3,474/3,731 `Unk` cells
(93.1%) pass all four stated thresholds. Median `nCount_ATAC` is 12,411 (`Unk`)
vs 6,957 (non-`Unk`); median `nCount_RNA` 5,216 vs 3,309; median `nFeature_ATAC`
5,698 vs 3,311. QC-failing cells are distributed across both classes (4,033
non-`Unk`, 257 `Unk`). Strongest alternative explanation: the authors applied an
*additional* unpublished QC stage that happens to retain exactly these cells —
overturning evidence would be an author rule/barcode list; the count coincidence
alone does not prove it.

**Cohort structure.** 26 donors (13 Ctrl + 13 Ts21), `hsa21_status` exactly
Disomic/Trisomic = Ctrl/Ts21 (so it adds no independent karyotype information);
13 sequencing libraries (`GEM1`–`GEM7`, `S1`–`S6`); 38 donor-library pairs (1–2
libraries per donor; 1–4 donors per library, i.e. multiplexed). Effective
replication is **26 donors**. Donors: 18 UCLA (`D96`–`D420`, 8 Ctrl/10 Ts21), 8
NIH (`NIH908`–`NIH1883`, 5 Ctrl/3 Ts21). `region` is confounded with provider —
all 18 UCLA donors are `Cortex`, the 8 NIH donors span `BA9`, `BA6`, `BA9/46`,
`Occipital`, `Parietal/occipital`, `Cerebrum`. RNA `Unk` (3,731) and WNN
`cluster.ids.wnn == "Unk"` (728; 663 overlap, 65 do not) are not interchangeable;
`class.wnn` has no `Unk` category (4 classes only). Smallest donor retains 281
cells / 273 non-`Unk` (`D98`).

**Age scale.** Manuscript: "gestational weeks (GW) 13 to 23"; for UCLA tissue
"gestational age was estimated following the guidelines of the American College
of Obstetricians & Gynecologists … age based on the date of last menstrual period
was revised using ultrasonographic dating" — i.e. obstetric gestational age, not
post-conception. Lattke's `dev_PCW` is 10–20 post-conception weeks. PCW ≈ GW−2;
the two ranges overlap after conversion (Vuong ≈ PCW 11–21), but raw GW and PCW
must not be joined directly.

**Independence.** Provider-level separation stands: Vuong tissue from UCLA cores
and NIH NeuroBioBank; Lattke fresh-frozen multiome from HDBR (project 200585).
No genetic crosswalk or author-certified specimen mapping was found. Supported
degree of independence is `no_overlap_evidence` (documented distinct providers +
distinct donor IDs), not genetically verified non-overlap.

Reproduce (metadata only; no expression/ATAC matrices):

```bash
cd /Users/anuragdani/Github/niw-eb1a/P22 && .venv-p22/bin/python - <<'PY'
import tarfile, hashlib, pandas as pd
p='data/multiome/VuongWeber_DSdevctx_metadata.tar'
m=('VuongWeber_2025_DSdevctx_metadata_20260128/'
   'VuongWeber_2025_DSdevctx_metadata_20260128.csv.gz')
with tarfile.open(p) as a:
    df=pd.read_csv(a.extractfile(m), compression='gzip')
unk=df['class'].eq('Unk')
hi=df.groupby('donor')['nCount_RNA'].transform(lambda s: s.mean()+3*s.std())
passall=(df['nCount_RNA']>200)&(df['nCount_RNA']<hi)&(df['nCount_ATAC']>100)&(df['percent.mt']<5)
assert (len(df), int(unk.sum()), int((~unk).sum()), int(passall.sum())) == (117532,3731,113801,113242)
assert round((passall&unk).sum()/unk.sum(),4)==0.9311
assert df.drop_duplicates('donor').condition.value_counts().to_dict()=={'Ctrl':13,'Ts21':13}
assert df['donor'].nunique()==26 and df['sample'].nunique()==13 and df['donor_sample'].nunique()==38
assert hashlib.sha256('\n'.join(sorted(df.loc[~unk,'Unnamed: 0'])).encode()).hexdigest() \
       =='0de060f67ab7d355e90766ab81168929260b3ce43d663b27d53f82c47f5ff9d6'
print('external cohort counts/QC/structure checks passed')
PY
```

### 3.9 Scientific value of the paired comparison (priority 5) (`OBSERVED_NOW`)

Frozen design (local, re-verified this pass): primary contrast = `cross_attention`
minus matched token-concat **external donor balanced accuracy**
(`tasks/todo.md:855`; `src/p22/eval/multiome_protocol.py:59-65` `paired_comparison`);
5 repeated 5-fold donor splits, 256-cell primary cap, threshold 0.5, 1,000 paired
donor resamples seed 22, and count-derived margin `practical_margin(15,15)=0.07`,
`(13,13)=0.08` (`src/p22/eval/estimand.py:32-45`; `tasks/todo.md:850-857`). The
margin is a donor-resolution floor (1/(2·15)≈0.033), not a power guarantee.

Local implementation state (`OBSERVED_NOW`):

- `NEURAL_FAMILIES = (rna_only, atac_only, rna_atac_concat, gated_fusion,
  token_concat, cross_attention)` (`multiome_runner.py:112-119`); `run_paired_fold`
  trains all six on donor-isolated folds (`:152-168`).
- `multiome_final.py:190` computes `paired_comparison(tables["cross_attention"],
  tables["token_concat"])`; `multiome_final._synthetic_only` refuses real
  orchestration (`:33-38`).
- **Gap (Q22):** `estimand.NAMED_BASELINES` (`estimand.py:20-29`) omits
  `cross_attention` and `token_concat`, and `named_baselines.BASELINE_ORDER`
  (`named_baselines.py:21`) drives `baseline_table` (`:226`) and
  `FrozenEstimand.baselines` (`estimand.py:66`). So the frozen estimand manifest
  and the G6 baseline table cannot name the primary-contrast arms, even though M5
  requires freezing "the complete baseline list". The runner is unaffected; the
  contract is. Fix is a small `estimand.py` tuple edit before M6c.

Incremental question per arm, and the simpler control that could explain an
apparent gain (each claim checked against the primary source named):

| Arm | Incremental question it answers | Simpler control that could explain an apparent gain | Refuting result |
|---|---|---|---|
| RNA-only (`pseudobulk_rna_logistic`, `rna_only`) | Per-modality donor signal floor | None — it is the floor | Already INCONCLUSIVE in the completed RNA study; a paired win over this is not novel |
| ATAC-only (`atac_only`) | Whether accessibility alone predicts | Peak selection on all donors leaks labels; region×provider | ATAC-only matching the fusion removes the fusion's claimed increment |
| Concatenation (`rna_atac_concat`, `token_concat`) | Joint signal under equal-weight linear fusion | Feature alignment (S52): if RNA/ATAC are pre-aligned, concat's lower sample complexity dominates | Cross-attention ≤ concat at the frozen margin |
| Gated fusion (`gated_fusion`) | Learned bounded modality weighting | Gate collapse to one modality | Gate collapsing to one view explains the gain without interaction |
| Cross-attention (`cross_attention`) | Learned token-level inter-modality interaction | All-donor peak selection, composition/region×provider, age scale | delta < margin or paired interval crossing zero |
| chr21 dosage (`chr21_dosage`) | Strong genetic baseline (~1.5× HSA21, S58; variegated, S59) | None — it is a near-ceiling control | A paired model that does not beat dosage adds no useful increment |
| QC/covariate (`qc_covariate_logistic`) | Whether technical axes alone predict | Any QC/covariate imbalance between conditions | Covariate-only reaching the fusion's accuracy |

Primary-source dispositions (`OBSERVED_NOW`, reopened this pass; N25–N30):

- S50 (*Nat Methods* 2025, DOI 10.1038/s41592-025-02856-3): integration quality
  dominates classifier choice; hold the encoder/classifier fixed
  (`paired_model`, `multiome_runner.py:122-142` does).
- S51 (CrossAttOmics, *Brief Bioinform* 2025, DOI 10.1093/bioinformatics/btaf302):
  cross-attention resists small training sets below ~300–600 pairs — evidence
  *for* cross-attention at 30 donors, not a guaranteed concat win.
- S52 (arXiv 2606.01207, **preprint**, Flickr8k vision-language): concat needs
  `O(d_v+d_t)` samples vs cross-attention `O(d_v·d_t)`; alignment decides. RNA/ATAC
  are not pre-aligned, but 30 donors is far below the tested 2,048–16,384 scale;
  domain transfer `UNVERIFIED`.
- S55/S56 (*Nat Commun* 2021): cells are pseudoreplicates; donors are the unit;
  >100 cells/individual gives marginal gain. Design already donor-split
  (`estimand.py:54-59`).
- S58 (*Am J Hum Genet* 2007, PMC1950826) / S59 (*Nat Commun* 2024,
  DOI 10.1038/s41467-024-49781-1): HSA21 ~1.5× but mostly compensated and
  variegated, with three molecular subtypes; dosage is a near-ceiling control and
  donor heterogeneity is itself a confounder at n=30.
- S57 (*Genome Biol* 2026, DOI 10.1186/s13059-026-04002-4): peaks+genes did not
  beat peaks-only for cell-type prediction accuracy — direct counterevidence to a
  guaranteed multimodal gain.
- S60 (arXiv 2605.31504, **preprint**, DECAT): cross-cohort stability is a valid
  stress test, but DECAT "cannot be directly applied to early-fusion architectures
  where modalities attend to each other", so it cannot score the cross-attention
  model; only the stability principle transfers. M8 already forbids NeMO refitting.

Leakage/confounding rules carried and confirmed: donor-disjoint splits, all of a
donor's cells together; feature selection and every learned transform fit on
training donors only (`tasks/plan.md:313`; `atac_features.py:58-62,84`); peak
selection on all donors leaks (`§3.3`); region is fully confounded with provider
(18 UCLA all Cortex vs 8 NIH spanning areas, `§3.8`); GW→PCW ≈ −2 is an explicit
approximation. A negative/inconclusive paired result is a valid, publishable
bound on what cross-attention adds at realistic donor counts and prevents
over-claiming a fusion benefit; it does not invalidate the accepted RNA result.
The RNA-only follow-up, if chosen, is a separate prospective study and must not be
presented as the paired cross-attention claim.

**Priority-5 disposition: `CONDITIONAL` — proceed under the existing scientific
contract only after a specific prospective amendment (frozen common-region
recount, §4 rank 1) and after fixing Q22. No claim of novelty-from-complexity or
attention-as-causal-evidence.**

### 3.10 Local CELLxGENE complete-dataset H5AD (`OBSERVED_NOW`)

Source: local `data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad`
(1,569,658,860 bytes; SHA-256 `08d6eff265db6e6a2e1c4a259153588f3dba3c51f5f754736dc63c28795fcdbb`),
the CELLxGENE release named by `uns.citation` (doi 10.1038/s41591-026-04211-1,
collection `0e9fd1d3…`), title "…complete dataset". Read with `anndata` 0.12.6 /
`h5py` 3.16.0 already present in `.venv-p22` (no install, no download). Metadata
and structure only; no donor-level analysis.

Observed structure:

- `obs`: 248,998 rows; `donor_id` 30 categories (15 CON / 15 DS), `sample` 30,
  `library` 37. The 37-library and 30-sample sets are set-equal to the pinned
  `B02` final cohort (`§3.7`): zero diff in either direction. `dev_PCW` ∈ 10–20.
- `cell_id` = `{library}_{10x barcode}` (e.g. `B10C1Q_AAACAGCCAACTAGCC-1`), so
  every retained barcode joins to library and donor with no external artifact.
- `var`: 35,477 genes only (`feature_type` all gene classes); no `chr:start-end`
  rows, no `Peaks`, no ATAC layer in `X`, `raw/X`, `layers` or `obsm`. The open
  export is RNA-only.
- `raw/X`: CSR, 360,876,411 integer entries, max 375 → raw-scale counts. Caveat:
  per-cell row sums differ from `nCount_RNA` (median −4, max −90; 6.8% exact), so
  `raw/X` is raw-scale but not proven to be the exact cellranger-arc raw matrix.
- Per-cell ATAC QC columns present: `nCount_ATAC` (101–24,997), `nFeature_ATAC`
  (18–11,250), `TSS.enrichment` (>1.102), `nucleosome_signal` (<2),
  `percent.mt` (<2), `nCount_RNA` (501–29,972) — every row passes the B02 rule
  by construction.
- `cells_in_excitatory_lineage_subset` = 215,680 cells across all 30 donors and
  PCW10–20; `cluster_name_subset` has 11 labels. Candidate cell membership for
  the selected `exc_lin_PCW10_20` object; exact equivalence to the C03 object is
  `UNKNOWN`.

Consequences:

- The development cohort's retained-barcode/library/donor join — named minimal
  artifact (c) in `§6` — is already public and local, readable with zero install.
  Only the ATAC measured counts are missing from it.
- Priority-4 reader path: the RNA + metadata + cell-membership side needs no R
  reader and no install; only the ATAC measured counts need the R object or
  fragments.
- Counterevidence to "only the 7.6/8.7 GiB objects can enumerate the final
  cohort": the open H5AD already enumerates it exactly. It does **not** close the
  paired gate — it has no ATAC matrix, so the only open ATAC routes remain the 46
  GEO per-library peak matrices or a fragment recount.

Reproduce (local metadata only):

```bash
cd /Users/anuragdani/Github/niw-eb1a/P22 && .venv-p22/bin/python - <<'PY'
import h5py, csv
p='data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad'
with h5py.File(p,'r') as f:
    o=f['obs']
    libs={c.decode() for c in o['library']['categories'][:]}
    smps={c.decode() for c in o['sample']['categories'][:]}
    print(len(o['cell_id']), len(libs), len(smps),
          list(f['X'].attrs['shape']), list(f['raw']['X'].attrs['shape']))
B=list(csv.DictReader(open('data/multiome/Lattke_B02_gr_tab_filtered_non_cx_excl_227f51b.csv')))
assert libs=={r['library'].strip() for r in B} and smps=={r['sample'].strip() for r in B}
print('H5AD cohort == B02 final cohort')
PY
```

### 3.11 GEO provider statement on the deposited objects (`OBSERVED_NOW`)

Source: local `data/multiome/GSE305146_family.soft.gz` (SHA-256
`8299f15e35f6eda820ac9c9995be94fce648299b12e0ec12e4b7e68d3ab3f087`; 4,890 lines);
per-sample `!Sample_data_processing` lines 317–321 (repeated for all 92 samples) and
`!Series_supplementary_file` lines 119–258.

- **Provider inventory (line 321):** "Supplementary files format and content: rda
  files containing the Seurat objects with labelled cell clusters and sample
  metadata (for complete dataset and filtered excitatory lineage cells)". This is the
  provider's own description of the two objects and corroborates Q4 with a statement
  rather than filename/flow inference: complete dataset ↔ `B04` labelled complete,
  filtered excitatory lineage ↔ `C03` labelled exc-lin. It lists **no cluster-peak
  assay**, supporting (not proving) Q2.
- **Version conflict (line 318):** the pipeline is "R v4.3.3 … Seurat … v5.1.0 …
  Signac … (v1.13.0)", linking `github.com/lattkem1/Down_Syndrome_Multiome`. The
  pinned `Packages_installed_250801.csv` records Seurat 5.3.0 / Signac 1.14.0. The
  GEO text and the package snapshot disagree; the version that serialized the
  deposited object is `UNKNOWN` (Q33). An S4 object written under 5.1.0/1.13.0 read
  by a 5.3.0/1.14.0 stack is normally backward-compatible but is untested here.
- **Scope:** 140 `!Series_supplementary_file` lines = 46 libraries × 3 files + 2
  `.rda`; there is no `!Series_data_processing` and no other manifest. The string
  `peaks_by_cluster` occurs 0 times in the SOFT; `seur_integr` occurs only on the two
  Series supplementary lines. No authoritative object-member inventory exists beyond
  line 321.

### 3.12 Priority-4 ATAC-side reader and resource path (`OBSERVED_NOW`)

**What the reader is for.** Even a perfect reader cannot close the paired gate: the
deposited objects' ATAC assay is a naive merge (Q3) and the selected object is
pre-`F01` (Q2). Both were re-verified from the pinned tree this pass:
`B01_v041_load_from_cellranger_arc.R:132-172` builds each library's
`CreateChromatinAssay(counts = counts$Peaks, …)` and `merge(seur_list[[1]],
y = seur_list[-1], merge.data = TRUE)` with no `FeatureMatrix`; the correct pinned
`F01_v045_seur_call_quant_peaks_by_cluster.R` loads
`C03_seur_integr_labelled.rda`, calls `CallPeaks(group.by = "cluster_name")`,
quantifies with `FeatureMatrix(fragments = Fragments(seur), …)`, adds
`peaks_by_cluster`, and `save(seur, peaks, …seur_w_peaks_by_cluster_quant.rda)` — a
different file. The pinned tree is complete (139 entries, `truncated:false`; PCW dirs
are `_PCW11_13`/`_PCW16_20`, not `PCW10_20`). So the reader's only unique value is
the E2-R assay-inventory check; RNA/labels/barcodes are already available from the
local H5AD (§3.10). The reader is a bounded verification task, not the critical path.

**Author class/version requirements (pinned `Packages_installed_250801.csv`).**
R 4.3.3; Seurat 5.3.0; SeuratObject 5.1.0; Signac 1.14.0; Matrix 1.6-5;
GenomicRanges 1.54.1; IRanges 2.36.0; S4Vectors 0.40.2; GenomeInfoDb 1.38.8;
BiocGenerics 0.48.1; DelayedArray 0.28.0; HDF5Array 1.30.1; hdf5r 1.3.12;
SummarizedExperiment 1.32.0; BPCells 0.1.0; chromVAR 1.24.0; EnsDb.Hsapiens.v86
2.99.0; BSgenome.Hsapiens.UCSC.hg38 1.4.5; motifmatchr 1.24.0; TFBSTools 1.40.0.
The pinned reader image proved only R 4.6.1 / Matrix 1.7.6 (contract `reader_proof`).

**Signac class structure (official source).** `ChromatinAssay <- setClass(Class =
"ChromatinAssay", contains = "Assay", slots = list(ranges = "GRanges", motifs =
"ANY", fragments = "list", seqinfo = "ANY", annotation = "ANY", bias = "ANY",
positionEnrichment = "list", links = "GRanges"))` (Signac `R/objects.R`).
`GetAssayData.ChromatinAssay` dispatches `layer` to `methods::slot(object, layer)`,
so ATAC counts are `@counts`. The author built the RNA assay with
`CreateAssayObject` (v3 `Assay`), not `CreateAssay5Object`; `Assay5` is a different
class with arbitrary `layers`. A reader must resolve `Seurat`/`Assay`,
`Signac`/`ChromatinAssay` and the GRanges stack together.

**`.rda` semantics (official).** `save()` writes one tagged pairlist of all workspace
objects and `load()` deserializes all of them; there is no supported selective/partial
read (`?load`, R 4.6.0; R Internals §1.8). Namespace references degrade to the global
environment with a warning when a namespace is unavailable (`?load`), but S4 class
attributes name the defining package (R Internals §1.12.1), and R resolves that
package when constructing the object. An absent defining package therefore leaves
slots/dispatch unreliable; the exact failure mode remains `UNVERIFIED` without
execution, but the evidence requires the full defining stack, not just `Matrix`.

**Route comparison (corrected).** (a) A minimal R reader with the full
Seurat/SeuratObject/Signac + GRanges/S4Vectors/GenomeInfoDb/Matrix stack is the only
route to exact measured ATAC counts/intervals, with full deserialization and no
partial read. (b) No author sparse export exists: the complete pinned tree (139
entries, `truncated:false`) has no count checkpoint and no `peaks_by_cluster` object.
(c) `pyreadr` cannot parse R lists or S4 objects (librdata); `rpy2` needs an R
install. (d) The pure-Python `rdata` package *can* parse S4 (default →
`types.SimpleNamespace`), exposing `dgCMatrix` slots `i`/`p`/`x`/`Dim`/`Dimnames`,
but it has no default Matrix constructor, is untested on a Seurat object, is not
installed, and offers no selective read. Correction to dossier R3: it evaluated
`pyreadr` as "Python-only unsupported" without separating the S4-capable pure-Python
`rdata`; `rdata` is a genuine untested alternative that must not be promoted above
the R route without a fixture run, nor declared impossible.

**Repository fixture state (corrected).** `scripts/inspect_development_object.R`
(SHA `aef9ccc1a8c19bf0ab53f848a5edcbb86bbb76195a3dbd288a0520dec67e36e7`) builds a
plain `list(counts = dgCMatrix, regions = data.frame, cells = data.frame)` and writes
it with `saveRDS(..., version = 3)` — an `.rds` of base classes, not a `save()`
workspace and not a Seurat/`ChromatinAssay` object. `scripts/run_r_fixture.py:31`
pins that SHA. The contract's `reader_proof` already records
`tested_serialization = saveRDS/readRDS … not save/load of a .rda workspace`, so the
E2-R required proof ("Applicable save/load .rda workspace and Seurat/ChromatinAssay
extraction") is **not met**. Minimal upgrade spec (`PROPOSED`, ≤1 MiB): one
`save(seur, file = …rda, version = 3)` workspace containing exactly one `Seurat`
with a v3 `Assay` (3×4 `dgCMatrix` counts) and a `ChromatinAssay` (3×4 `dgCMatrix`,
`ranges` a GRanges with `chr:start-end` names, `genome = "hg38"`), and `meta.data`
with a `donor` column. Assert after `load(envir = new.env())`: exactly one member;
expected assay names/classes; `LayerData(…, "counts")` exact nonzero entries/order;
`granges` intervals/genome; donor metadata. Refusal cases: extra workspace member;
non-`dgCMatrix` counts; missing defining package → `NOT_RUN`; corrupt/truncated
workspace. Proposal until run and reviewed.

**HEAD-control accounting (proposed limits vs actual code).** The contract's HEAD
proposal caps process-tree memory 268435456 B, swap 0, wall 15 s, retained output
1048576 B. By domain: **workload** = the in-container Python running
`capture_development_head.capture_head` (plus threads); the 256 MiB cgroup
`memory.max` covers this tree and its charged page/kernel memory, while `body_bytes`
counts application reads only and excludes TLS/OS buffering
(`capture_development_head.py:5-6,45`). **Supervisor** = the host launcher calling
`capture_head`; `launcher_head_capture.preflight` is offline, reserves nothing
(`output_reserved=false`) and enforces no memory/deadline — not covered.
**Docker client** = the host `docker` CLI subprocess — not covered by the container
cgroup. **Linux guest** = the Docker Desktop VM's own memory/swap/disk and the
daemon, outside the container `memory.max`; "zero swap" is certifiable only for the
container cgroup. **Host** = macOS RAM/swap/disk shared with the VM; Docker flags
bound no host paging. Deadline/output: `capture_development_head` sets one absolute
15 s deadline via `SIGALRM`, but its own docstring warns "Python signals can be
delayed by C execution" and there is no external watchdog; the header loop is capped
at 65,536 bytes and reads no body. `run_r_fixture.run_owned` (a different helper)
uses `communicate(timeout = seconds)` and kills the container on timeout, and its R
path has no byte-counting output reader. Proposed limits, configured flags, sampled
usage and demonstrated enforcement stay distinct: only the R fixture has
demonstrated cgroup enforcement (4 GiB normal / 128 MiB OOM), and none of the HEAD
proposal is bound to a live launcher.

**Priority-4 disposition: `RESOURCE_UNRESOLVED` (ATAC-side reader).** No untested
route can be accepted or rejected without an install or fixture run; the minimal R
route requires the full Seurat/Signac/Bioconductor stack, the pure-Python `rdata`
route is untested, and the existing fixture does not meet the contract's required
proof. The reader is a bounded E2-R verification task and cannot close the paired
gate even if it succeeds (Q2/Q3).

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
| 3 | **Deposited 7.6 GiB exc-lin object** | A labelled cell set and RNA layers | ATAC assay is naive merge (Q3); `peaks_by_cluster` absent (Q2); unknown decoded size/RAM; `object_inspection_authorized=false`; provider inventory lists only labelled clusters + metadata (§3.11) | Inspect assay feature count/ranges if ever authorized | Cannot supply comparable measured ATAC counts even if it loads |
| 4 | **GEO per-library MEX ATAC matrices** | Per-library measured counts on library-specific peaks | No common exact feature space (Q1); union leaves unmeasured coverage | Full 46-library intersection/overlap reconciliation (deferred check, §5) | Not a common measured matrix; cannot be zero-filled |
| 5 | **Cross-cohort direct matrix comparison (GSE305146 vs NeMO)** | Nothing exact | Different peak-calling studies; different count stages; no shared intervals | None short of recount on a common frozen set | Rejected for confirmatory; exploratory only with explicit `peak_derived` labelling |
| 6 | **Peak-to-gene summed score** | A derived exploratory signal | Pinned gene annotation/interval/overlap policy | Hand-calculated overlap examples + missingness per gene | Exploratory only; not exact fragment gene activity |
| 7 | **Local CELLxGENE complete-dataset H5AD (RNA-only)** | Exact final-cohort retained barcodes, library/donor join, raw-scale RNA counts, per-cell ATAC QC metadata | No ATAC measured counts; `raw/X` not proven to be the exact raw matrix | Confirm no ATAC layer (done, §3.10) | Zero-download Python read for the RNA/join side; cannot supply paired ATAC |

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
- **Could the open CELLxGENE H5AD make the R objects unnecessary?** For the RNA
  side, the donor join and the retained barcodes, yes (`§3.10`); for the measured
  ATAC counts, no — the export has no ATAC layer. Overturning evidence: an ATAC
  assay or peak matrix inside the H5AD (none found) or an open ATAC export on the
  same common regions.
- **Could the paired comparison be scientifically vacuous?** Only if the
  incremental question were already answered by the completed RNA study or
  inseparable from a simpler control. The estimand differs (cross-attention−concat
  vs RNA donor association) and the controls are separable (§3.9), so the question
  is refutable and worth asking. Counterevidence to a *positive* claim: S57
  (peaks+genes did not beat peaks-only for prediction), S52 (alignment can favor
  concat), and the project's own all-donor peak selection. Overturning evidence for
  a positive claim: an accepted paired delta ≥ margin with all simpler controls
  reported and no interval crossing zero.
- **Could DECAT (S60) certify a shared-biology paired result?** No — S60 states
  DECAT cannot be applied to early-fusion architectures where modalities attend to
  each other, which is exactly the cross-attention model. Only the cross-cohort
  stability principle transfers. Overturning evidence: a DECAT variant that
  supports early fusion.
- **Could the object be read without the full R stack?** Not proven. `pyreadr`
  cannot parse S4/lists (JOSS 2024); the pure-Python `rdata` package can parse S4
  to `SimpleNamespace` but has no Matrix constructor and is untested on a Seurat
  object. Overturning evidence: a `rdata` fixture run that extracts the `@counts`
  `dgCMatrix` from a Seurat `.rda` with exact nonzero entries, or an official
  Seurat/SeuratObject statement that a minimal subset of packages suffices.
- **Could a successful reader still justify the download?** Only if it reveals a
  common, measured ATAC feature space or a `peaks_by_cluster` assay. The provider
  inventory (§3.11) and the pinned `B01`/`F01` code predict neither. Overturning
  evidence: object inspection showing a common measured range set.

## 5. Prioritized implementation handoff and the single next action

All six priorities now have supported dispositions: priority 1 (§3.7), priority 3
(§3.8), priority 5 (§3.9, `CONDITIONAL` — the primary contrast is implemented,
refutable and worth running, but only under a prospective amendment and after the
Q22 estimand fix), priority 4 (§3.12, `RESOURCE_UNRESOLVED`), priority 2 (§4 route
table, with the full 46-library reconciliation below as the one remaining
approval-gated check), and priority 6 (this handoff). The RNA/donor-join/
cell-membership side is a zero-install Python read (§3.10), so only the ATAC side
was reader-dependent.

Completed priority-4 disposition (kept for the record; no further action unless a
fixture/install is authorized): the ATAC-side reader is `RESOURCE_UNRESOLVED`
(§3.12). The minimal R route needs the full Seurat/Signac/Bioconductor class stack;
`pyreadr` cannot parse S4/lists; pure-Python `rdata` is untested/not installed; the
existing E2-R fixture is a base `.rds`, not the contract's required `save()`
workspace with Seurat/`ChromatinAssay`. The exact minimal fixture spec and the
HEAD-control accounting (workload/supervisor/client/guest/host) are in §3.12. Even a
successful read cannot close the paired gate (Q2/Q3).

**Single highest-value next action (do this first): complete the 46-library
peak-space reconciliation (priority 2's smallest decisive check).**

- Input: the 46 public `GSE305146_<library>_features.tsv.gz` files (~1–3 MB each; no
  `matrix.mtx.gz`, no barcodes, no fragments). Three are local; the other 43 are
  small public annotation files.
- Method/output/acceptance: as in §3.4, extended to all 46 libraries; verdict
  `COMMON_EXACT_SUBSET=EMPTY|SMALL|ADEQUATE`; must reproduce 46,672 / 20,708 /
  22,676 and 3/0/0/0 on the three local files.
- Authority: these are dataset supplementary files, not merely a published mapping
  table, so the 43-file fetch is a scoped approval item, not an assumed right. If
  approval is not granted, the fallback is the F01 artifact request (§6 item 1a).
- How either result changes the next decision: an empty/tiny common exact subset
  (expected, given 3/0/0/0) leaves a frozen-region recount as the only valid route —
  choose between requesting the minimal author artifacts and a bounded-recount
  amendment, not a 7.6 GiB download. An adequate subset makes the cheap GEO MEX
  route viable within-study, deferring the recount to the external (NeMO) side.

Completed priority-3 disposition (kept for the record; no further action unless
the artifact is requested): the external cohort is resolved to the
metadata/count-stage level (§3.8); the one remaining unknown is an author QC
rule/retained-barcode artifact, requested in §6 item 2. Verdict:
`EXTERNAL_QC_RULE_UNRESOLVED`; keep the external cohort `covariate-limited`.

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

**How either result changes the next decision.** An empty/tiny common exact subset
(expected) leaves a frozen-region recount as the only valid route — choose between
requesting the minimal author artifacts and a bounded-recount amendment, not a
7.6 GiB download. An adequate subset makes the cheap GEO MEX route viable
within-study, deferring the recount to the external (NeMO) side.

Supporting handoff tasks (existing IDs; do not invent):

- **E2-R** (`tasks/todo.md`, target reader/resource contract): the object's ATAC
  assay is a naive merge (`INFERENCE`), so E2-R must require, before any load, a
  documented assay-inventory check (assay names, `counts` layer type, feature
  count, whether `peaks_by_cluster` exists) and must not assume a comparable
  measured ATAC matrix. Acceptance: a `<=1 MiB` applicable `save()` `.rda`
  workspace with Seurat/`ChromatinAssay` (exact spec in §3.12) passes and refuses
  unexpected classes. The current `scripts/inspect_development_object.R` fixture
  (base `list` via `saveRDS`) does **not** meet this and must be upgraded first.
- **E2-M1** (`tasks/plan.md`): runtime/control feasibility. Keep separate from the
  data question. The earlier "256 MiB / 15 s feasible" assertion is `UNVERIFIED`
  (Q7); require an end-to-end measurement before treating the HEAD contract as
  feasible.
- **Contract update** (`configs/development_object_source_contract.json`, requires
  authority): correct any budget text derived from the "4×" factor to 16×, and add
  the `peaks_by_cluster`-absent and naive-merge findings to the `not_proven`/scope
  notes. Do not edit without owner approval.
- **M5 estimand fix** (`src/p22/eval/estimand.py:20-29`): add `token_concat` and
  `cross_attention` to `NAMED_BASELINES` (or explicitly document that it is the
  cheap-control list only) so the frozen manifest and `baseline_table` name the
  primary-contrast arms. Entry point: `estimand.py`; expected output: updated
  tuple; acceptance: `tests/test_multiome_protocol.py` and
  `tests/test_professor_gates.py:99` still pass and the manifest lists both arms;
  authority: code review (this is a code change, not executed here).

## 6. Remaining evidence / approval requests and bounded proposed checks

1. **Minimal artifact request (draft only; do not send).** To the Lattke authors at
   pinned commit `227f51b4…` / GEO `GSE305146`: (a) the F01 output pair
   `F01_seur_w_peaks_by_cluster_quant.rda` and `F01_peaks_by_cluster.bed`; (b) a
   one-page manifest stating, for
   `GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz`, the workspace member
   names, assay names, ATAC feature-space definition, count stage, genome build and
   interval convention — **partly answered by the GEO provider statement (§3.11,
   "Seurat objects with labelled cell clusters and sample metadata"), which still
   does not enumerate assays or the ATAC feature space**; (c) the retained-barcode
   list per library — **narrowed by
   §3.10**: the final-cohort retained barcodes, library and donor join are already
   public and local in the CELLxGENE H5AD, so (c) is now only needed for the
   *pre-QC/cellranger* barcode stage, not the final cohort; (d)
   `B02filter_stats.csv` (per-library `N_cells_unfiltered`, `N_cells_filtered`,
   `fract_removed`, `cells_retained`) to attribute the 3 B02-QC drops exactly. The
   exclusion rule behind the 37-library/30-specimen final cohort is already public
   (`B02_v040…R:46-68`, §3.7); these are the minimum artifacts that would convert
   the remaining `INFERENCE`/`UNVERIFIED` rows into `SUPPORTED` without any large
   download.
2. **NeMO count-stage definition (draft only).** Request the author's QC table or
   count-stage definition behind the release `nCount_ATAC`/`class` columns, the
   author rule connecting 117,532 release rows to the reported 113,801 (the
   `Unk` partition matches exactly but is unstated), and the author-defined final
   barcode list. Needed before external QC replay; the release column cannot be
   substituted for the QC-stage fragment count (it fails the paper's own
   `nCount_ATAC`>100 filter for 1,798 rows, §3.8).
3. **Bounded proposed checks (PROPOSED, no execution authority yet):**
   - 46-library peak reconciliation (§5, now the single next action); needs scoped
     approval because it fetches 43 dataset-adjacent supplementary files.
   - Scientific-value / RNA-only-fallback assessment: completed iteration 4
     (§3.9, disposition `CONDITIONAL`); no further action unless the Q22 fix or
     prospective amendment is reviewed.
   - Minimum reader/resource path (priority 4): completed iteration 6 (§3.12,
     disposition `RESOURCE_UNRESOLVED`); no further action unless a fixture or
     package install is authorized.
   - External-cohort provenance pass: completed to the metadata/count-stage level
     (§3.8); re-open only to request the author QC rule/barcode artifact.
   - A tiny `.rda`/Seurat/`ChromatinAssay` fixture (exact spec in §3.12, upgrading
     the earlier dossier R3 design and the current base-`list` `.rds` fixture) to
     close the reader-class gate — a proposal until run and reviewed.
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
- Earlier-campaign dossier worktree `p22-research-campaig-b057f9` is now complete:
  iteration 4 reads HEAD `b64ba07`, SHA-256
  `c0d6206f81edea661d7ca22c66de138a8103cbeb4ec55e7fabb7fe673db37487`, with R1–R8
  bodies present (the earlier iterations saw `7e37ceb` and `b40458f`). Its R1–R6
  are treated as `RECORDED_PREVIOUSLY`; R7/R8 were re-read and their consequential
  claims (donor counts, margin arithmetic, `NAMED_BASELINES` gap, R6 citation
  correction) re-verified locally this run.
- Required hashes re-checked iteration 5: contract
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
| N19 | NeMO `col-umstjg0` parent page (controlled, GRU + not-for-profit + local IRB; 127 files/760 GB) | OBSERVED_NOW | 2026-09-20 |
| N20 | NeMO open children `col-mbgxwtz` (RNA) / `col-ad8t52b` (ATAC) | OBSERVED_NOW | 2026-09-20 |
| N21 | Manuscript data-availability statement (NeMO `col-umstjg0`; no code repo named) | OBSERVED_NOW | 2026-09-20 |
| N22 | Web search for a Vuong/de la Torre-Ubieta analysis code repo (none found) | OBSERVED_NOW | 2026-09-20 |
| N23 | Local release metadata re-analysis (§3.8; 117,532×22; QC replay 113,242) | OBSERVED_NOW | 2026-09-20 |
| N24 | Manuscript QC/age/provider methods (XML, `S21` QC section; sample acquisition) | OBSERVED_NOW | 2026-09-20 |
| N25 | `src/p22/eval/estimand.py`, `multiome_runner.py`, `multiome_final.py`, `multiome_protocol.py`, `named_baselines.py` (primary-contrast implementation + Q22 gap) | OBSERVED_NOW | 2026-09-20 |
| N26 | S50, Liu et al., *Nat Methods* 2025, DOI 10.1038/s41592-025-02856-3 (integration quality dominates classifier) | OBSERVED_NOW | 2026-09-20 |
| N27 | S51, Beaude et al., CrossAttOmics, *Brief Bioinform* 2025, DOI 10.1093/bioinformatics/btaf302 (cross-attention with few paired examples) | OBSERVED_NOW | 2026-09-20 |
| N28 | S52, arXiv 2606.01207 (preprint; alignment/sample complexity O(d_v+d_t) vs O(d_v·d_t)) | OBSERVED_NOW | 2026-09-20 |
| N29 | S55 Zimmerman *Nat Commun* 2021 + S56 Squair *Nat Commun* 2021 + S58 Aït Yahya-Graison *Am J Hum Genet* 2007 + S59 Donovan *Nat Commun* 2024 (donor unit; HSA21 dosage) | OBSERVED_NOW | 2026-09-20 |
| N30 | S57 Acera-Mateos et al., *Genome Biol* 2026, DOI 10.1186/s13059-026-04002-4; S60 arXiv 2605.31504 DECAT (peaks+genes vs peaks-only; early-fusion limitation) | OBSERVED_NOW | 2026-09-20 |
| N31 | Local CELLxGENE `data/real/f16c25da-…h5ad` (SHA `08d6eff2…`; 248,998×35,477 RNA-only; 37 libraries / 30 samples set-equal to B02) | OBSERVED_NOW | 2026-09-21 |
| N32 | GEO SOFT `!Sample_data_processing` lines 317–321 + `!Series_supplementary_file` lines 119–258 (provider inventory of the two `.rda`; version text; 46×3+2 files) | OBSERVED_NOW | 2026-09-21 |
| N33 | Pinned `Packages_installed_250801.csv` @ `227f51b4…` re-parsed (Seurat 5.3.0/SeuratObject 5.1.0/Signac 1.14.0/Matrix 1.6-5 + Bioc stack) | OBSERVED_NOW | 2026-09-21 |
| N34 | R base `load` reference (R 4.6.0; whole-workspace load; namespace-ref degradation) + R Internals §1.8/§1.12.1 (S4 class attr names package) | OBSERVED_NOW | 2026-09-21 |
| N35 | Signac `R/objects.R` `ChromatinAssay` class def + `GetAssayData.ChromatinAssay`; SeuratObject `Assay5` vs `Assay` docs | OBSERVED_NOW | 2026-09-21 |
| N36 | `rdata` (JOSS 2024) docs/conversions (S4→`SimpleNamespace`; pyreadr/librdata cannot parse S4/lists); pinned `B01`/`F01` re-read; `inspect_development_object.R`/`run_r_fixture.py` fixture state | OBSERVED_NOW | 2026-09-21 |

Reused without re-fetch: earlier dossier S1–S42 (local canonical docs, saved Vuong
XML/NeMO metadata, pinned author tables). Coverage: iter 1 — author source tree + 8
scripts, Signac docs, GEO listing, local annotations/contract/plan/code; iter 2 —
GEO SOFT, pinned `A_input`/`B02` tables, pinned B02 script/tree, campaign dossier;
iter 3 — local Vuong XML and release metadata, NeMO pages, author-code search (none
found); iter 4 — local paired-model/estimand code and six primary method sources
(S50–S52, S55–S60 subset; N26–N30); iter 5 — local CELLxGENE H5AD structure and
cohort reconciliation vs pinned B02 (metadata/structure only); iter 6 — GEO SOFT
provider statement, pinned package CSV, R/Signac/SeuratObject/rdata docs, pinned
`B01`/`F01` re-read, local fixture state. No payload, object, fragment or matrix
reads beyond the local H5AD structure; no install, container, training or author
contact.

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
8. The earlier-campaign dossier progressed mid-run (`7e37ceb` → `b40458f` →
   `b64ba07`); by iteration 4 it is complete with R1–R8 bodies (SHA `c0d6206f…`),
   so the earlier "R7 has no body" caveat no longer applies.
9. The NeMO `nCount_ATAC` column is **not** the QC-stage fragment count: 1,798
   release rows have `nCount_ATAC`<=100 (Q9 `UNVERIFIED` → `REJECTED`, iteration 3).
10. The paper's stated QC replay gives **113,242**, not 113,801; the 113,801 is
    exactly the RNA non-`Unk` count (iteration 3, §3.8). Do not equate them.
11. `Unk` is a cell-type annotation class, not the QC-dropped set: 93.1% pass QC
    and have higher counts than non-`Unk` (iteration 3, §3.8).
12. Vuong reports obstetric *gestational weeks*, not post-conception weeks; Lattke
    `dev_PCW` needs a ≈2-week conversion before any age join (iteration 3, §3.8).
13. The frozen estimand's `NAMED_BASELINES` omits `cross_attention`/`token_concat`
    even though the runner implements the primary contrast; the earlier campaign's
    R8 finding is confirmed as a real M5/M6c gap, not a runner blocker (iteration
    4, Q22, §3.9).
14. The earlier dossier's S52 citation is an unrefereed vision-language preprint
    with a conditional direction, and S60's DECAT explicitly cannot score
    early-fusion cross-attention; both must be cited with those limits (iteration
    4, §3.9).
15. The earlier dossier called the CELLxGENE H5AD a "different representation" but
    did not verify its cohort: it is exactly the B02 final 30-specimen/37-library
    cohort and holds raw-scale RNA counts with a barcode→library→donor join; it is
    RNA-only (no ATAC). Its `raw/X` is raw-scale but not proven to be the exact
    cellranger-arc raw matrix (row sums differ from `nCount_RNA`) (iteration 5,
    §3.10).
16. The earlier dossier R3 recorded the reader class versions from the pinned
    package snapshot (Seurat 5.3.0 / Signac 1.14.0) but did not note the GEO
    submission's conflicting text (Seurat v5.1.0 / Signac v1.13.0); the version
    that serialized the object is `UNKNOWN` (iteration 6, Q33, §3.11).
17. The earlier dossier R3's route (d) conflated `pyreadr` (cannot parse S4/lists)
    with the pure-Python `rdata` package (parses S4 to `SimpleNamespace`); they are
    distinct routes with different evidence (iteration 6, §3.12).
18. The existing E2-R fixture (`scripts/inspect_development_object.R`) is a base
    `list` written with `saveRDS`, not the `save()` workspace with
    Seurat/`ChromatinAssay` the contract requires; the earlier dossier's R3 fixture
    design was never implemented (iteration 6, Q36, §3.12).

### Iteration progress

- Iteration 1: R6 (defensible common ATAC feature route) researched; object
  provenance chain recovered; naive-merge finding; 3-library peak-space
  measurement; arithmetic/challenge corrections; handoff created.
- Iteration 2: priority 1 closed — full library↔specimen reconciliation
  from GEO SOFT + pinned author tables, two exclusion layers, duplicate-key checks,
  three claim corrections, and the minimal missing artifact (`B02filter_stats.csv`)
  named. Next action moved to priority 3 (external-cohort provenance).
- Iteration 3: priority 3 resolved to the metadata/count-stage level
  (§3.8) — 113,801 = RNA non-`Unk` (stated-QC replay 113,242), release
  `nCount_ATAC` is not the QC column, `Unk` is an annotation class, cohort is 26
  donors / 13 libraries with provider×region confounding, GW≠PCW. No author code
  repo/barcode artifact found (Q21). Single next action moved to priority 5.
- Iteration 4: priority 5 resolved to `CONDITIONAL` (§3.9) — the
  primary contrast is implemented in the runner (`multiome_final.py:190`), the
  frozen estimand omits its two arms (Q22), and six primary sources were reopened
  with two corrections (S52 preprint/conditional, S60 cannot score early-fusion
  cross-attention). Single next action moved to priority 4.
- Iteration 5: characterized the local CELLxGENE complete-dataset
  H5AD (§3.10) — 248,998 cells, 37 libraries / 30 samples set-equal to B02,
  raw-scale RNA counts, barcode→library→donor join, no ATAC; Q28–Q31 added and
  correction 15 recorded. Priority 4 narrowed: only the ATAC side needs an R
  reader; single next action is the ATAC-side reader/fixture.
- Iteration 6 (this pass): closed priority 4 to `RESOURCE_UNRESOLVED` (§3.12) —
  verified author class versions from the pinned CSV, the Signac `ChromatinAssay`
  class/`GetAssayData` path, `.rda`/S4 load semantics, the three reader routes
  (correcting the `pyreadr` vs pure-Python `rdata` distinction), the existing
  fixture gap with an exact minimal fixture spec, and the HEAD-control
  workload/supervisor/client/guest/host accounting. Recovered the GEO provider
  statement on the two `.rda` objects and the reader-version conflict (§3.11);
  Q32–Q37 and corrections 16–18 added; single next action is the approval-gated
  46-library peak reconciliation (fallback: F01 artifact request).
- Stop condition: met. Priorities 1–6 all have supported dispositions (1 §3.7,
  2 §4 route table + §5 bounded check, 3 §3.8, 4 §3.12, 5 §3.9, 6 this handoff);
  the consequential claims were re-verified this pass (`B01`/`F01`, package CSV,
  H5AD cohort, GEO provider statement, contract hashes). The remaining items are
  authority-gated (43-file fetch) or contact-gated (author artifacts), so the
  research handoff is complete; `should_fully_stop=true`.

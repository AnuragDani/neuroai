# P22 deep-research handoff for Codex

Prepared 2026-09-20 (iteration 1; updated through iteration 4). Worktree
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
only under a prospective amendment and after the estimand fix (Q22).**

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

Iterations 1–3 (details and sources in §3 and the progress log): recovered the full
object-provenance chain (both GEO objects map to author stages B04/C03; the selected
object is pre-`F01`, so `peaks_by_cluster` is absent); showed the deposited ATAC
assay is a naive per-library peak merge, not a common measured space (Signac warns
this "can result in inaccuracies"); measured 3 of 46 GEO per-library peak spaces
(exact intersections 3/0/0/0, overlap 17–76%); corrected the 4 GiB-vs-256 MiB
factor to 16× and the `create_args`/`run_owned` characterizations; reproduced the
46→37→30 library/specimen progression with two exclusion layers and named
`B02filter_stats.csv` as the minimal missing artifact; and resolved the external
cohort to 26 donors/13 libraries with 113,801 = RNA non-`Unk` (stated-QC replay
113,242), release `nCount_ATAC` ≠ QC stage, `Unk` an annotation class, and
obstetric GW ≠ post-conception weeks.

What iteration 4 adds (all `OBSERVED_NOW` unless noted) — priority 5 is now
resolved to a decision, and the primary-contrast arms are checked against the
frozen estimand:

16. **The frozen primary contrast is implemented in the runner but missing from
    the frozen estimand's declared baseline list (Q22).** `NEURAL_FAMILIES`
    (`multiome_runner.py:112-119`) and `multiome_final.py:190`
    (`paired_comparison(cross_attention, token_concat)`) implement the contrast,
    but `estimand.NAMED_BASELINES` (`estimand.py:20-29`) omits both arms and drives
    `baseline_table`/`FrozenEstimand.baselines`. This confirms the earlier
    campaign's R8 prerequisite gap; the runner is unaffected, the M5 manifest/G6
    report is.
17. **Priority-5 primary sources were reopened and mostly upheld, with two
    corrections** (full detail in §3.9): S52 is an unrefereed vision-language
    preprint whose direction is conditional, and S60's DECAT explicitly cannot
    score early-fusion cross-attention. Verified: integration quality dominates
    classifier choice (S50); cross-attention helps with few paired examples (S51);
    cells are pseudoreplicates (S55); HSA21 dosage is ~1.5× but mostly compensated
    and variegated (S58, S59); peaks+genes did not beat peaks-only for prediction
    (S57); external cross-cohort stability is a valid stress test (S60).
18. **Priority-5 verdict: `CONDITIONAL`** — the incremental question is not
    already answered by the completed RNA study, is refutable at the 0.07/0.08
    margin, and has value as a negative result, but is confounded by all-donor
    peak selection, provider×region, age scale and a framework that cannot
    diagnose cross-attention. Proceed only after a prospective amendment and the
    Q22 fix; no novelty-from-complexity or attention-as-causal claims.

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

## 5. Prioritized implementation handoff and the single next action

Priorities 1 (§3.7), 3 (§3.8) and 5 (§3.9) now have supported dispositions.
Priority 5 is `CONDITIONAL`: the primary contrast is implemented, refutable and
worth running, but only under a prospective amendment and after the Q22 estimand
fix. Priority 2 has a route table (§4) with the full 46-library reconciliation
deferred as an approval item. Priority 6 is the decision/handoff itself. The
single next action therefore moves to priority 4, the remaining independently
researchable question: the minimum reader/resource path that could work.

**Single highest-value next action (do this first): establish the minimum
reader and resource path that could work (priority 4).**

- Input: official R, SeuratObject, Seurat, Signac and sparse-format
  documentation/source; the pinned author `Packages_installed_250801.csv`;
  `configs/development_object_source_contract.json`; the earlier-campaign dossier
  R2/R3 and the local fixture helper `scripts/run_r_fixture.py`. Public
  docs/author code + local code inspection only; no installs, no container
  launch, no payload.
- Method: (a) separate the packages the author's full analysis needs from those
  required only to deserialize, validate and extract counts; (b) distinguish
  constructing a new object from reading an existing one; (c) compare a minimal R
  route, a documented author export, and interchange/Python alternatives without
  declaring any untested route impossible or any untested dependency mandatory;
  (d) state the exact minimal `.rda`/class fixture members, assays, sparse
  entries, intervals and donor joins, plus refusal cases; (e) name dependency
  assets, version compatibility, and acquisition/decoded/temporary/retained
  resource unknowns; (f) for any HEAD-control proposal, account separately for
  workload, supervisor, Docker client, Linux guest and host, and verify
  single-deadline and bounded-output assumptions against the actual helper code.
- Expected output: a route/decision table (minimal R vs author export vs
  Python/interchange) with prerequisites, unknowns and a smallest decisive check,
  plus the fixture spec and a bounded resource ledger.
- Acceptance check: every route claim cites official docs/source or local code;
  no RAM inferred from compressed size; no promise of partial workspace loading
  from a general format description; proposed limits, configured flags, sampled
  usage and demonstrated enforcement are kept as distinct evidence types.
- Dependencies: public docs/author code + local inspection only.
- Authority: public web/primary docs; no install, container or payload.
- Stop condition: if no untested route can be rejected or accepted without an
  install/launch, record the exact bounded check and dependency, and mark the
  reader path `RESOURCE_UNRESOLVED` rather than asserting impossibility.

**How either result changes the next decision.** If a minimal, documented reader
route exists with a small fixture and bounded decoded memory, the object-inspection
question becomes a concrete, reviewable E2-R task. If it does not, the object
route stays `RESOURCE_UNRESOLVED` and the paired path must rely on the frozen-region
recount, reinforcing the prospective amendment already implied by priority 5.

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
   interval convention; (c) the retained-barcode list per library; (d)
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
   - 46-library peak reconciliation (§5); needs scoped approval because it fetches
     43 dataset-adjacent supplementary files.
    - Scientific-value / RNA-only-fallback assessment: completed iteration 4
      (§3.9, disposition `CONDITIONAL`); no further action unless the Q22 fix or
      prospective amendment is reviewed.
    - Minimum reader/resource path (priority 4, now the single next action, §5);
      official docs/author code + local inspection only.
   - External-cohort provenance pass: completed to the metadata/count-stage level
     (§3.8); re-open only to request the author QC rule/barcode artifact.
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
- Earlier-campaign dossier worktree `p22-research-campaig-b057f9` is now complete:
  iteration 4 reads HEAD `b64ba07`, SHA-256
  `c0d6206f81edea661d7ca22c66de138a8103cbeb4ec55e7fabb7fe673db37487`, with R1–R8
  bodies present (the earlier iterations saw `7e37ceb` and `b40458f`). Its R1–R6
  are treated as `RECORDED_PREVIOUSLY`; R7/R8 were re-read and their consequential
  claims (donor counts, margin arithmetic, `NAMED_BASELINES` gap, R6 citation
  correction) re-verified locally this run.
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

Reused without re-fetch: earlier dossier S1–S42 (local canonical docs, saved Vuong
XML/NeMO metadata, pinned author tables). Search coverage iteration 1: author
source tree + 8 raw scripts, Signac primary docs, GEO listing, local annotation
files, local contract/plan/code. Search coverage iteration 2: GEO SOFT family
record, pinned `A_input` and `B02` tables, pinned B02 script and tree, local
contract/plan/code, earlier-campaign dossier (new HEAD). Search coverage iteration
3: local Vuong manuscript XML (QC/age/provider methods, data availability) and
local release metadata re-analysis; NeMO parent/open-collection pages; web search
for an author code repository (none found). No NeMO payload/count/fragment
re-fetch; no payload, object, fragment or matrix reads; no author contact; no
payload GET (only the local saved XML, local metadata tar and author-repo
CSVs/scripts). Search coverage iteration 4: local paired-model/estimand code
(`estimand.py`, `multiome_runner.py`, `multiome_final.py`, `multiome_protocol.py`,
`named_baselines.py`, tests) and six primary method sources reopened on the web
(S50–S52, S55–S60 subset; N26–N30). No payload, install, container or training.

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
- Iteration 4 (this pass): priority 5 resolved to `CONDITIONAL` (§3.9) — the
  primary contrast is implemented in the runner (`multiome_final.py:190`), the
  frozen estimand omits its two arms (Q22), and six primary sources were reopened
  with two corrections (S52 preprint/conditional, S60 cannot score early-fusion
  cross-attention). Single next action moved to priority 4.
- Next iteration: priority 4 (minimum reader/resource path), then priority 6
  (finalize the decision/handoff) and priority 2 (full 46-library peak
  reconciliation, still needing scoped approval).
- Stop condition: not met. Priority 4 lacks a supported disposition in this
  handoff; priority 2's full reconciliation remains an approval-gated bounded
  check. `should_fully_stop=false`.

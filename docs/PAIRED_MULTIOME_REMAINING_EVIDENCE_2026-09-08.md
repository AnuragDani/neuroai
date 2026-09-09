# Remaining paired-multiome evidence: bounded source check

Checked 2026-09-08. Public metadata and methods only; no model fitting, count-matrix
download, controlled access, author contact, approval change, or exclusion applied.

## Result

Two gaps narrowed substantially; neither is a completed external-validation run.

| Gate | New evidence | Current status |
|---|---|---|
| NeMO release count | Exactly 3,731 metadata rows have RNA annotation `Unk`; the other rows total 113,801 | Exact candidate reconciliation, not verified author exclusion or complete QC replay |
| Specimen provenance | Author methods name UCLA cores and NIH NeuroBioBank; metadata gives 18 UCLA and 8 NIH donors | Documented provider-level separation from Lattke/HDBR; no overlap evidence found, specimen-level non-overlap not independently certified |
| Common measured ATAC regions | Both authors describe study-specific peak calling; Lattke source explicitly recounts fragments | No cross-cohort common-count release established; confirmatory compatibility remains pending |

## 1. NeMO count difference has a precise candidate explanation

The [author manuscript](https://pmc.ncbi.nlm.nih.gov/articles/PMC13225313/) reports
113,801 retained nuclei. The already-pinned public metadata contains 117,532 rows.
Its RNA annotations give the following exact partition:

| Metadata selection | Cells | Control cells | Ts21 cells | Control donors | Ts21 donors |
|---|---:|---:|---:|---:|---:|
| All rows | 117,532 | 61,656 | 55,876 | 13 | 13 |
| `class == "Unk"` | 3,731 | 2,107 | 1,624 | 13 | 13 |
| `class != "Unk"` | 113,801 | 59,549 | 54,252 | 13 | 13 |

`class == "Unk"` and `cluster.ids == "Unk"` identify exactly the same rows.
Every donor remains after this candidate filter; the smallest donor retains 273
cells. This is a deterministic annotation-based reconciliation, not deletion of
an arbitrary number of cells. It is **not yet proof that this was the authors'
final exclusion rule**: the retrieved methods do not explicitly identify `Unk`
as the reason for the reported count.

Do not substitute the WNN annotation: `cluster.ids.wnn == "Unk"` identifies only
728 rows. Of those, 663 overlap RNA `Unk` and 65 do not. `class.wnn` has no `Unk`
category. RNA and WNN inclusion masks therefore are not interchangeable.

### Additional QC caveat

Methods describe RNA counts above 200 with a donor-relative upper cutoff, ATAC
fragment counts above 100, and tissue mitochondrial percentage below 5.
[Source: quality-control methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC13225313/).

The current metadata does not directly reproduce those thresholds:

| Current metadata | `nCount_ATAC <= 100` | `percent.mt >= 5` | Either condition |
|---|---:|---:|---:|
| All rows | 1,798 | 7 | 1,805 |
| RNA non-`Unk` rows | 1,751 | 6 | 1,757 |

No row has `nCount_RNA <= 200`. These diagnostics do not establish that the paper
is wrong: the current ATAC column may refer to a different counting stage or
region set, and the release may differ. Those are possible explanations, not
verified facts. Do not silently reinterpret this column as the original QC
fragment total, re-estimate the original donor cutoff from a filtered release,
or claim the 113,801 candidate rows all pass reproduced QC.

**Acceptance still needed:** an author-defined final barcode list, an explicit
source-code exclusion rule, or equivalent archive documentation connecting the
release to the final RNA/ATAC analysis. Until then, report
`ANNOTATION_COUNT_MATCH_QC_UNVERIFIED`; do not promote this diagnostic to M1/M8
scientific acceptance.

## 2. Tissue providers are now documented

Vuong's sample-acquisition methods name the UCLA Gene and Cell Therapy Core,
UCLA Translational Pathology Core Laboratory, and NIH NeuroBioBank repository.
[Source: sample-acquisition methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC13225313/).

The downloaded metadata's `source` field is invariant within each donor:

| Source | Donors | Control donors | Ts21 donors | All cells | RNA non-`Unk` cells |
|---|---:|---:|---:|---:|---:|
| `UCLA` | 18 | 8 | 10 | 74,346 | 71,387 |
| `NIH_NBB` | 8 | 5 | 3 | 43,186 | 42,414 |

`condition`, `source`, `gw`, `sex`, and `ancestry` each have one value per donor.
The NIH donors are `NIH1031`, `NIH1089`, `NIH1139`, `NIH1152`, `NIH1329`,
`NIH1644`, `NIH1883`, and `NIH908`. The other 18 donor identifiers are UCLA
records. No public crosswalk to HDBR specimens was found in these sources.

Lattke's fresh-frozen fetal multiome tissue came from the UK Human Developmental
Biology Resource, project 200585. Its separate Zagreb fixed-tissue material is
not the multiome donor source. [Source: fetal-tissue methods](https://www.nature.com/articles/s41591-026-04211-1).

**Conclusion:** `no_overlap_evidence`, supported by different documented
procurement providers and the previously checked distinct donor IDs. This is
stronger than the former donor-name-only check. It is not a genetic identity
check or an author-certified specimen crosswalk; the NIH source field does not
identify each original collection site. An unqualified claim of independently
verified specimen non-overlap would still overstate this evidence.

## 3. Existing common-count objects do not yet solve the feature contract

Vuong methods describe GRCh38 2024-A-2.0.0 alignment, merged-fragment MACS2 peak
calling, blacklist removal, and a resulting nucleus-by-peaks matrix.
[Source: preprocessing and integration methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC13225313/).
That supports a study-level shared matrix, not identical measured intervals in
Lattke or a fixed reference established independently of all development donors.

The [pinned Lattke peak-quantification script](https://github.com/lattkem1/Down_Syndrome_Multiome/blob/227f51b4e63c6a7d9c73be44f06ab21ac11e45ba/F_Chromatin_scMEGA_GRN_analysis_exc_lin_from_all_non_cx_excl_v045_scripts/F01_v045_seur_call_quant_peaks_by_cluster.R)
explicitly calls peaks by `cluster_name`, then uses
`FeatureMatrix(fragments = Fragments(seur), features = peaks, cells = colnames(seur))`
and creates a `peaks_by_cluster` assay. Its output is
`F01_seur_w_peaks_by_cluster_quant.rda` in an author-local directory. The checked
[public source tree](https://api.github.com/repos/lattkem1/Down_Syndrome_Multiome/git/trees/227f51b4e63c6a7d9c73be44f06ab21ac11e45ba?recursive=1)
is complete (`truncated: false`) but does not contain that count checkpoint.

The [GEO supplementary listing](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE305nnn/GSE305146/suppl/)
does list two processed objects:

- `GSE305146_seur_integr_labelled_complete_dataset.rda.gz` (listing: 8.7G).
- `GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz` (listing: 7.6G).

Neither was downloaded or inspected here. Their names alone do not prove that
they contain the later `peaks_by_cluster` assay, compatible counts, or an external
common feature space. A published object can close within-study measurement
gaps without closing cross-study compatibility or training-only peak-selection
requirements. Downloading either whole object is outside this check's 20 MB cap.

The [NeMO ATAC directory](https://data.nemoarchive.org/other/grant/r21_delatorre/delatorre/multimodal/sncell/10xMultiome_ATACseq/human/processed/counts/)
lists the DSdevctx ATAC MEX and fragment archive, but no separate small fixed-
region count object. The inspected raw GEO peak-list mismatch remains as
documented in [the existing audit](PAIRED_MULTIOME_AUDIT.md).

**Next actionable input:** establish the exact assays in a provider-documented
common-count checkpoint and compare measured region/count semantics; otherwise
scope an exact fragment recount on frozen regions with measured disk/network
budgets. A different GPU cannot resolve missing measurements or provenance.

## Verification record

- Public [RNA child collection](https://assets.nemoarchive.org/collection/nemo:col-mbgxwtz)
  and [ATAC child collection](https://assets.nemoarchive.org/collection/nemo:col-ad8t52b)
  are described as open processed releases. Parent collection remains restricted
  because it also contains controlled data. No redistribution permission inferred.
- Repeated direct public NeMO manifest download failed TLS with curl exit 35;
  cached directory/collection listings remained readable. No matrix downloaded.
- PMC article HTML returned a browser challenge. The documented
  [NCBI E-utilities route](https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=13225313)
  returned the actual manuscript XML with DOI `10.1126/science.aea1259`.
  Saved locally as `data/multiome/Vuong_PMC13225313_efetch_20260908.xml`:
  467,378 bytes; SHA-256
  `7e58d9f00c3e7132145aa4903661f33be3f265b9c9b6712389c1a1eac1af005d`.
- Supplementary Table S1 request returned a browser-challenge HTML page, not an
  Excel workbook; it was not parsed as data or used as evidence. Response retained
  as `data/multiome/Vuong_Table_S1_20260908.failed.html`. No challenge bypassed.
- Metadata source remains
  `data/multiome/VuongWeber_DSdevctx_metadata.tar`, SHA-256
  `72cf7284663aeaee76ed3bab16ce0b414faf82847a883e946e7c2afab21b1526`.
  Selected CSV member:
  `VuongWeber_2025_DSdevctx_metadata_20260128/VuongWeber_2025_DSdevctx_metadata_20260128.csv.gz`.
- Sorted RNA non-`Unk` original cell IDs, joined by newline without a trailing
  newline, SHA-256:
  `0de060f67ab7d355e90766ab81168929260b3ce43d663b27d53f82c47f5ff9d6`.
  Corresponding excluded-ID hash:
  `30a274ee9f17278c1f4f020b1cf3bf2889a3b89c0733746f066ebd5f96749d16`.

Reproduce the new metadata checks without expression or ATAC matrices:

```bash
.venv-p22/bin/python - <<'PY'
import hashlib
import tarfile
from pathlib import Path
import pandas as pd
from p22.data.census import sha256_file

path = Path('data/multiome/VuongWeber_DSdevctx_metadata.tar')
assert sha256_file(path) == '72cf7284663aeaee76ed3bab16ce0b414faf82847a883e946e7c2afab21b1526'
member = ('VuongWeber_2025_DSdevctx_metadata_20260128/'
          'VuongWeber_2025_DSdevctx_metadata_20260128.csv.gz')
with tarfile.open(path) as archive:
    frame = pd.read_csv(archive.extractfile(member), compression='gzip')
assert frame['Unnamed: 0'].is_unique
unknown = frame['class'].eq('Unk')
assert unknown.equals(frame['cluster.ids'].eq('Unk'))
retained = frame.loc[~unknown]
assert (len(frame), int(unknown.sum()), len(retained)) == (117532, 3731, 113801)
assert retained.groupby('condition').donor.nunique().to_dict() == {'Ctrl': 13, 'Ts21': 13}
assert (frame.groupby('donor')[['condition', 'source', 'gw', 'sex', 'ancestry']].nunique() == 1).all().all()
assert frame.drop_duplicates('donor').source.value_counts().to_dict() == {'UCLA': 18, 'NIH_NBB': 8}
assert int((retained.nCount_ATAC <= 100).sum()) == 1751
assert int((retained['percent.mt'] >= 5).sum()) == 6
digest = hashlib.sha256('\n'.join(sorted(retained['Unnamed: 0'])).encode()).hexdigest()
assert digest == '0de060f67ab7d355e90766ab81168929260b3ce43d663b27d53f82c47f5ff9d6'
print('Candidate count reconciliation and provider/QC checks passed; scientific acceptance not implied.')
PY
```

Research skill used to restrict findings to primary sources and preserve exact
reproducible evidence; caveman skill used for concise task updates.

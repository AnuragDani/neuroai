# Paired multiome audit: implemented first stage

Updated: 2026-09-08. Scope of this audit: public-file diagnostics and reusable ingestion
code. It performs no training, external predictive evaluation, or approval changes.
The subsequent [synthetic neural-network implementation](PAIRED_MULTIOME_TRAINING.md)
is a separate verified development stage.

## Run

From the repository root, using the existing environment:

```bash
.venv-p22/bin/python scripts/audit_multiome.py \
  --manifest configs/paired_multiome_audit.json \
  --output-dir reports/generated/multiome/audit_next \
  --cell-cap 256 \
  --max-input-bytes 1700000000 \
  --max-expanded-bytes 268435456 \
  --max-nnz 10000000
```

Inputs are already present under the ignored `data/multiome/` and `data/real/` directories on this machine. On another machine, obtain the public files named in [the manifest](../configs/paired_multiome_audit.json), preserve their names, and verify the pinned hashes. GEO URLs point directly to files; the NeMO URL identifies the source collection. The command never downloads data or requests controlled access.

The explicit 1.7 GB input budget includes streaming the 1.57 GB H5AD checksum;
only its identity columns are materialized, not its expression matrix. The default
64 MiB limit remains suitable for tiny fixtures and will refuse this full manifest.

Use a new output directory for each run. Existing directories are refused. Exit code `0` means the file audit completed, **not** that training is permitted. Invalid inputs produce exit code `2` and a failure report when the output directory can be created.

Outputs are `audit.json`, `SUMMARY.md`, and an exact `manifest.json` snapshot. The snapshot retains paths relative to the original manifest directory; restore it under `configs/` for replay. The report also records resolved input paths, hashes, command, sample fingerprint, and resource measurements.

## What works

- GEO SOFT parsing maps RNA/ATAC accession pairs to 46 libraries and preserves donor, condition, age, and author inclusion flags.
- Metadata validation rejects duplicate library/barcode identities, missing identities, unknown labels, and conflicting donor labels. Multiplexed libraries remain valid.
- Age normalization preserves raw values and documented units. Ambiguous units remain unresolved. The age sensitivity reports donors per class, not cell-based sample size.
- The sparse loader handles combined RNA+ATAC MEX and separate modality MEX. It supports two-/three-column features and six-column ARC features, preserving unmapped RNA coordinates explicitly.
- Paired matrices require identical ordered barcodes and an exact metadata join. The existing donor-level sampling helper keeps the selected cells matched.
- Local files require pinned hashes and byte budgets. Archives are read without extraction. Outer decompression is bounded before PAX/GNU headers are parsed. Invalid matrix dimensions, values, duplicates, and excessive entry counts fail.
- The peak-space gate never turns unmeasured regions into zeros. `PASS` refers only to the supplied feature contract, never to scientific readiness or training approval.

The loader buffers bounded files before sparse parsing. It is **not** a full-atlas streaming loader. Expansion limits include archive headers and nested decoded layers, not total process RAM. Large NeMO matrices, Seurat objects, and fragment recounting need separate measured budgets. No new dependency was added.

## Measured public-file results

Primary retained-pilot evidence: [audit summary](../reports/generated/multiome/audit_20260908_retained/SUMMARY.md), [full audit](../reports/generated/multiome/audit_20260908_retained/audit.json).
The subsequent [author-reconciled audit](../reports/generated/multiome/audit_20260908_author_reconciled/audit.json)
adds the pinned author filtered-library table below.

| Check | Observed result | Meaning |
|---|---|---|
| GEO library mapping | 46 libraries, 37 donor identifiers; final-analysis flags include 41 libraries and 33 donors | Flags alone do not reproduce the published 30-donor cohort |
| NeMO metadata | 117,532 cells, 26 donors, 13 per class | The 3,731-cell difference from the paper remains unresolved |
| NeMO age sensitivity | 8 control and 10 trisomy-21 donors at canonical PCW 13–20 | Before new QC exclusions; not a power guarantee |
| B17C2L sparse pilot | 652 raw cells; 550 retained; 256 selected from retained cells; 36,601 RNA features and 22,676 ATAC features | One donor, final-release identity join; not a trained model |
| B17C2L versus B10C1Q | Zero exactly shared intervals across 22,676 and 46,672 peak regions | These matrices cannot provide a shared exact peak subset as supplied |
| Pilot resources | 2.286 seconds; 0.5834 GB process peak RSS; 1,582,111,901 input bytes including streamed H5AD hash | This bounded audit on this machine, not an estimate for full training |

Separate read-only cross-check of the existing CELLxGENE H5AD found 248,998 cells and 30 donors. Three GEO final-flag donor IDs are absent: `PCW10_DS_17630`, `PCW11_CON_14674`, and `PCW12_CON_14550`. All 30 H5AD donor IDs occur among the GEO flagged donors. This identifies the differing set; it does not establish why the releases differ or authorize arbitrary exclusions.

The first pilot used B10D1N, whose donor is among those absent from the final H5AD. Its [original report](../reports/generated/multiome/audit_20260905/SUMMARY.md) remains preserved as a raw-file test. The replacement pilot uses B17C2L, whose donor is present in that H5AD. Its donor has 2,450 retained cells, including 550 from B17C2L. The current command applies the exact retained-barcode join before capping.

### Follow-up: exact retained-cell identity check

Read-only inspection now verifies that all **550** final-release B17C2L cell IDs
match `B17C2L_` plus an exact raw barcode. No retained cell is missing from the raw
list; **102 of 652** raw cells are not retained. The retained donor is
`PCW17_CON_14310`. This establishes the one-library ID mapping, not the reason for
exclusions, the complete cohort's release history, or a new QC policy. The audit
now applies this mask, rejects missing retained cells or mismatched donor/condition
labels, and records retained counts for all 46 GEO libraries. Full raw-file coverage
and per-cell QC reproduction remain pending. The subsequent source-table check
below reconciles the final library/donor membership.

### Author-defined final cohort, checked 2026-09-08

The [author's downstream filtered table](https://github.com/lattkem1/Down_Syndrome_Multiome/blob/227f51b4e63c6a7d9c73be44f06ab21ac11e45ba/B_basic_analysis/B02_gr_tab_filtered_non_cx_excl.csv)
has exactly the final H5AD's 37 libraries and 30 donors. Every library's donor and
condition agree. This table is an input to the author's
[non-cortical subsetting step](https://github.com/lattkem1/Down_Syndrome_Multiome/blob/227f51b4e63c6a7d9c73be44f06ab21ac11e45ba/C_subsetting_all_cells_non_cx_excl_scripts/C01_v040_subsetting_reintegration.R).
Use that downstream release membership, not GEO's broader inclusion flags, to
define the cohort. The audit now checks this automatically and rejects mismatches.

Pinned source commit: `227f51b4e63c6a7d9c73be44f06ab21ac11e45ba`.
Table: 6,304 bytes; SHA-256 `7f2113cf235795ab1f06a9999069a25b1c713d42f3c1dc913df3bcd8f59c412c`.
Latest audit: 2.021 seconds, 0.5671 GB peak RSS, 1,582,118,205 input bytes.
This is membership reconciliation, not a replay of every original QC decision.
The author's per-cell/library QC script and local Seurat checkpoint names were
inspected; no downloadable shared-region count checkpoint was established from
those scripts. Raw per-library peak unions remain invalid for exact comparison.

NeMO's [public RNA](https://data.nemoarchive.org/other/grant/r21_delatorre/delatorre/multimodal/sncell/10xMultiome_RNAseq/human/processed/counts/)
and [ATAC](https://data.nemoarchive.org/other/grant/r21_delatorre/delatorre/multimodal/sncell/10xMultiome_ATACseq/human/processed/counts/)
listings were rechecked. A direct manifest request failed TLS; count packages were
not fetched in this increment. No evidence was found here resolving the 3,731-cell
release discrepancy or specimen-level independence. Those are pending, not failed
biological replication. No controlled access requested and no authors contacted.

Pinned H5AD SHA-256: `08d6eff265db6e6a2e1c4a259153588f3dba3c51f5f754736dc63c28795fcdbb`.
Raw-barcode hash remains the value in [the audit manifest](../configs/paired_multiome_audit.json).
Sorted retained IDs joined by newline hash to
`855b64ed34fa487f99306c337077c29ab5ad8c0c6b2f004162ac92016f5a75c7`.
The final H5AD contains 37 nonempty libraries across its 30 donors.

Reproduce without loading expression/ATAC matrices:

```bash
.venv-p22/bin/python - <<'PY'
import gzip
from pathlib import Path
import h5py
import numpy as np
from p22.data.census import sha256_file

path = Path('data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad')
assert sha256_file(path) == '08d6eff265db6e6a2e1c4a259153588f3dba3c51f5f754736dc63c28795fcdbb'
with h5py.File(path) as handle:
    obs = handle['obs']
    category = np.flatnonzero(obs['library/categories'].asstr()[:] == 'B17C2L')[0]
    rows = np.flatnonzero(obs['library/codes'][:] == category)
    retained = set(obs['cell_id'].asstr()[rows])
with gzip.open('data/multiome/GSE305146_B17C2L_barcodes.tsv.gz', 'rt') as stream:
    raw = {'B17C2L_' + line.strip() for line in stream}
assert len(retained) == 550 and len(raw) == 652 and retained <= raw
print({'retained': len(retained), 'raw_only': len(raw - retained)})
PY
```

## Verification

```bash
.venv-p22/bin/python -m pytest -q tests/test_multiome.py tests/test_atac_features.py
make lint
make test-all
```

Latest verification: 43 multiome ingestion tests passed; 576 full-suite tests passed;
lint and formatting passed. The full suite retains 19 existing scikit-learn warnings
from synthetic end-to-end tests. Tests cover both MEX layouts, malformed counts,
archive expansion attacks, ambiguous ages, valid multiplexing, output preservation,
retained-cell joins, author release reconciliation and failure reports. Independent
review found the documented audit byte budget needed updating for the H5AD checksum;
that was corrected. No required findings remain in the reviewed increments.

## What remains

Follow [the development checklist](../tasks/todo.md). The audit does not complete
M1–M4 scientific acceptance. Reusable M5–M8 training/comparison code has since advanced
through synthetic verification; accepted real-data protocol and execution remain pending.

1. Extend the verified final-release barcode join beyond the one-library pilot. Author library/donor membership is now reconciled; full raw-file coverage is not.
2. Explain NeMO's release/QC difference and complete the cross-study specimen audit.
3. Inspect an author-provided common-count object or budget exact counts on frozen regions. Do not use peak overlap as an exact projection.
4. Establish count semantics and genome-build provenance for the chosen representation.
5. Record professor approval and freeze the donor-level protocol before condition-specific training.

The existing synthetic safeguards, approval record, historical results, and user
notebook changes remain untouched. Neural-network code and synthetic training are
now documented in [the training guide](PAIRED_MULTIOME_TRAINING.md). They do not
resolve this audit's outstanding real-data gates.

Implementation references: [Python archive streams](https://docs.python.org/3.11/library/tarfile.html#tarfile.TarFile.extractfile), [SciPy Matrix Market reader](https://docs.scipy.org/doc/scipy/reference/generated/scipy.io.mmread.html), [10x feature matrices](https://www.10xgenomics.com/support/software/cell-ranger-arc/latest/analysis/feature-barcode-matrices), and [Signac peak-merging limitations](https://stuartlab.org/signac/articles/merging).

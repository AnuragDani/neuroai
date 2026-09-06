# Paired multiome audit: implemented first stage

Date: 2026-09-05. Scope: public-file diagnostics and reusable ingestion code. No model training, external predictive evaluation, or approval changes.

## Run

From the repository root, using the existing environment:

```bash
.venv-p22/bin/python scripts/audit_multiome.py \
  --manifest configs/paired_multiome_audit.json \
  --output-dir reports/generated/multiome/audit_next \
  --cell-cap 256 \
  --max-input-bytes 67108864 \
  --max-expanded-bytes 268435456 \
  --max-nnz 10000000
```

Inputs are already present under the ignored `data/multiome/` directory on this machine. On another machine, obtain the public files named in [the manifest](../configs/paired_multiome_audit.json), preserve their names, and verify the pinned hashes. GEO URLs point directly to files; the NeMO URL identifies the source collection. The command never downloads data or requests controlled access.

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

Primary evidence: [audit summary](../reports/generated/multiome/audit_20260905_retained_donor/SUMMARY.md), [full audit](../reports/generated/multiome/audit_20260905_retained_donor/audit.json).

| Check | Observed result | Meaning |
|---|---|---|
| GEO library mapping | 46 libraries, 37 donor identifiers; final-analysis flags include 41 libraries and 33 donors | Flags alone do not reproduce the published 30-donor cohort |
| NeMO metadata | 117,532 cells, 26 donors, 13 per class | The 3,731-cell difference from the paper remains unresolved |
| NeMO age sensitivity | 8 control and 10 trisomy-21 donors at canonical PCW 13–20 | Before new QC exclusions; not a power guarantee |
| B17C2L sparse pilot | 652 raw cells; 256 selected; 36,601 RNA features and 22,676 ATAC features | One donor, file-level pairing only; not a trained model |
| B17C2L versus B10C1Q | Zero exactly shared intervals across 22,676 and 46,672 peak regions | These matrices cannot provide a shared exact peak subset as supplied |
| Pilot resources | 0.72 seconds; 0.372 GB process peak RSS; 12,453,041 input bytes | This bounded audit on this machine, not an estimate for full training |

Separate read-only cross-check of the existing CELLxGENE H5AD found 248,998 cells and 30 donors. Three GEO final-flag donor IDs are absent: `PCW10_DS_17630`, `PCW11_CON_14674`, and `PCW12_CON_14550`. All 30 H5AD donor IDs occur among the GEO flagged donors. This identifies the differing set; it does not establish why the releases differ or authorize arbitrary exclusions.

The first pilot used B10D1N, whose donor is among those absent from the final H5AD. Its [original report](../reports/generated/multiome/audit_20260905/SUMMARY.md) remains preserved as a raw-file test. The replacement pilot uses B17C2L, whose donor is present in that H5AD. Its donor has 2,450 retained cells, including 550 from B17C2L. The current pilot still samples the 652 raw MEX cells; a final retained-barcode join remains necessary.

## Verification

```bash
.venv-p22/bin/python -m pytest -q tests/test_multiome.py tests/test_atac_features.py
make lint
make test-all
```

Results: 51 focused tests passed; 529 full-suite tests passed; lint and formatting passed. The full suite retains 19 existing scikit-learn warnings from synthetic end-to-end tests. Tests cover both MEX layouts, malformed counts, archive expansion attacks, ambiguous ages, valid multiplexing, output preservation, and failure reports. An independent code review found archive-budget and validation defects; regression tests reproduced them before fixes. All required review findings were then closed.

## What remains

Follow [the development checklist](../tasks/todo.md). The first audit stage does not complete M1–M4 scientific acceptance, and M5–M8 remain pending.

1. Reconcile the final training donor/cell set and pin its retained-barcode mapping.
2. Explain NeMO's release/QC difference and complete the cross-study specimen audit.
3. Inspect an author-provided common-count object or budget exact counts on frozen regions. Do not use peak overlap as an exact projection.
4. Establish count semantics and genome-build provenance for the chosen representation.
5. Record professor approval and freeze the donor-level protocol before condition-specific training.

The existing synthetic safeguards, approval record, historical results, and user notebook changes remain untouched. Neural-network implementation and training remain later gated tasks, not completed deliverables of this slice.

Implementation references: [Python archive streams](https://docs.python.org/3.11/library/tarfile.html#tarfile.TarFile.extractfile), [SciPy Matrix Market reader](https://docs.scipy.org/doc/scipy/reference/generated/scipy.io.mmread.html), [10x feature matrices](https://www.10xgenomics.com/support/software/cell-ranger-arc/latest/analysis/feature-barcode-matrices), and [Signac peak-merging limitations](https://stuartlab.org/signac/articles/merging).

# Development ATAC fragment join validation — 2026-09-21

Status: **development indexed-fragment route validated at the barcode/index gate**.
This is a bounded header/prefix measurement, not a paired experiment.

## What was executed

Command:

```
.venv-p22/bin/python scripts/validate_fragment_join.py \
  --out reports/generated/atac_fragment_join_20260921/dev_fragment_join.json
```

Asset: CELLxGENE complete-dataset ATAC fragment
`https://datasets.cellxgene.cziscience.com/46b43994-2af5-4359-bf75-3314a0d3a7a5-fragment.tsv.bgz`
and its `.tbi`. Only HEAD plus a 2 MiB Range GET of the fragment and a 512 KiB
Range GET of the index were read. No payload body, no whole-asset transfer.

## Result

| Check | Observed | Verdict |
|---|---|---|
| Fragment transfer | HTTP 200; `Content-Length` 25,514,837,002; `Accept-Ranges: bytes` | accessible, rangeable |
| Index transfer | HTTP 200; `Content-Length` 5,339,155; `Accept-Ranges: bytes` | accessible, rangeable |
| Fragment encoding | BGZF magic `1f8b` | bgzf |
| Barcode convention | every observed barcode matches `<library>_<barcode>-1` | library-prefixed |
| Barcode join | 3,430 unique observed barcodes; 3,430 in the 248,998-cell H5AD `cell_id` allowlist; 0 unknown | complete coverage on the sampled block |
| Interval columns | 5-column `chrom start end barcode count`; 0 malformed rows; 0 nonpositive counts | valid |
| Index format | tabix magic `TBI\1`; `format=65536`; `col_seq=1, col_beg=2, col_end=3`; `n_ref=39` | standard tabix over the same bgzf stream |

Sampled text = first 200,000 decoded bytes (3,929 rows). Evidence:
`reports/generated/atac_fragment_join_20260921/dev_fragment_join.json`.

## What this establishes, and what it does not

- `verified`: the development fragment is an open, range-readable bgzf TSV whose
  barcode column uses the same `<library>_<barcode>-1` namespace as the H5AD
  `cell_id` obs index, and it carries a standard tabix index. This clears the
  barcode-join and index-format gate that the ATAC feasibility handoff left open
  for the development indexed-fragment route.
- `verified`: `Content-Length` and `Accept-Ranges` for both assets, matching the
  provider inventory (25,514,837,002 / 5,339,155 bytes).
- `unknown` (unchanged): full barcode coverage over all 25.5 GB; the exact count
  unit and dedup rules a quantifier would apply; the training-fold-only region
  set; genome-build/interval acceptance of any candidate common region set.
- `unknown` (unchanged): the external cohort route. Its ATAC counts MEX and
  fragment live inside a `.tar.gz`/`.tar`, so no bounded range join was performed.
  The external route remains unvalidated at this gate.
- `not established`: this is not a paired pilot, not a count matrix, and not
  evidence that a common measured region set exists. Full-fragment coverage and
  the actual quantification still require their own bounded allocation.

## Reproduce

```
.venv-p22/bin/python scripts/validate_fragment_join.py \
  --out reports/generated/atac_fragment_join_20260921/dev_fragment_join.json
.venv-p22/bin/python -m pytest tests/test_validate_fragment_join.py -q
```

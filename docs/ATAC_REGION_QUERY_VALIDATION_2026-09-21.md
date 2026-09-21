# Development ATAC fragment: bounded remote tabix region-query validation

Date: 2026-09-21 · Run: `p22-results-executio-debda8` · Status: **PASS** (mechanism)

## What this proves

`verified` — The development CELLxGENE ATAC fragment can be **randomly accessed
remotely** through its served `.tbi` index without downloading the 25.5 GB asset.
For each queried region the reader returns the overlapping fragment rows, joins
their library-prefixed barcodes against the 248,998-cell H5AD allowlist, and
records the exact bytes and requests used.

This is the enabling mechanism for the only viable development ATAC route
(fragment quantification on a frozen region set). It is **not** a scientific
feature contract and not a paired result: the region set must still be frozen
from a fixed reference annotation or the training fold before the counts enter
a comparison.

## Independent ground-truth cross-check

The indexed whole-contig query for the first contig was compared with an
independent decode of a bounded prefix that contains the whole contig:

| Quantity | Value |
|---|---|
| Prefix request | `Range: bytes=0-262143` (262,144 B), SHA-256 `bdb06b9f…33d9f3` |
| Prefix decoded bytes | 1,078,125 |
| Prefix `GL000009.2` rows | 13,270 |
| Indexed query `GL000009.2:0-300000` rows | 13,270 |
| Match | `true` |

The `.tbi`'s chunk end for `GL000009.2` is compressed offset 159,550, so the
contig is fully inside the prefix. Two independent paths agree exactly.

## Real region queries

| Region | Rows | Unique barcodes | In allowlist | Unknown | Chunks | Requests | Bytes fetched |
|---|---:|---:|---:|---:|---:|---:|---:|
| chr21:33,000,000-33,100,000 | 167,973 | 82,546 | 82,546 | 0 | 14 | 21 | 5,505,024 |
| chr21:45,000,000-45,100,000 | 160,708 | 85,239 | 85,239 | 0 | 28 | 36 | 9,437,184 |
| chr1:1,000,000-1,100,000 | 459,976 | 145,108 | 145,108 | 0 | 62 | 79 | 20,709,376 |
| chr22:20,000,000-20,100,000 | 231,480 | 114,995 | 114,995 | 0 | 42 | 53 | 13,893,632 |
| chrX:10,000,000-10,100,000 | 78,893 | 53,407 | 53,407 | 0 | 28 | 32 | 8,388,608 |
| GL000009.2:0-300000 | 13,270 | 10,108 | 10,108 | 0 | 1 | 1 | 262,144 |

Every region joined with **zero unknown barcodes** (`join_complete: true`).
A sparse regions × cells counts matrix was produced: shape `6 × 248,998`,
`nnz = 491,403`, count unit `fragment_overlap_sum`, SHA-256
`bc5dc24b…2172ad` (`reports/generated/atac_region_query_20260921/counts/`).

Measured cost: ~5.5–20.7 MB transferred per 100 kb region (21–79 requests).
A 128-feature pilot over ~100 kb regions therefore needs roughly 1 GB of network
transfer, no whole-asset read, and no persistent fragment copy.

## Commands

```
# index (gzip-compressed .tbi, 5,339,155 B) and bounded prefix ground truth
curl -sS -o frag.tbi "<fragment-url>.tbi"
curl -sS -r 0-262143 -o frag_prefix.bin "<fragment-url>"

# real region queries + sparse counts matrix
PYTHONDONTWRITEBYTECODE=1 .venv-p22/bin/python scripts/query_fragment_regions.py \
  --index-path frag.tbi \
  --region chr21:33000000-33100000 --region chr21:45000000-45100000 \
  --region chr1:1000000-1100000 --region chr22:20000000-20100000 \
  --region chrX:10000000-10100000 --region GL000009.2:0-300000 \
  --counts-out reports/generated/atac_region_query_20260921/counts \
  --out reports/generated/atac_region_query_20260921/query.json

# offline regression tests
PYTHONDONTWRITEBYTECODE=1 .venv-p22/bin/python -m pytest tests/test_query_fragment_regions.py -q
```

## What remains unknown / next

- `unknown` — the frozen region set (fixed reference annotation or training-fold
  peaks) has not been selected; region choice drives feature compatibility.
- `unknown` — whether the summed fragment `count` column is the intended ATAC
  count unit for the accepted protocol (insertions vs fragments) needs a frozen
  decision before confirmatory use.
- `unknown` — the external NeMO cohort stays tar-packaged under per-file
  `embargo`; its fragments are not remotely index-readable.

Smallest next action: freeze a modest fixed-reference region set, query it for
the retained cells, and assemble the development ATAC matrix for a real paired
pilot (ingestion/splits/fit/artifacts), labeled a pilot.

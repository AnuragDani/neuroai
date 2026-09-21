# P22 results execution and professor handoff

Run: `p22-results-executio-debda8` · Worktree base `8217719713c271349d1e54eda679672b82133a56`
Updated: 2026-09-21 (iteration 2) · Maintained inside the GNHF worktree.

## 1. Current status and result

**Result first.** The completed RNA replication remains **INCONCLUSIVE** (all four
donor-bootstrap correlation intervals cross zero). The paired RNA+ATAC study is
**not yet executed**; no paired real-data fit has been run.

This iteration resolved one concrete input gate on the development path:

- `verified` — The development CELLxGENE ATAC fragment
  (`46b43994-…-fragment.tsv.bgz`, 25,514,837,002 B) is an open, range-readable
  **BGZF TSV** whose barcode column uses the same `<library>_<barcode>-1`
  namespace as the 248,998-cell H5AD `cell_id` obs index, and its `.tbi`
  (5,339,155 B) is a **standard tabix index** over the same stream.
- `verified` — On the sampled leading block (3,929 rows / 3,430 unique barcodes),
  **every** barcode resolved against the H5AD allowlist (0 unknown, 0 malformed
  rows, 0 nonpositive counts).
- `unknown` (unchanged) — full-archive barcode coverage, count unit/dedup rules,
  and the training-fold-only region set. External cohort route remains
  unvalidated because its payloads are packaged in tar/tar.gz.

This clears the **barcode-join and index-format gate** for the development
indexed-fragment route. It is not a paired pilot and not a count matrix.

Iteration 2 then cleared the next development gate — **remote random access**:

- `verified` — The fragment can be read by **bounded remote tabix region
  queries** through its served `.tbi`, without downloading the 25.5 GB asset.
  `scripts/query_fragment_regions.py` implements the BGZF/tabix random-access
  reader; a whole-contig indexed query (`GL000009.2:0-300000` → 13,270 rows)
  matches an independent bounded-prefix decode (13,270 rows) exactly.
- `verified` — Six real 100 kb regions across chr1/chr21/chr22/chrX and one small
  contig returned 0 unknown barcodes against the 248,998-cell allowlist
  (`join_complete: true` for all six) and produced a real sparse
  regions × cells matrix (6 × 248,998, nnz 491,403, unit `fragment_overlap_sum`).
- `verified` — Measured cost ≈ 5.5–20.7 MB transferred per 100 kb region
  (21–79 requests); a ~128-feature pilot needs roughly 1 GB of network and no
  whole-asset read or persistent fragment copy.

This proves the **only viable development ATAC mechanism** works on real data.
It is still not a paired pilot: the region set must be frozen from a fixed
reference annotation or the training fold before counts enter a comparison.

## 2. Delta from prior runs and execution/resource amendment

- Prior ATAC run (`p22-atac-access-and-b89c8a`, HEAD `f32077b`) completed research
  only: no payload, fragment or object was read. Its handoff named one next
  action — bounded barcode/index header validation — which this run executed.
- Iteration 1 files: `scripts/validate_fragment_join.py`,
  `tests/test_validate_fragment_join.py`,
  `docs/ATAC_FRAGMENT_JOIN_VALIDATION_2026-09-21.md`,
  `configs/results_execution_amendment_2026-09-21.json`.
- Iteration 2 files: `scripts/query_fragment_regions.py`,
  `tests/test_query_fragment_regions.py`,
  `docs/ATAC_REGION_QUERY_VALIDATION_2026-09-21.md`,
  `docs/atac_region_query_validation_2026-09-21.json`; generated evidence under
  `reports/generated/atac_region_query_20260921/`.
- Prospective amendment recorded in `configs/results_execution_amendment_2026-09-21.json`:
  public range/header acquisition and local execution for the approved study;
  no paid infra, no controlled access, no unbounded acquisition. Historical
  records (`plan/approvals.json`, the source contract, the Sept-8 evidence note)
  are preserved byte-for-byte.

## 3. Professor-direction coverage

| Direction | Source anchor | Executed evidence this run |
|---|---|---|
| Mathematical specificity / customization | Jul 2 [00:00],[01:10],[17:10]; Jul 21 [25:26] | Fail-closed validation script; adds only the missing ingestion gate, no architecture change |
| Meaningful biological question | Jul 2 [00:36],[18:06],[19:30],[20:51] | Disease benchmark preserved; no new endpoint claimed from headers |
| Clear conclusions, honest Tasic scope | Jul 21 [00:00],[07:52],[13:39] | RNA stays INCONCLUSIVE; header result labeled `verified`, not a biological finding |
| Independent modalities, simple fusion | Jul 21 [15:04],[15:55],[17:39] | Fragment join is a prerequisite to measured pairing; no fusion claim yet |
| Fair supervision / method selection | Jul 2 [14:12],[16:43]; Jul 21 [15:55] | No model comparison executed; frozen protocol untouched |
| Donor-aware sampling / held-out eval | Jul 21 [03:40], To-Dos 3–4 | No splits executed; donor keys confirmed library-prefixed |
| Faithfulness / seed variability | Jul 21 To-Do 10 | Not yet applicable (no fit) |
| Independent biological validation | Jul 21 [18:51],[20:19],[21:56] | None claimed |
| Check GenAI claims vs originals | Jul 2 [12:09], To-Do 8 | Schema and Signac primary sources inspected in the prior run; carried forward |
| Data access / approval | Jul 2 [03:10],[05:10],[06:46]; Sept attestation | Public open assets only; no restricted access, no contact |

## 4. Input acceptance evidence

| Fact | Value | Label |
|---|---|---|
| Fragment URL | `https://datasets.cellxgene.cziscience.com/46b43994-2af5-4359-bf75-3314a0d3a7a5-fragment.tsv.bgz` | verified |
| Fragment HEAD | 200; `Content-Length` 25,514,837,002; `Accept-Ranges: bytes`; ETag `afd8f4fa…-3042` | verified |
| Index HEAD | 200; `Content-Length` 5,339,155; `Accept-Ranges: bytes`; ETag `e283c582…` | verified |
| Barcode namespace | `<library>_<barcode>-1`, matches H5AD `cell_id` | verified |
| Sampled join | 3,430 unique / 3,430 in allowlist / 0 unknown | verified |
| Interval layout | `chrom start end barcode count`, 0 malformed, 0 nonpositive | verified |
| Index | tabix `TBI\1`; format 65536; cols 1/2/3; 39 contigs | verified |
| Range SHA-256 | fragment `bb8e9f55…`; index `845602ea…` (leading bytes only) | verified |
| Full-archive coverage | not measured | unknown |
| Count unit / dedup | quantifier-dependent | unknown |
| External route | tar/tar.gz + per-file embargo | unknown |
| Remote region access | whole-contig indexed query == prefix decode | verified (iter 2) |
| Region barcode join | 6 real regions, 0 unknown | verified (iter 2) |
| Frozen region set | not selected | unknown |

## 5. Implemented code, environment and tests

- `scripts/validate_fragment_join.py` — stdlib HEAD/Range/BGZF/tabix parser plus an
  optional H5AD allowlist reader; writes a JSON record. No whole-asset reads.
- `tests/test_validate_fragment_join.py` — 6 offline tests (BGZF truncation,
  interval/count parsing, tabix header round-trip and rejection, join coverage,
  injected-transport end-to-end).
- `scripts/query_fragment_regions.py` — remote BGZF/tabix random-access reader
  (`reg2bins`, chunk merge, linear-index filter, bounded window fetches) plus a
  sparse regions × cells counts writer. No whole-asset reads.
- `tests/test_query_fragment_regions.py` — 10 offline tests over a synthetic
  BGZF+tabix fixture (bin math, index round-trip raw/gzip, truncated-tail
  handling, overlap filtering, multi-block continuation, byte-cap refusal,
  region parsing, chunk merge, counts placement).
- Environment: `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python`
  (anndata 0.12.6, h5py 3.16.0, scipy 1.17.1) for the allowlist and matrix writes.

Commands actually run and status:

```
.venv-p22/bin/python -m pytest tests/test_validate_fragment_join.py -q   # 6 passed
.venv-p22/bin/python scripts/validate_fragment_join.py --out reports/generated/atac_fragment_join_20260921/dev_fragment_join.json  # status PASS
.venv-p22/bin/python -m pytest tests/test_query_fragment_regions.py -q   # 10 passed
.venv-p22/bin/python -m pytest -q -m "not slow"                          # 876 passed, 32 deselected
.venv-p22/bin/ruff check scripts tests && .venv-p22/bin/ruff format --check scripts tests  # pass
.venv-p22/bin/python scripts/query_fragment_regions.py --index-path <frag.tbi> \
  --region chr21:33000000-33100000 ... --counts-out <dir> --out <query.json>  # PASS
```

## 6. Pilot vs final vs historical results

- Historical (unchanged): RNA replication INCONCLUSIVE; 68 exploratory donor
  omissions preserved; synthetic paired fits and Colab RNA display only.
- This run: **input-gate validation** (iter 1) and a **remote-read mechanism
  proof with real region counts** (iter 2), not a pilot. No model was fit.
- Final paired estimate: **not produced**.

## 7. External evaluation and biological validation

External paired evaluation was **not launched**: no evaluation lock exists, the
external pairing/QC/common-feature gates are unresolved, and the external payloads
are tar-packaged with per-file embargo. No biological mechanism is claimed.

## 8. Artifact paths

- Evidence JSON (run output, gitignored dir): `reports/generated/atac_fragment_join_20260921/dev_fragment_join.json`
- Evidence JSON (tracked durable copy): `docs/atac_fragment_join_validation_2026-09-21.json`
- Tracked summary: `docs/ATAC_FRAGMENT_JOIN_VALIDATION_2026-09-21.md`
- Region-query evidence (run output): `reports/generated/atac_region_query_20260921/query.json` and `counts/` (npz + sidecar)
- Region-query evidence (tracked copy): `docs/atac_region_query_validation_2026-09-21.json`, `docs/ATAC_REGION_QUERY_VALIDATION_2026-09-21.md`
- Amendment: `configs/results_execution_amendment_2026-09-21.json`
- Code/test: `scripts/validate_fragment_join.py`, `scripts/query_fragment_regions.py`, matching tests

## 9. Unsent professor update

> Question: can accepted paired RNA+ATAC inputs support the planned multimodal
> comparison? Status: the RNA replication remains inconclusive; the paired study
> is not yet executed. Two development input gates are now cleared on real data:
> the ATAC fragment is open, library-prefixed and tabix-indexed so its barcodes
> join the 248,998-cell H5AD index; and the fragment can be read by bounded
> remote indexed region queries without downloading the 25.5 GB asset, with a
> whole-contig query matching an independent prefix decode and six real regions
> joining with zero unknown barcodes. Limitation: this is a read/join mechanism
> proof, not a paired recount or model fit, and the region set is not yet frozen.
> The external cohort's payloads remain tar-packaged under a per-file embargo.
> Outstanding decision: which fixed-reference or training-fold region set to
> freeze for the development ATAC matrix, and how to handle the external
> packaging/embargo.

## 10. Exact unresolved dependency and smallest next action

Unresolved: no **frozen region set** exists yet for the development ATAC matrix,
and the external route remains tar-packaged/embargoed.
Smallest unblocking action: freeze a modest fixed-reference (or training-fold)
region set, quantify it for the retained cells with the proven remote reader, and
assemble the development ATAC matrix for a real paired pilot (ingestion, splits,
fit, artifacts, interventions) labeled a pilot. External execution additionally
depends on resolving the tar packaging and per-file embargo.

## 11. Reproduce

```
.venv-p22/bin/python scripts/validate_fragment_join.py \
  --out reports/generated/atac_fragment_join_20260921/dev_fragment_join.json
.venv-p22/bin/python -m pytest tests/test_validate_fragment_join.py -q

curl -sS -o frag.tbi "<fragment-url>.tbi"
curl -sS -r 0-262143 -o frag_prefix.bin "<fragment-url>"
.venv-p22/bin/python scripts/query_fragment_regions.py --index-path frag.tbi \
  --region chr21:33000000-33100000 --region chr21:45000000-45100000 \
  --region chr1:1000000-1100000 --region chr22:20000000-20100000 \
  --region chrX:10000000-10100000 --region GL000009.2:0-300000 \
  --counts-out reports/generated/atac_region_query_20260921/counts \
  --out reports/generated/atac_region_query_20260921/query.json
.venv-p22/bin/python -m pytest tests/test_query_fragment_regions.py -q
```

# P22 corrected results and professor handoff

Status: **PARTIAL — measurement repair in progress.** This record is the live repair
log for the review of the seven GNHF execution commits
(`GNHF_P22_RESULTS_REVIEW.md`, reviewed HEAD
`fe881ea754c9da71588fd10fb6b33deeef52fc38`). It is updated in place as each review
finding is repaired and independently verified. No corrected internal estimate is
claimed yet; the old exploratory result is preserved unchanged and remains
superseded for scientific acceptance.

Worktree: `/Users/anuragdani/Github/niw-eb1a/P22-gnhf-worktrees/p22-results-executio-debda8`.

## Before / after input semantics

| Input | Old (exploratory, superseded) | Corrected declaration |
|---|---|---|
| ATAC overlap unit | read-support-weighted overlap (sum of column five, i.e. supporting read pairs including duplicates) | `unique_fragment_overlap`: one count per unique qualifying fragment record |
| ATAC reader | per-member line parsing; records split across BGZF members dropped; chunk-end virtual offset not enforced; unbounded `response.read()` | members concatenated before line splitting; chunk end virtual offset enforced; HTTP range verified and size-bounded; truncated/corrupt queries refused before matrix assembly |
| RNA representation | H5AD `X` labelled "raw counts" (actually noninteger processed values) | **not yet repaired** — `raw/X` selection and axis validation still pending |

The historical ATAC unit label `fragment_overlap_sum` in
`configs/final_internal_comparison_2026-09-21.json` and the old
`reports/generated/repeated_comparison_20260921/counts/counts.json` is inaccurate and
is preserved only as history. The corrected unit is declared prospectively in
`configs/atac_measurement_contract_2026-09-21.json`.

## Finding-to-evidence table

| Review finding | Regression test | Fix | Executed evidence | Remaining limitation |
|---|---|---|---|---|
| #2 ATAC read-support weighting | `tests/test_query_fragment_regions.py::test_query_region_returns_overlapping_rows`, `test_read_support_mode_reproduces_historical_weighting`; `tests/test_quantify_development_atac.py::test_quantify_regions_concurrent_matrix` | `parse_fragment_line` weights one per unique record in `count_mode="fragment"` (default); `read_support` retained for historical reproduction | `scripts/query_fragment_regions.py` audit case now yields `saved_count=1` for a support-7 fragment | Historical matrices still encode read-support weighting; they must be regenerated |
| #3a split record across two BGZF members | `tests/test_query_fragment_regions.py::test_record_split_across_two_members_is_one_record` | decompressed members concatenated into a pending-line buffer before splitting on newline | audit case now yields `observed_rows=1`, `truncated=false`; HTSlib oracle agrees | none observed offline |
| #3b chunk-end virtual offsets / duplicate emission | `test_fetch_window_beyond_chunk_end_adds_no_extra_counts`, `test_adjacent_and_overlapping_chunks_do_not_duplicate` | parse only bytes in `[start_voffset, stop_voffset)`; merged chunks prevent duplicate emission | tests pass | none observed offline |
| #3c unbounded HTTP range | `test_http_range_refuses_ignored_range`, `test_http_range_refuses_oversized_body_and_short_read`, `test_http_range_bounded_read_and_consistent_content_range`, `test_http_range_refuses_unsafe_redirect` | HTTP 206 + consistent `Content-Range` required, size-bounded read, oversized/short/unsafe refused | audit case now refused: "server did not honor byte range (HTTP 200)" | none observed offline |
| #3d partial matrix accepted | `tests/test_quantify_development_atac.py::test_quantify_regions_refuses_truncated_query` | `quantify_regions` raises `IncompleteQueryError` before matrix assembly unless `allow_partial` | audit case refused: "1 region(s) returned incomplete reads" | none observed offline |
| #3e zero-count region vs failure | `test_valid_zero_count_region_is_not_a_failure`, `test_quantify_regions_accepts_valid_empty_region` | `empty_region` flag; `join_complete = not truncated and no unknown barcodes` | tests pass; HTSlib oracle agrees on an empty region | none observed offline |
| #3f unknown barcodes / retained population | `test_quantify_regions_refuses_unknown_barcodes_by_default`, `test_quantify_regions_marks_unknown_barcodes` | unknown barcodes refused by default; explicit `unknown_policy="drop"` reports exclusions per region | tests pass | The real development run joined all observed barcodes; re-verify on regeneration |
| #3g aggregate transfer accounting | `test_quantify_regions_enforces_aggregate_budget` | `_BudgetedTransport` caps aggregate bytes across concurrent workers | test passes | Real-run byte allocation must be set before regeneration |
| #1 RNA `X` vs `raw/X` | pending | pending | audit: 100,000/100,000 `X` nonzeros noninteger; 0/100,000 `raw/X` nonzeros noninteger | Not yet repaired |
| #4 chromosome-1 feature bias | pending | pending (report correction) | audit: 163–219 of 256 regions per fold on chr1 | Not yet corrected in prose |
| Acceptance binding | pending | pending | `run_real_paired_comparison.py` still auto-promotes | Not yet repaired |

## Independent reader validation

The custom reader was checked against HTSlib (pysam 0.24.1) in an isolated
environment outside the shared venv, on locally generated fixtures and on real
remote regions. A split-member record and a true zero-count region were included.

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts \
  <pysam-venv>/bin/python scripts/validate_reader_against_htslib.py \
  --fragment-url https://datasets.cellxgene.cziscience.com/46b43994-2af5-4359-bf75-3314a0d3a7a5-fragment.tsv.bgz \
  --index-url  https://datasets.cellxgene.cziscience.com/46b43994-2af5-4359-bf75-3314a0d3a7a5-fragment.tsv.bgz.tbi \
  --region chr1:125181130-125182104 --region chr1:145996263-145997154 \
  --region chr21:34790000-34792000 \
  --out reports/generated/reader_correction_20260921/reader_oracle_htslib.json
```

Result: local and remote cases all agree on per-barcode fragment counts
(`all_agree: true`). Remote rows: 312, 29,393 and 1,090 for the three regions.

## Tests actually run

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts \
  /Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -m pytest tests/ -q
# 969 passed, 19 warnings in 91.68s

ruff check scripts/query_fragment_regions.py scripts/quantify_development_atac.py \
  scripts/validate_reader_against_htslib.py tests/test_query_fragment_regions.py \
  tests/test_quantify_development_atac.py
# All checks passed
```

## Superseded claims

- The old internal estimate (cross-attention minus token concatenation +0.0333333,
  95% interval [−0.0133333, +0.0805556], margin 0.07) is reproducible from the saved
  donor predictions but was measured on the old inputs. It is preserved as
  **exploratory historical results** in `docs/repeated_internal_comparison_2026-09-21.json`
  and is not promoted.
- The old "raw-count standard scaling" RNA description is false and is withdrawn.

## Remaining incomplete work

1. RNA `raw/X` selection, raw gene axis and integer-count validation (finding #1).
2. Chromosome-1 feature-bias correction in the report (finding #4); retain the old
   feature rule for the measurement-correction comparison.
3. Bind `scientific_claim_allowed`/`final_internal_estimate` to a validated
   acceptance record instead of auto-promotion.
4. Regenerate corrected ATAC matrices in a new output directory after RNA and
   reader/unit checks pass; record hashes, bytes, axes and reader version.
5. Rerun the corrected pilot and fixed internal comparison, then interventions and
   initialization sensitivity, with one donor-level estimand.
6. Update the canonical notebook and prepare the professor update. External
   evaluation remains separately gated and is not claimed.

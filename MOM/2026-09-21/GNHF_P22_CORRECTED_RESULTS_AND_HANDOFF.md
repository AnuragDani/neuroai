# P22 corrected results and professor handoff

Status: **PARTIAL — corrected measurements executed and internally accepted; external
evaluation still blocked.** This record is the live repair log for the review of the
seven GNHF execution commits (`GNHF_P22_RESULTS_REVIEW.md`, reviewed HEAD
`fe881ea754c9da71588fd10fb6b33deeef52fc38`). The corrected ATAC matrix has now been
regenerated with the fixed reader and the declared `unique_fragment_overlap` unit, the
measured-artifact manifest exists, the shared acceptance gate returns `ACCEPTED`, and
the corrected internal comparison, faithfulness and normalization sensitivity have been
rerun. The old exploratory result is preserved unchanged and remains superseded for
scientific acceptance. The study is not COMPLETE: the canonical notebook handoff is not
yet updated and external paired evaluation remains separately gated.

Worktree: `/Users/anuragdani/Github/niw-eb1a/P22-gnhf-worktrees/p22-results-executio-debda8`.

## Corrected actual results (lead)

The corrected internal primary estimate is a **null**, closer to zero than the old
exploratory estimate:

| Quantity | Old (exploratory, superseded) | Corrected (ACCEPTED) |
|---|---|---|
| RNA representation | processed `X` mislabelled raw | `raw/X` integer counts, `raw/var` axis |
| ATAC count unit | read-support-weighted overlap | `unique_fragment_overlap` (one per fragment) |
| Cross-attention − token-concat donor balanced accuracy | +0.0333333 | **+0.0066667** |
| 95% donor-bootstrap interval | [−0.0133333, +0.0805556] | **[−0.025, +0.0350074]** |
| Practical margin / advantage | 0.07 / false | 0.07 / **false** |
| Acceptance | auto-promoted | **ACCEPTED** (10/10 checks, no blockers) |

- Corrected ATAC matrix: 480 × 248,998, nnz 9,513,875,
  `matrix_sha256 81dfdf7c615dd2252792103a4917d87d949ffb46d3affe3aa0f20d3dd31ecf3f`,
  measured once from the frozen union BED with 480/480 complete joins and the same
  3,295,412,224-byte bounded acquisition footprint as the historical read-support run.
- The corrected matrix is **not** the old matrix relabelled: the sparsity pattern is
  identical but 5,601,677 of 9,513,875 stored counts differ; corrected sum 14,589,258
  vs historical 31,102,865 and max 1,332 vs 4,074.
- Normalization sensitivity (corrected): raw +0.0066667 [−0.025, +0.0350074]; log1p
  +0.0133333 [−0.0266787, +0.0543162]; advantage false in both — the corrected null is
  not normalization-dependent.
- Faithfulness (corrected, 25 folds): RNA-view interventions dominate (view-A clamp /
  ablation drops ≈0.08–0.14), ATAC-view interventions are near zero or slightly
  negative, within-donor permutation ≈0, and uniform routing is measured only for the
  gated family (drop 0.051). This is model dependence under a stated manipulation, not
  causal biology.
- Initialization sensitivity (corrected, donor splits fixed): per-seed primary delta mean
  seed 0 +0.0083333, seed 1 +0.0126667, seed 2 −0.0033333 (spread 0.016) — the null
  holds across initialization seeds.
- Machine-readable records:
  `docs/repeated_internal_comparison_corrected_2026-09-21.json`,
  `docs/real_paired_faithfulness_frozen_corrected_2026-09-21.json`,
  `docs/real_paired_normalization_sensitivity_corrected_2026-09-21.json`; the
  measured-artifact manifest is `configs/real_paired_input_manifest_2026-09-21.json`.

### Exact replay of the corrected run

```
cd /Users/anuragdani/Github/niw-eb1a/P22-gnhf-worktrees/p22-results-executio-debda8
PY=PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts /Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python

# 1. regenerate the corrected 480-region union matrix (bounded remote tabix; ~11 min)
env $PY scripts/quantify_development_atac.py \
  --regions-file reports/generated/repeated_comparison_20260921/union.bed \
  --index-path reports/generated/development_region_set_20260921/fragment.tbi \
  --count-mode fragment --unknown-policy error --workers 8 \
  --total-max-bytes 6442450944 \
  --counts-out reports/generated/repeated_comparison_corrected_20260921/counts \
  --out reports/generated/repeated_comparison_corrected_20260921/quantify.json

# 2. bind the measured manifest and check acceptance (must print ACCEPTED)
env $PY scripts/build_real_paired_input_manifest.py \
  --atac-matrix reports/generated/repeated_comparison_corrected_20260921/counts/counts.npz
env $PY scripts/check_real_paired_acceptance.py \
  --atac-matrix reports/generated/repeated_comparison_corrected_20260921/counts/counts.npz \
  --manifest configs/real_paired_input_manifest_2026-09-21.json

# 3. rerun the frozen comparison and sensitivities on the corrected inputs
env $PY scripts/run_real_paired_comparison.py \
  --atac-matrix reports/generated/repeated_comparison_corrected_20260921/counts/counts.npz \
  --region-sets reports/generated/repeated_comparison_20260921/region_sets.json \
  --acceptance-manifest configs/real_paired_input_manifest_2026-09-21.json \
  --output-dir reports/generated/real_paired_comparison_corrected_20260921/run
env $PY scripts/run_real_paired_faithfulness_frozen.py \
  --atac-matrix reports/generated/repeated_comparison_corrected_20260921/counts/counts.npz \
  --region-sets reports/generated/repeated_comparison_20260921/region_sets.json \
  --acceptance-manifest configs/real_paired_input_manifest_2026-09-21.json \
  --output-dir reports/generated/real_paired_faithfulness_frozen_corrected_20260921/run
env $PY scripts/run_real_paired_normalization_sensitivity.py \
  --atac-matrix reports/generated/repeated_comparison_corrected_20260921/counts/counts.npz \
  --region-sets reports/generated/repeated_comparison_20260921/region_sets.json \
  --output-dir reports/generated/real_paired_normalization_corrected_20260921/run
```

### Wiring defect found while executing

The acceptance-gate call inside `run_real_paired_comparison.py` and
`run_real_paired_faithfulness_frozen.py` passed the `{(repeat, fold): fold}` mapping
returned by `_fold_map` straight into `build_evidence`, which expects a list of fold
objects. This latent defect only surfaced on the first corrected execution; both call
sites now pass `list(folds.values())`. The corrected comparison and faithfulness runs
are the executed proof of the fixed wiring.

## Before / after input semantics

| Input | Old (exploratory, superseded) | Corrected declaration |
|---|---|---|
| ATAC overlap unit | read-support-weighted overlap (sum of column five, i.e. supporting read pairs including duplicates) | `unique_fragment_overlap`: one count per unique qualifying fragment record |
| ATAC reader | per-member line parsing; records split across BGZF members dropped; chunk-end virtual offset not enforced; unbounded `response.read()` | members concatenated before line splitting; chunk end virtual offset enforced; HTTP range verified and size-bounded; truncated/corrupt queries refused before matrix assembly |
| RNA representation | H5AD `X` labelled "raw counts" (actually noninteger processed values) | H5AD `raw/X` integer counts; columns follow the `raw/var` gene axis; axis identifiers validated (present, non-empty, dimension-matched, unique) |

The historical ATAC unit label `fragment_overlap_sum` in
`configs/final_internal_comparison_2026-09-21.json` and the old
`reports/generated/repeated_comparison_20260921/counts/counts.json` is inaccurate and
is preserved only as history. The corrected unit is declared prospectively in
`configs/atac_measurement_contract_2026-09-21.json`.

## Finding-to-evidence table

| Review finding | Regression test | Fix | Executed evidence | Remaining limitation |
|---|---|---|---|---|
| #2 ATAC read-support weighting | `tests/test_query_fragment_regions.py::test_query_region_returns_overlapping_rows`, `test_read_support_mode_reproduces_historical_weighting`; `tests/test_quantify_development_atac.py::test_quantify_regions_concurrent_matrix` | `parse_fragment_line` weights one per unique record in `count_mode="fragment"` (default); `read_support` retained for historical reproduction | audit case yields `saved_count=1` for a support-7 fragment; corrected 480-region matrix regenerated with `unique_fragment_overlap` (5,601,677/9,513,875 stored counts differ from the historical matrix) | Resolved: corrected matrix is the operative one; the historical matrix remains only as preserved history |
| #2b count-semantics provenance | `tests/test_query_fragment_regions.py::test_parse_fragment_line_fragment_mode_weights_one` | one count per unique qualifying record; `read_support` retained only for historical reproduction | bounded 65,536-byte prefix fetch confirms the asset has exactly 5 columns (`chrom, chromStart, chromEnd, barcode, readSupport`), column five all-integer with sample supports 1–3, matching the [10x fragments spec](https://www.10xgenomics.com/support/software/cell-ranger-arc/latest/analysis/outputs/fragments-file); recorded in `docs/atac_fragment_format_and_provenance_2026-09-21.json` | The CELLxGENE dataset is the open development asset; no external cohort is claimed |
| #3a split record across two BGZF members | `tests/test_query_fragment_regions.py::test_record_split_across_two_members_is_one_record` | decompressed members concatenated into a pending-line buffer before splitting on newline | audit case now yields `observed_rows=1`, `truncated=false`; HTSlib oracle agrees | none observed offline |
| #3b chunk-end virtual offsets / duplicate emission | `test_fetch_window_beyond_chunk_end_adds_no_extra_counts`, `test_adjacent_and_overlapping_chunks_do_not_duplicate` | parse only bytes in `[start_voffset, stop_voffset)`; merged chunks prevent duplicate emission | tests pass | none observed offline |
| #3c unbounded HTTP range | `test_http_range_refuses_ignored_range`, `test_http_range_refuses_oversized_body_and_short_read`, `test_http_range_bounded_read_and_consistent_content_range`, `test_http_range_refuses_unsafe_redirect` | HTTP 206 + consistent `Content-Range` required, size-bounded read, oversized/short/unsafe refused | audit case now refused: "server did not honor byte range (HTTP 200)" | none observed offline |
| #3d partial matrix accepted | `tests/test_quantify_development_atac.py::test_quantify_regions_refuses_truncated_query` | `quantify_regions` raises `IncompleteQueryError` before matrix assembly unless `allow_partial` | audit case refused: "1 region(s) returned incomplete reads" | none observed offline |
| #3e zero-count region vs failure | `test_valid_zero_count_region_is_not_a_failure`, `test_quantify_regions_accepts_valid_empty_region` | `empty_region` flag; `join_complete = not truncated and no unknown barcodes` | tests pass; HTSlib oracle agrees on an empty region | none observed offline |
| #3f unknown barcodes / retained population | `test_quantify_regions_refuses_unknown_barcodes_by_default`, `test_quantify_regions_marks_unknown_barcodes` | unknown barcodes refused by default; explicit `unknown_policy="drop"` reports exclusions per region | corrected regeneration with `unknown_policy=error` completed 480/480 complete joins and no unknown barcodes | none observed on the corrected run |
| #3g aggregate transfer accounting | `test_quantify_regions_enforces_aggregate_budget` | `_BudgetedTransport` caps aggregate bytes across concurrent workers | corrected run declared `--total-max-bytes 6442450944` and fetched 3,295,412,224 bytes with 8 workers | none observed on the corrected run |
| #1 RNA `X` vs `raw/X` | `tests/test_real_cohort.py::test_default_rna_matrix_is_raw_counts`, `test_wrong_default_processed_block_cannot_pass_as_raw`, `test_raw_matrix_columns_follow_raw_axis_not_processed_axis`, `test_load_cell_matrix_rejects_negative_raw_counts`, `test_load_cell_matrix_refuses_missing_raw_block`, and the axis-hardening tests `test_read_matrix_axis_refuses_{undeclared_matrix_key,absent_axis_block,empty_identifiers,dimension_mismatch,duplicate_identifiers,missing_index_dataset}` | `load_cell_matrix` defaults to `DEFAULT_RNA_MATRIX_KEY="raw/X"` and rejects non-finite/negative/noninteger consumed values; `read_matrix_axis` resolves `raw/var` for raw columns and refuses absent, unresolved, empty, dimension-mismatched or duplicate identifiers; `run_real_paired_pilot.load_development_inputs` records the raw axis key, cell/column counts and gene-axis hash and refuses an empty axis | real `raw/X` sample `(55, 35477)` all-integer, `X` refused as non-integer; new tests pass | Resolved: the corrected matrix and comparison now consume `raw/X`; the old pilot/comparison results are preserved only as history |
| #4 chromosome-1 feature bias | report-level correction (no code test; the bias is a property of the retained rule) | corrected prose in `MOM/2026-09-21/GNHF_P22_RESULTS_AND_PROFESSOR_HANDOFF.md` §2 to state the chr1 tie-break bias persists (163–219/256 per fold; union 308 chr1 / 110 chr10 / 1 chr21) and is retained for the measurement-correction comparison | audit: 163–219 of 256 regions per fold on chr1 | The biased feature set is retained by design so input correctness is not confounded with outcome-driven feature redesign; its limited coverage bounds any architecture conclusion |
| #5 automatic scientific promotion | `tests/test_real_paired_acceptance.py` (14 tests: accepted fixture, missing manifest, old processed-`X`/read-support unit, hash/cell/region mismatch, held-out donor in feature discovery, overlapping train/test donors, protocol margin/family mismatch, non-prospective requirements); `tests/test_build_real_paired_input_manifest.py` (5 tests) | shared `src/p22/eval/real_paired_acceptance.py` gate; `run_real_paired_comparison.py` and `run_real_paired_faithfulness_frozen.py` derive `scientific_claim_allowed`/`final_internal_estimate` from the decision instead of hardcoding `True`; `scripts/build_real_paired_input_manifest.py` emits the measured manifest; both entry points now pass `list(folds.values())` to `build_evidence` | historical inputs `REFUSED` (`atac_unit`, `manifest_present` and the three manifest-bound checks fail); corrected inputs **`ACCEPTED`** (10/10 checks, no blockers) after the manifest was generated | Resolved for the internal corrected run; external validation is still a separate gate |

## Acceptance binding (finding #5)

The promotion flag was the review's structural blocker: the comparison and
frozen-faithfulness entry points set `scientific_claim_allowed=True` themselves. A
shared gate now owns that decision:

- `configs/real_paired_acceptance_2026-09-21.json` — prospective requirements
  (raw/`X` + `raw/var`, `unique_fragment_overlap`/`fragment`/`error`, the frozen
  union hash and 480 regions, 30 donors 15/15, the six families, 0.07 margin, the
  donor-bootstrap uncertainty rule and the split seeds).
- `src/p22/eval/real_paired_acceptance.py` — `evaluate_input_acceptance` checks
  representation, count unit, region/cell identities, per-fold donor provenance,
  population and protocol, and refuses promotion whenever any check fails or the
  measured manifest is absent. `build_evidence` assembles the bundle from the
  artifacts actually consumed (h5ad/ATAC hashes, ordered-cell hashes, union
  decode, per-fold region-set donor lists).
- `scripts/check_real_paired_acceptance.py` — replayable inspection that prints
  the decision for the current artifacts.

Real-data result on the historical inputs (the expected refusal):

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts \
  /Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python \
  scripts/check_real_paired_acceptance.py \
  --out reports/generated/acceptance_binding_20260921/decision.json
# status REFUSED; blocking = atac_unit, manifest_present, rna_artifact,
#   cell_identity, atac_artifact
# PASS: rna_representation (raw/X, raw/var, integer), region_identity,
#   population (30 donors 15/15), protocol_match (6 families, margin 0.07),
#   fold_provenance (25/25 training-only donor-matched)
```

The old 480-region sidecar declares `count_unit=fragment_overlap_sum` and no
`count_mode`, so `atac_unit` fails: the historical matrices cannot be promoted.
`fold_provenance` passes on all 25 real folds, confirming the region-set train/test
donor lists match the executable donor split (no held-out donor entered feature
discovery). Machine-readable evidence:
`docs/real_paired_acceptance_binding_2026-09-21.json`.

## Caller audit for the RNA default change

Changing `load_cell_matrix`'s default from `X` to `raw/X` was traced through every
production caller:

- `scripts/run_real_paired_pilot.py:load_development_inputs` — the paired input path;
  now selects `raw/X` explicitly and records the resolved axis. Fixed.
- `scripts/run_real_paired_comparison.py` — reuses `load_development_inputs`, so it
  inherits the corrected RNA view with no separate loader.
- `src/p22/eval/real_pipeline.py` (`_cap_load`, `run_real_model_comparison`,
  `run_real_interventions`) — the canonical-notebook path (C24–C31). These call
  `load_cell_matrix` without a key, so they now consume `raw/X`. This is the correct
  choice for this path: the surrounding QC (`derive_cell_qc`, `run_cohort_qc`) and
  `donor_pseudobulk` already stream `raw/X`, so the cell-level model is now
  consistent with the rest of the pipeline instead of mixing processed and raw
  representations. No processed-`X` workflow uses this loader; an explicit
  `matrix_key="X", validate_counts=False` call remains available where a processed
  block is genuinely intended.
- `src/p22/eval/rna_donor_influence.py` uses `donor_pseudobulk` only, which is
  unchanged; the pinned hash was amended prospectively, no replay claimed.
- Tests cover the corrected default, the refusal of a processed block, and the axis
  hardening.

## RNA input evidence on the real development H5AD

`read_matrix_axis` resolves `raw/var` for the `raw/X` block (248,998 x 35,477) and an
independent `derive_cell_qc` pass over `raw/X` reproduces the author per-cell QC
columns to within a small residual, which supports row-order alignment rather than
only matching dimensions:

| Column | identical | correlation | max abs difference |
|---|---|---|---|
| `nFeature_RNA` | no | 0.999996 | 55 |
| `nCount_RNA` | no | 0.999999 | 90 |
| `percent.mt` | no | 0.999999 | 0.0195 |

The small residual (median `-4` counts) is a source-provenance detail: the author QC
columns were computed on the pre-filter gene set while `raw/X` holds counts over the
retained 35,477 features. It is recorded as a limitation, not treated as identity.
A 55-row sample of `raw/X` is all-integer (min 0, max 446); the same call on `X`
raises `non-integer`. Evidence:
`docs/rna_input_correction_2026-09-21.json` (machine-readable, includes the H5AD and
raw-gene-axis hashes); the ignored working copy is at
`reports/generated/rna_input_correction_20260921/derive_qc_agreement.json`.

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
# 1000 passed, 19 warnings in 70.03s

ruff check scripts/query_fragment_regions.py scripts/quantify_development_atac.py \
  scripts/validate_reader_against_htslib.py scripts/run_real_paired_pilot.py \
  scripts/run_real_paired_comparison.py scripts/run_real_paired_faithfulness_frozen.py \
  scripts/check_real_paired_acceptance.py \
  src/p22/data/real_cohort.py src/p22/eval/real_paired_acceptance.py \
  src/p22/eval/rna_donor_influence.py \
  tests/test_query_fragment_regions.py tests/test_quantify_development_atac.py \
  tests/test_real_cohort.py tests/test_real_paired_acceptance.py
# All checks passed
```

The RNA repair added 11 tests (5 raw-count/axis tests plus 6 axis-hardening tests),
taking the suite from 969 to 980; the acceptance gate added 14 more (994); the
measured-manifest builder added 5 more and the fragment-mode unit test added 1
(1000). `donor_pseudobulk` (the only function the
frozen RNA donor-influence diagnostic calls) is unchanged, so its pinned source hash
in `configs/rna_donor_influence.json` was amended prospectively with a recorded
`source_code_amendments` entry and matching `CONFIG_SHA256`; no diagnostic replay is
claimed.

## Superseded claims

- The old internal estimate (cross-attention minus token concatenation +0.0333333,
  95% interval [−0.0133333, +0.0805556], margin 0.07) is reproducible from the saved
  donor predictions but was measured on the old inputs. It is preserved as
  **exploratory historical results** in `docs/repeated_internal_comparison_2026-09-21.json`
  and is not promoted.
- The old "raw-count standard scaling" RNA description is false and is withdrawn;
  the corrected run uses the true `raw/X` block. The earlier raw-versus-log1p
  normalization claim was computed on processed `X`, so it is withdrawn and
  replaced by the corrected sensitivity in
  `docs/real_paired_normalization_sensitivity_corrected_2026-09-21.json`.
- The corrected internal estimate (+0.0066667, 95% [−0.025, +0.0350074], margin
  0.07, advantage false) supersedes the old +0.0333333 for scientific acceptance.
  The old value and its artifacts remain preserved and reproducible.

## Remaining incomplete work

1. ~~RNA `raw/X` selection, raw gene axis and integer-count validation (finding #1).~~
   Repaired; the corrected matrix and comparison now consume `raw/X`.
2. ~~Chromosome-1 feature-bias correction in the report (finding #4).~~ Report
   corrected; the old feature rule is retained for the measurement-correction
   comparison as required.
3. ~~Bind `scientific_claim_allowed`/`final_internal_estimate` to a validated
   acceptance record instead of auto-promotion.~~ Repaired (finding #5): shared
   gate + prospective requirements + real refusal evidence; the measured artifact
   manifest now exists and the corrected run is `ACCEPTED`.
4. ~~Regenerate corrected ATAC matrices ... emit
   `configs/real_paired_input_manifest_2026-09-21.json`.~~ **Done:** corrected
   480 × 248,998 matrix measured in
   `reports/generated/repeated_comparison_corrected_20260921/counts/`, manifest
   emitted, acceptance gate returns `ACCEPTED`.
5. ~~Rerun the corrected pilot and fixed internal comparison, then interventions
   and initialization sensitivity, with one donor-level estimand.~~ **Done:** the
   corrected comparison (+0.0066667, [−0.025, +0.0350074]), faithfulness and
   initialization sensitivity, and the corrected normalization sensitivity all
   executed on the corrected inputs.
6. **Remaining:** update the canonical `P22_down_syndrome_all_in_one.ipynb` to
   expose the corrected real workflow and save an executed copy; write the unsent
   professor update. External evaluation remains separately gated and is not
   claimed.

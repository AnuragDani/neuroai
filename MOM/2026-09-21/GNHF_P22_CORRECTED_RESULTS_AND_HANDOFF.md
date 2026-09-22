# P22 corrected results and professor handoff

Status: **PARTIAL — corrected measurements executed and internally accepted; external
evaluation still blocked.** This record is the live repair log for the review of the
seven GNHF execution commits (`GNHF_P22_RESULTS_REVIEW.md`, reviewed HEAD
`fe881ea754c9da71588fd10fb6b33deeef52fc38`). The corrected ATAC matrix has now been
regenerated with the fixed reader and the declared `unique_fragment_overlap` unit, the
measured-artifact manifest exists, the shared acceptance gate returns `ACCEPTED`, and
the corrected internal comparison, faithfulness and normalization sensitivity have been
rerun. The old exploratory result is preserved unchanged and remains superseded for
scientific acceptance. The canonical notebook now exposes the corrected workflow and a
safe-mode executed copy has been saved, and an unsent professor update has been drafted.
The study is not COMPLETE: external paired evaluation remains separately gated, so the
overall study is labelled PARTIAL.

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
| Acceptance | auto-promoted | **ACCEPTED** (11/11 checks, no blockers) |

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
- Initialization sensitivity (corrected, donor splits fixed, five specified seeds
  0–4): per-seed primary delta mean seed 0 +0.0083333, seed 1 +0.0126667,
  seed 2 −0.0033333, seed 3 −0.009, seed 4 0.0 (spread 0.0216667) — the null
  holds across initialization seeds. Seeds 0–2 reproduce the earlier three-seed
  corrected record exactly; the three-seed record's initialization scope is
  superseded by `docs/real_paired_faithfulness_frozen_corrected5_2026-09-21.json`
  while its interventions are unchanged and preserved.
- Machine-readable records:
  `docs/repeated_internal_comparison_corrected_2026-09-21.json`,
  `docs/real_paired_faithfulness_frozen_corrected_2026-09-21.json` (three-seed
  scope) and its five-seed supersession
  `docs/real_paired_faithfulness_frozen_corrected5_2026-09-21.json`,
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
  --manifest configs/real_paired_input_manifest_2026-09-21.json \
  --out reports/generated/acceptance_binding_20260921/decision_with_inner_validation.json
# prints status ACCEPTED; inner_validation PASS; 11/11 checks, no blockers

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

# 4. five specified initialization seeds (donor splits held fixed; ~105 s)
env $PY scripts/run_real_paired_faithfulness_frozen.py \
  --atac-matrix reports/generated/repeated_comparison_corrected_20260921/counts/counts.npz \
  --region-sets reports/generated/repeated_comparison_20260921/region_sets.json \
  --acceptance-manifest configs/real_paired_input_manifest_2026-09-21.json \
  --init-seeds 0 1 2 3 4 \
  --output-dir reports/generated/real_paired_faithfulness_frozen_corrected5_20260921/run
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
| #5 automatic scientific promotion | `tests/test_real_paired_acceptance.py` (19 tests: accepted fixture, missing manifest, old processed-`X`/read-support unit, hash/cell/region mismatch, held-out donor in feature discovery, overlapping train/test donors, protocol margin/family mismatch, non-prospective requirements, and the five inner-validation cases); `tests/test_build_real_paired_input_manifest.py` (5 tests) | shared `src/p22/eval/real_paired_acceptance.py` gate; `run_real_paired_comparison.py` and `run_real_paired_faithfulness_frozen.py` derive `scientific_claim_allowed`/`final_internal_estimate` from the decision instead of hardcoding `True`; `scripts/build_real_paired_input_manifest.py` emits the measured manifest; both entry points now pass `list(folds.values())` to `build_evidence` | historical inputs `REFUSED` (`atac_unit`, `manifest_present` and the three manifest-bound checks fail); corrected inputs **`ACCEPTED`** (11/11 checks, no blockers) after the manifest was generated | Resolved for the internal corrected run; external validation is still a separate gate |
| #6 outer-only check misdescribed as nested validation | `tests/test_real_paired_acceptance.py::test_inner_validation_donor_from_test_set_refused`, `test_inner_validation_donor_not_in_training_refused`, `test_absent_inner_validation_donors_refused`, `test_undeclared_inner_validation_requirement_refused`, `test_wrong_selection_unit_refused` | new `inner_validation` check in `real_paired_acceptance.py`; `build_evidence` now binds each fold's inner `val_donors`/`selection_split`/`selection_unit` from the executable split via `_inner_validation_map`; `protocol.inner_validation` declared prospectively in `configs/real_paired_acceptance_2026-09-21.json` | corrected real inputs: `inner_validation` **PASS** ("all folds inner validation training-only and test-disjoint"), 11/11 checks, `ACCEPTED`; recorded in `docs/real_paired_inner_validation_2026-09-21.json` | Inner validation is verified to be a training-only, test-disjoint donor subset; the feature rule itself is unchanged and its chr1 bias still bounds any architecture conclusion |

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
#   fold_provenance (25/25 training-only donor-matched),
#   inner_validation (25/25 validation donors training-only, test-disjoint)
```

The old 480-region sidecar declares `count_unit=fragment_overlap_sum` and no
`count_mode`, so `atac_unit` fails: the historical matrices cannot be promoted.
`fold_provenance` passes on all 25 real folds, confirming the region-set train/test
donor lists match the executable donor split (no held-out donor entered feature
discovery). Machine-readable evidence:
`docs/real_paired_acceptance_binding_2026-09-21.json`.

**Nested-validation provenance (finding #6).** The outer `fold_provenance` check is
now paired with an `inner_validation` check, so an outer-only check is not described
as a complete nested-validation proof. `configs/real_paired_acceptance_2026-09-21.json`
declares `protocol.inner_validation` (`selection_split='val'`,
`selection_unit='donor'`, subset-of-train and disjoint-from-test required)
prospectively. `build_evidence` binds each fold's inner `val_donors` from the same
executable split the trainer consumes (`_inner_validation_map` calls `_indices`), and
`_inner_validation_check` refuses the claim when a fold's validation donors are
absent, not training donors, or overlap the held-out test donors. On the corrected
real inputs the check reports **PASS** ("all folds inner validation training-only and
test-disjoint"); the full decision is `ACCEPTED` 11/11 and is recorded in
`docs/real_paired_inner_validation_2026-09-21.json`.

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
# 1009 passed, 19 warnings in 63.21s

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
(1000); the measurement-correction reader added 4 (1004); the inner-validation check
added 5 (1009). `donor_pseudobulk` (the only function the
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
6. ~~Update the canonical notebook and write the unsent professor update.~~
   **Done:** see "Canonical notebook and professor update" below. External
   evaluation remains separately gated and is not claimed, so the overall study
   stays **PARTIAL**.
7. ~~Assert inner-validation donor provenance so an outer-only check is not
   described as a complete nested-validation proof.~~ **Done (finding #6):** the
   shared gate now has an `inner_validation` check bound to the executable split;
   corrected real inputs PASS 11/11 and are `ACCEPTED`. See
   `docs/real_paired_inner_validation_2026-09-21.json`.

All in-scope executable repair items from the review are now complete. The overall
study remains **PARTIAL** only because external paired evaluation is separately
gated and blocked.

## Canonical notebook and professor update

The existing canonical notebook `P22_down_syndrome_all_in_one.ipynb` was
regenerated from `scripts/rewrite_canonical_notebook.py`; no competing notebook
was created. The regeneration re-embeds the current `src/p22` tree, so the
corrected `raw/X` loader, the `real_paired_acceptance` gate and the new
`src/p22/eval/measurement_correction.py` reader are all present in the standalone
notebook.

- **Safe mode remains the default** (`NOTEBOOK_MODE="simulation"`); real mode
  still requires `P22_RUN_REAL_DATA=1`, `P22_RUN_MODEL=1` and the approval
  attestation.
- A new section, **"Corrected real paired workflow — measurement correction"**,
  declares the corrected RNA representation and ATAC unit, and calls the shared
  `summarize_measurement_correction` reader. In safe mode it prints the declared
  contract plus the saved corrected result and acceptance status; the bounded
  remote ATAC regeneration is not executed.
- **Executed copy** (safe mode, kernel `p22`):
  `MOM/2026-09-21/P22_down_syndrome_all_in_one.corrected.executed.ipynb`
  (also written under `reports/generated/notebooks_corrected_20260921/`). All 13
  code cells executed with no error output; the corrected cell printed
  `status=CORRECTED_RESULT_PRESENT`, estimate `+0.0066667`, interval
  `[-0.025, +0.0350074]`, margin `0.07`, advantage `false`, acceptance `ACCEPTED`.
  The real-data model-fitting and remote ATAC regeneration cells are intentionally
  not executed in the safe-mode copy; they require the gated real mode.
  Canonical notebook SHA-256 `9fdd9638e197338fbae7d5467a2d5f19cbe72b1550a445b5be31e9bcd8318e93`;
  executed copy SHA-256 `55b3c6a30a8c54f8a09ea2017cefacd93f7a3ca0be9a375c311dbc912430b568`
  (regenerated after the inner-validation gate change; 13 code cells, zero errors, the
  corrected cell still prints `+0.0066667`, interval `[-0.025, +0.0350074]`, margin
  `0.07`, advantage `false`, acceptance `ACCEPTED`).
- **Unsent professor update**: `docs/professor_update_2026-09-21/` (`one_pager.md`
  and the unsent `email.md`), separating the completed corrected internal work
  from the blocked external and absent biological validation.

Replay:

```
PYTHONDONTWRITEBYTECODE=1 /Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python \
  scripts/rewrite_canonical_notebook.py
PYTHONDONTWRITEBYTECODE=1 /Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -m jupyter nbconvert \
  --to notebook --execute P22_down_syndrome_all_in_one.ipynb \
  --output-dir reports/generated/notebooks_corrected_20260921 \
  --output P22_down_syndrome_all_in_one.corrected.executed.ipynb \
  --ExecutePreprocessor.kernel_name=p22 --ExecutePreprocessor.timeout=900
```

## Professor direction-to-evidence

| Direction | Where it is satisfied | Evidence | Boundary |
|---|---|---|---|
| Mathematically specific methods and verification against primary sources (2026-07-02) | corrected count unit declared before regeneration; interval rule stated; reader checked against the 10x fragment spec and HTSlib | `configs/atac_measurement_contract_2026-09-21.json`; `docs/atac_fragment_format_and_provenance_2026-09-21.json`; `reports/generated/reader_correction_20260921/reader_oracle_htslib.json` | count unit is one per unique fragment record; no insertion-count claim |
| Fair supervision and matched controls (2026-07-02, 2026-07-21) | six families share transforms, splits and selection; matched token-concat control is the primary reference | `docs/repeated_internal_comparison_corrected_2026-09-21.json` | null is honest; not an architecture-failure proof |
| Independent modalities and concatenation controls (2026-07-21) | RNA-only / ATAC-only / concat / gated / token-concat / cross-attention all evaluated on the same folds | `docs/repeated_internal_comparison_corrected_2026-09-21.json`; `docs/real_paired_faithfulness_frozen_corrected5_2026-09-21.json` | RNA-view dominance is model dependence, not biology |
| Donor-aware evaluation, interventions, seed variation (2026-07-21) | donor-held-out folds, donor-aggregated estimand, donor-bootstrap interval, held-out interventions, five initialization seeds | comparison, faithfulness and corrected5 records above; per-fold donor predictions in the source run dirs | intervention effects are manipulation evidence only |
| Clear claim boundaries and canonical notebook (`PROFESSOR_RECOMMENDATIONS_EXECUTION_PLAN.md`) | safe-mode default, corrected workflow exposed, executed copy saved, acceptance gate owns promotion | `P22_down_syndrome_all_in_one.ipynb`; `MOM/2026-09-21/P22_down_syndrome_all_in_one.corrected.executed.ipynb` | real mode remains gated |

Tasic remains engineering evidence only. The completed separate RNA replication
remains **INCONCLUSIVE**. There is no attention-as-mechanism claim and no
fabricated biological validation.

## External status

External paired evaluation remains **BLOCKED** and is not claimed: prior workers
reported NeMO transport failure, contradictory access declarations and no
established common measurement space. No external outcome was used, no access
control or embargo was bypassed, and the blocked route was not repeatedly probed
this iteration. If new evidence later resolves access, matching counts, QC,
features and independence must be validated and the development selection locked
before any external outcome is used. Because external validation is blocked, the
overall study is labelled **PARTIAL**, not complete end-to-end.

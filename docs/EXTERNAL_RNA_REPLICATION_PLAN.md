# External RNA Replication: Implementation Plan

**Status:** Plan only  
**Date:** 2026-09-03  
**Review applied:** `EXTERNAL_RNA_REPLICATION_PLAN_REVIEW_2026-09-03.md`  
**Goal:** Turn current negative classifier result into a bounded external-replication analysis with concrete code, tests, notebook output, and claim limits.

## Decision

Stop extending the binary DS classifier. Same-cap results show chromosome-21 dosage already explains held-out performance; routing and multimodal claims are unsupported.

Next useful result: test whether DS-associated **non-chromosome-21 RNA effects** in fetal-brain progenitors reproduce directionally in independent GSE280175 summary effects.

This first slice intentionally uses the published processed differential-expression workbook. It is a summary-effect replication, not raw external-data reanalysis.

## Frozen scientific contract

| Item | Contract |
|---|---|
| Discovery cohort | Existing primary H5AD |
| Developmental overlap | Primary filter PCW 13–19, with observed primary donors at PCW 13–18; external cohort PCW 13–19 |
| Unit of inference | Donor pseudobulk; never cells as independent replicates |
| Eligible donor-population pair | At least 50 cells |
| Discovery populations | `obs["author_cell_type"]`: `RG`, `RG_prol`, `IPC_prol`, `IPC`; never `cell_type` or `cell_class` |
| External populations | `RG -> oRG`; `RG -> vRG`; `RG_prol ∪ IPC_prol -> CP`; `IPC -> IP` (`IP IN` excluded) |
| Discovery model | Per-gene `log1p(CPM) ~ DS status + exact PCW + sex`; natural-log coefficient used only for rank and sign |
| External effect | Published `avg_log2FC` from Supplementary Data 2 |
| Primary exclusions | chr21/X/Y via `var.seqnames`; mitochondrial via existing `mito_gene_mask`/`MT-` prefix; missing and non-canonical chromosomes excluded |
| Expression floor | Per discovery group on that group's donor pseudobulk CPM: at least 1 CPM in at least half of donors in each disease class; apply before ranking and before the 500-shared-gene stop rule |
| Primary outputs | Shared-gene Spearman rho; sign agreement over top 100 discovery genes ranked by `abs(t)` (DS coefficient / OLS standard error) after expression filtering, with identical re-ranking inside each bootstrap replicate; donor-bootstrap 95% intervals; comparison-specific permutation p-values for agreement |
| Resampling | 1,000 within-class donor bootstraps plus 1,000 whole-external-vector permutations; seed 22; at most 5% failed/rank-deficient bootstrap fits |
| Per-comparison labels | Descriptive, nominal 2.5%: `directionally_supported` when rho bootstrap CI lower > 0 and upper-tail agreement permutation p <= 0.025; `discordant` when rho CI upper < 0 and lower-tail p <= 0.025; otherwise `inconclusive`. Agreement bootstrap intervals are reported, not gated. |
| Headline rule | `directionally_supported` when at least 3 of 4 comparisons are supported and none discordant; `discordant` when at least 3 are discordant and none supported; otherwise `inconclusive` |
| Claim boundary | External support for RNA effect direction only; no classifier, routing, ATAC, or multimodal validation claim |

The frozen headline rule cannot be met by the two RG-derived rows alone. It is a descriptive aggregate rule, not a demonstrated 2.5% family-wise test under arbitrary dependence. The earlier review's calibration claim was incorrect: even if each of four support events has probability at most 0.025 under a global null, Markov's inequality only gives P(at least three) <= 4 * 0.025 / 3. That bound does not establish strong family-wise control or validate the gene-exchangeability assumption. No thresholds or outcomes are changed in response to results; per-comparison and headline labels remain descriptive.

Current audit supports feasibility: filtering PCW 13–19 yields 17 primary-cohort donors (9 DS, 8 control), observed at PCW 13–18. All analysis groups meet the 50-cell floor in 17/17 donors; `IPC_prol` minimum is 55 and `RG_prol ∪ IPC_prol` minimum is 111. Disease, PCW, and sex are invariant within donor. Design rank is 4/4; 0 of 20,000 checked within-class resamples were rank-deficient. Recompute counts, invariance, and rank at runtime.

## External source contract

- GEO accession: [GSE280175](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE280175)
- Study: [Nature Communications article](https://www.nature.com/articles/s41467-025-63752-0)
- Cohort: 10 snRNA-seq samples, 5 DS and 5 euploid; 122,663 nuclei; PCW 13–19. Authority: GEO sample-level growth protocol and article Methods, not the GEO overall-design line describing the Slide-seq subset.
- Supplementary Data 2: [processed differential-expression workbook](https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-025-63752-0/MediaObjects/41467_2025_63752_MOESM4_ESM.xlsx)
- Expected size: 19,576,790 bytes
- Expected SHA-256: `ea0e5a0d96e122ce39ace8be29b65039c3f7775cc96699873a8acc4ee74ccf13`
- Required columns: `gene`, `avg_log2FC`, `p_val`, `p_val_adj`, `pct.1`, `pct.2`, `celltype`, `FDR`, `sig`
- Required sheets: `oRG`, `vRG`, `CP`, `IP`
- Required sole `celltype` value per sheet: `oRG -> oRG`, `vRG -> vRG`, `CP -> Cycling_progenitors`, `IP -> IP`.
- Effect orientation established from article Methods and dosage controls: positive `avg_log2FC` means higher expression in DS than euploid.
- Runtime orientation guard, per required sheet: median chr21 `avg_log2FC > 0` and at least 80% of chr21 effects positive. Otherwise return `execution_status="failed"` with reason `external orientation check failed`.

Fail closed on source hash, schema, or orientation mismatch. Do not silently substitute a different workbook version.

## Minimal code proposal

Public entry point:

```python
COMPARISONS = (
    ("RG", ("RG",), "oRG"),
    ("RG", ("RG",), "vRG"),
    ("cycling_progenitors", ("RG_prol", "IPC_prol"), "CP"),
    ("IPC", ("IPC",), "IP"),
)

run_external_rna_replication(
    h5ad_path,
    external_xlsx,
    pcw_range=(13, 19),
    min_cells_per_donor=50,
    n_bootstrap=1_000,
    n_permutations=1_000,
    seed=22,
)
```

Keep implementation narrow:

```text
existing donor_pseudobulk called once per discovery group
  -> donor x gene counts and n_cells
  -> donor-level logCPM + covariates
  -> per-gene DS coefficient
  -> join published external avg_log2FC by gene
  -> bootstrap intervals + permutation agreement null
  -> four concordance rows + one headline outcome + one compact plot
  -> existing validation.csv reporting path
```

One new module is enough: `src/p22/eval/external_validation.py`. Reuse `donor_pseudobulk`, `mito_gene_mask`, existing data readers, and current reporting path. Do not modify `real_cohort.py` unless measured runtime proves three streaming passes unacceptable. Use `openpyxl` rather than maintaining a custom XLSX parser; add it to project dependencies and Colab bootstrap.

## Implementation tasks

### 1. Lock contract with focused tests

Add `tests/test_external_validation.py` before implementation.

Tests must cover:

- Workbook hash/schema validation.
- Correct external cohort metadata: 5 DS and 5 euploid, not 3 and 3.
- Exact four comparisons and masks against `author_cell_type`; verified sole `celltype` value in each external sheet.
- Orientation guard using chr21 effects.
- chr21/X/Y, `MT-`, missing-chromosome, and non-canonical-contig exclusions.
- Gene normalization; duplicated symbols dropped and counted on both sides.
- Donor metadata collapse rejects disease, PCW, or sex values that vary within a donor.
- Per-group expression-floor ordering and top-100 `abs(t)` ranking, including re-ranking inside each bootstrap replicate.
- Spearman, top-100 agreement, whole-vector permutation p-values, and bootstrap intervals on deterministic fixtures.
- Rank-deficient designs, class loss, shared-gene floor, failed-bootstrap budget, label boundaries, headline rule, and `validation_rows` alias preservation.

**Acceptance:** focused test file fails before implementation and passes after tasks 2–3.  
**Verification:** `pytest tests/test_external_validation.py`  
**Dependencies:** None  
**Files likely touched:** `tests/test_external_validation.py`  
**Estimated scope:** Small

### 2. Implement external replication core

Files:

- New `src/p22/eval/external_validation.py`
- `pyproject.toml`

Functions:

```python
load_external_effects(path, *, expected_sha256, sheets)
fit_discovery_effects(counts, donor_metadata, gene_metadata)
compare_effect_directions(discovery, external, *, top_n=100, seed=22)
summarize_headline_outcome(comparisons)
```

Rules:

- Add `openpyxl==3.1.5` as a declared dependency, matching repository pinning convention. Parse only four required sheets and enforce their sole expected `celltype` values.
- For each discovery group, build `keep_mask & obs["dev_PCW"].between(13, 19) & obs["author_cell_type"].isin(labels)` and call existing `donor_pseudobulk`. Accept three streaming passes. Do not edit `real_cohort.py` unless runtime is measured unacceptable.
- Use returned `n_cells`, `donor_ids`, and `conditions` to enforce the cell floor and class presence.
- Collapse disease, exact PCW, and sex to one row per donor only after asserting each field is invariant within donor.
- Normalize symbols once using uppercase plus whitespace stripping. Drop every symbol duplicated on either side and record dropped counts; do not abort because one duplicate exists.
- Use primary `var.seqnames` for chr21/X/Y and canonical-contig filters. Use existing `mito_gene_mask`/`MT-` fallback for mitochondrial genes.
- Do not separately filter on `feature_is_filtered`; per-group CPM floor is the gene-eligibility rule.
- Use `DonorPseudobulk.log_cpm()` and fit the DS coefficient with exact PCW and sex using NumPy/SciPy OLS. Check design rank before fitting.
- Do not add `batch_seq`: 9 levels among 17 donors cannot be estimated safely. Record this limitation.
- Rank and compare signs only. Primary log1p(CPM) coefficients and external log2 fold changes are not magnitude-comparable.
- Apply the expression floor per discovery group before ranking and before counting shared genes. Rank top 100 by `abs(t)`, where `t = DS coefficient / OLS standard error`.
- Bootstrap donors within disease class, refit discovery effects, and re-rank top 100 by `abs(t)` inside every replicate.
- Build agreement null by permuting the whole external effect vector across shared genes 1,000 times, preserving sign imbalance and magnitude distribution. Compute upper-tail `p = (1 + count(null >= observed)) / (1 + N)` and analogous lower-tail p. Derive independent deterministic streams with `np.random.SeedSequence(seed).spawn(...)`.
- Return shared-gene count, Spearman rho, top-100 agreement, bootstrap intervals, agreement p-values, execution status, per-comparison outcome, headline outcome, reason, source hash, and audit counts.

**Acceptance:** no cell-level inference or external p-values enter the primary test; same-platform fixed-seed numeric output matches to `1e-9`; cross-platform differences are reported, not failed.  
**Verification:** `pytest tests/test_external_validation.py`  
**Dependencies:** Task 1  
**Files likely touched:** `src/p22/eval/external_validation.py`, `pyproject.toml`  
**Estimated scope:** Medium

### Checkpoint after Tasks 1–2

- Focused tests pass.
- Existing pseudobulk behavior remains unchanged.
- Synthetic run returns exactly four deterministic comparisons.

### 3. Integrate with current validation reporting

Files:

- `src/p22/eval/real_pipeline.py`
- `src/p22/eval/validation.py`

- Add `run_external_rna_replication` beside current real-validation orchestration.
- Correct GSE280175 metadata from 3 + 3 to 5 + 5 and record PCW 13–19, 122,663 nuclei, RNA-only. Do not use historical generated CSV files as authority.
- Extend `real_state.validation_rows` in place with `.extend(rows)` before `EvidencePackage.write`. Notebook G8 aliases this list as `validation_rows`; never rebind either name to a new list. `validation.csv` is regenerated per run as a union of row columns, not appended across runs.
- Add exactly four comparison rows. Keep `execution_status`, `scientific_outcome`, and `headline_outcome` separate.
- Add `evidence_scope="published cell-level MAST summary effects (donor covariate); not raw external reanalysis"`.
- Keep `external_matrix_ingested=False`; G8 remains `INCONCLUSIVE`. Summary-effect replication must never flip G8.
- Preserve current held-out-panel results and gate semantics.

Suggested result columns:

```text
analysis, discovery_population, primary_labels, external_population,
n_ds_donors, n_control_donors, n_shared_genes, spearman_rho,
spearman_ci_low, spearman_ci_high, top100_direction_agreement,
agreement_ci_low, agreement_ci_high, agreement_permutation_p_upper,
agreement_permutation_p_lower, execution_status, scientific_outcome,
headline_outcome, reason, evidence_scope, external_accession,
external_sha256, dropped_duplicate_primary, dropped_duplicate_external
```

**Acceptance:** exactly four rows appear with source hash, donor counts, audit counts, evidence scope, and unchanged G8 status.  
**Verification:** focused tests plus synthetic evidence-package write/read through a pre-bound `validation_rows` alias; alias must observe four appended rows  
**Dependencies:** Task 2  
**Files likely touched:** `src/p22/eval/real_pipeline.py`, `src/p22/eval/validation.py`  
**Estimated scope:** Medium

### 4. Put result in canonical notebook

Files:

- `scripts/rewrite_canonical_notebook.py`
- Generated `P22_down_syndrome_all_in_one.ipynb`

Real-mode behavior:

- Add pinned `openpyxl==3.1.5` to CELL1 bootstrap dependencies.
- Download the 18.6 MB workbook only when missing and verify SHA-256 before parsing.
- Add deterministic, idempotent insertion in `main()`: when notebook has 22 cells, assert cell id `ext-rna1` is absent and insert an empty code cell with that id at index 20; when it has 23 cells, assert index 20 already has that id; reject any other layout.
- After insertion, assert 23 cells and map `20 -> CELL_EXTERNAL`, `21 -> CELL20`, `22 -> CELL21`. Cells 2, 3, and 5 remain hand-maintained and must not be overwritten by managed-cell regeneration.
- Run replication entry point.
- Display one four-row table, one compact four-panel concordance plot, and headline outcome.
- State summary-effect-only claim boundary and limitations beside result: local PCW 19 absent; labels mapped nominally; batch unmodelled; one sub-quality and one thin donor; natural-log discovery effects are compared only by rank/sign with external log2 effects.

**Acceptance:** generated notebook matches rewrite-script output, executes with zero errors, and shows four rows plus boundary text.  
**Verification:** regenerate twice to prove idempotence; compare managed cells; execute real mode using documented nbconvert command with `--output-dir reports/generated/notebooks`; never write executed copy at repository root  
**Dependencies:** Task 3  
**Files likely touched:** `scripts/rewrite_canonical_notebook.py`, `P22_down_syndrome_all_in_one.ipynb`  
**Estimated scope:** Medium

### Checkpoint after Tasks 3–4

- Full test suite and lint pass.
- Synthetic evidence package contains four rows and leaves G8 inconclusive.
- Local real notebook completes with no errors.

### 5. Verify in increasing-cost order

1. Focused external-validation tests.
2. Existing unit and integration suite.
3. `ruff check src tests scripts`.
4. Local real-data notebook execution.
5. Fresh Google Colab execution.

Final evidence must include:

- Exact source SHA-256.
- Four comparison rows.
- Per-row donor and shared-gene counts.
- Reproducible bootstrap intervals and agreement permutation p-values.
- Per-comparison and headline outcomes.
- Zero notebook execution errors.
- G8 remains inconclusive.
- Clear statement that this tests aggregate direction of processed RNA effects, not predictive generalization or per-gene replication.

**Acceptance:** all five verification levels pass; local and Colab differences, if any, are reported.  
**Verification:** archive focused/full test output, lint output, local notebook execution record, and fresh-Colab execution record with final evidence package  
**Dependencies:** Task 4  
**Files likely touched:** None beyond generated evidence artifacts  
**Estimated scope:** Medium

## Stop conditions

Return a failed execution result, not a scientific conclusion, when:

- Workbook hash or required schema differs.
- Any required sheet fails the chr21 orientation guard: median `avg_log2FC <= 0` or fewer than 80% of chr21 effects are positive.
- Any mapped primary population loses DS or control donors.
- Any included donor-population pair has fewer than 50 cells.
- Fewer than 500 shared eligible genes remain after exclusions.
- More than 5% of bootstrap fits are rank-deficient or otherwise invalid.
- Covariate design matrix is rank-deficient.

Record these thresholds as named constants with tests. They are analysis-contract decisions, not hidden implementation defaults.

## Known limitations

- External evidence is published cell-level MAST summary output with donor replicate as a covariate, not donor-level raw-matrix reanalysis.
- `batch_seq` has 9 levels among 17 primary donors and cannot be estimated safely with this design. Batch remains unmodelled and must be disclosed.
- Primary donors are observed at PCW 13–18; external cohort includes PCW 19.
- Cell-population mappings are nominal. No label transfer proves equivalence; `RG_prol ∪ IPC_prol -> CP` reflects a broad cycling-progenitor match.
- Primary effects use natural-log `log1p(CPM)` while external effects use log2 fold change. Only ranks and signs are compared; magnitudes are not.
- `PCW18_DS_16545` has sub-quality tissue and `PCW17_CON_14310` is thin near the cell floor. Donor bootstrap partly exposes sensitivity, but output must name both limitations.
- Removing chr21 tests trans effects outside the aneuploid chromosome. It does not establish dosage-independent biology or causal mechanism.

## Explicitly deferred

- Downloading/reprocessing the roughly 1.9 GB raw GSE280175 expression matrix.
- Cell-label transfer between studies.
- External ATAC validation.
- New neural architecture or routing experiment.
- Stage-interaction model.
- Broad neuronal population mapping.
- Custom XLSX parser.
- Pseudobulk aggregation refactor; reconsider only if three measured streaming passes are too slow.

Add raw reanalysis only if processed-effect replication is informative or a reviewer explicitly requires end-to-end external preprocessing.

## Definition of done

- Four frozen comparisons run from the canonical notebook.
- Donor-level discovery model and donor bootstrap are tested.
- External workbook is hash-, schema-, and orientation-verified.
- Agreement uses comparison-specific, whole-vector permutation p-values, not a 0.5 null or mixed CI/percentile gate.
- Results use existing reporting path.
- G8 remains inconclusive because no external matrix is ingested.
- All checks pass locally and in fresh Colab.
- Conclusions stay within the external RNA direction-replication boundary.

## Repository safety

Do not overwrite `notebooks/implementation/06_metrics_and_run_reporting.ipynb`, root-level `P22_down_syndrome_all_in_one_executed.ipynb`, or unrelated untracked files. Executed notebook output belongs under gitignored `reports/generated/notebooks`. No `tasks/` directory exists. Separate Colab verification is tracked in `docs/CURSOR_VERIFICATION_HANDOFF.md`.

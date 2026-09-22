# P22: representation sensitivity, simple controls, and the missing biological question

Prepared 21 September 2026. Status: **ASSIGNMENT_COMPLETE / STUDY_PARTIAL** — the
prespecified ATAC representation sensitivity and the missing simple linear controls
have executed validly on both representations, and the model-free cell-state
feasibility assessment is delivered. External paired evaluation and independent
biological validation remain **NOT PERFORMED**.

## Question

Does the corrected internal null persist when the arbitrary chromosome-name
lexicographic tie-break inside training-library prevalence ties is removed, and does
the available paired information support a cell-state-focused next study?

## What is new since 19 September

1. **One prespecified representation change.** The retained 256-region ATAC rule
   ranked training-library prevalence and broke ties by `(chromosome, start, end)`,
   which put 163–219 of 256 regions on chromosome 1 in every fold. A prospective
   amendment (`configs/atac_tiebreak_sensitivity_2026-09-21.json`, salt
   `p22-atac-tiebreak-v1`) changed **only** the tie-break inside equal prevalence to
   `sha256(salt + "\n" + region)`. Candidate construction, prevalence definition,
   region budget, chromosome filter and donor folds were unchanged; the salt was
   fixed before any selection ran.
2. **A new measured matrix** for the resulting 465-region union (465 × 248,998,
   SHA-256 `5f13c089…`, `unique_fragment_overlap`, 3.182 GB bounded tabix transfer),
   bound to a new measured-artifact manifest that passes the shared acceptance gate.
3. **The missing simple linear controls** — RNA-only, ATAC-only and concatenated
   cell-level logistic regressions — on both representations, with frozen
   `C=1.0`, `lbfgs`, `max_iter=1000`, `tol=1e-4`, seed 0; all fits converged.
4. **A model-free cell-state feasibility assessment** (no model fitted, no outcome
   used): donor-by-cell-type support, measured ATAC panel support, a deterministic
   donor-aware stratified sampling proposal, and a prespecified future estimand.

## Result: the null persists

| Representation | Union | Cross-attention − token-concat | 95% donor-bootstrap interval | Margin | Advantage |
|---|---|---|---|---|---|
| Historical corrected | 480 (chr1 308) | **+0.0067** | [−0.025, +0.0350] | 0.07 | false |
| sha256 tie-break | 465 (chr1 37) | **−0.0200** | [−0.0533, +0.0113] | 0.07 | false |

The corrected internal null is **not** an artifact of chromosome-1 lexicographic
preference. Five initialization seeds on the tie-break representation
(−0.0200, 0.0, +0.0400, −0.0133, +0.0067; spread 0.06 < margin) show no seed with an
advantage. Secondary linear controls show RNA-only and concatenated logistic
regression (≈0.62) outperform the neural token-concat reference (≈0.53) on both
representations, while ATAC-only logistic underperforms (≈0.41); this is an
estimator-level observation, not a cross-attention result.

## The biological objective still missing from the classifier work

The classifier comparison answers a **donor disease-classification** question. The
biological objective the professor asked for is a **within-excitatory-lineage
maturation / regulatory program** question, and the current artifacts cannot yet
answer it:

- All 13 prespecified program genes (RORB, FOXP1, TLE4, BCL11B, CUX2, NEUROD2,
  NEUROD6, SOX9, PAX6, EOMES, FEZF2, TCF7L2, RORA) are present on the RNA axis.
- Only **1 of 13** (TLE4, `chr9:79571205-79572111`) has any overlapping measured
  ATAC region in either panel; RORB and FOXP1 have none. The prevalence-selected
  panels are therefore **not** a targeted regulatory panel.
- `dev_PCW` is donor-invariant and usable as an exact age covariate; `batch_seq` and
  `library` are **not** donor-invariant (7 of 30 donors carry two batches/libraries),
  so batch must be a within-donor sensitivity, not a donor covariate.

A prespecified future estimand and falsification criterion are recorded in
`docs/cellstate_next_study_2026-09-21.json`. Testing it needs a locus-targeted region
set or the author peak-by-cell matrix / a bounded gene-proximal fragment recount,
which is outside this assignment.

## Limits

- The sha256 set is an **ordering control**, not genome-wide coverage or a validated
  regulatory panel. Removing lexicographic preference is not a claim of better
  biology.
- Cell-state tables are descriptive; author cell-type labels are context, not
  independent truth; region-overlap sums are not total assay fragments.
- External paired evaluation remains **NOT READY** (permission/declaration,
  transport, release/QC identity, paired axes, compatible regions and specimen
  independence are all separately unresolved). No external outcome was used.
- The Lattke paper is this same cohort (annotation support only), and the separate
  completed RNA replication remains **INCONCLUSIVE**.

## Evidence to open first

- Main handoff: `MOM/2026-09-21/GNHF_P22_NEXT_STAGE_RESULTS.md`.
- Safe-mode executed canonical notebook (now exposes the tie-break sensitivity,
  linear controls and cell-state feasibility):
  `MOM/2026-09-21/P22_down_syndrome_all_in_one.corrected.executed.ipynb`.
- Machine-readable records: `docs/atac_tiebreak_measured_and_comparison_2026-09-21.json`,
  `docs/atac_tiebreak_sensitivity_2026-09-21.json`,
  `docs/cellstate_feasibility_2026-09-21.json`,
  `docs/cellstate_next_study_2026-09-21.json`.

This is a measurement-adequacy follow-up, not a search for a cross-attention win.

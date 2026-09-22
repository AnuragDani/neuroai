# P22 professor update package — 21 September 2026

Start with [one_pager.md](one_pager.md). [email.md](email.md) is an **unsent**
draft. This is a local review package, not a new experiment and not a claim that
P22 is complete.

## Status

**ASSIGNMENT_COMPLETE / STUDY_PARTIAL.** The prespecified ATAC representation
sensitivity and the missing simple linear controls have executed validly on both
representations, and the model-free cell-state feasibility assessment is delivered.
External paired evaluation and independent biological validation remain blocked and
are not claimed.

## What is included

| Material | Path |
|---|---|
| Main next-stage handoff | `MOM/2026-09-21/GNHF_P22_NEXT_STAGE_RESULTS.md` |
| Repair record (finding-to-evidence table) | `MOM/2026-09-21/GNHF_P22_CORRECTED_RESULTS_AND_HANDOFF.md` |
| Safe-mode executed canonical notebook | `MOM/2026-09-21/P22_down_syndrome_all_in_one.corrected.executed.ipynb` |
| Canonical notebook source (corrected + sensitivity workflow exposed) | `P22_down_syndrome_all_in_one.ipynb` |
| Prospective sensitivity amendment | `configs/atac_tiebreak_sensitivity_2026-09-21.json` |
| Tie-break measurement and comparison record | `docs/atac_tiebreak_measured_and_comparison_2026-09-21.json` |
| Tie-break region-set diagnostics | `docs/atac_tiebreak_sensitivity_2026-09-21.json` |
| Cell-state feasibility record | `docs/cellstate_feasibility_2026-09-21.json` |
| Prespecified future estimand | `docs/cellstate_next_study_2026-09-21.json` |
| Corrected internal comparison record | `docs/repeated_internal_comparison_corrected_2026-09-21.json` |

## Results

Cross-attention minus matched token-concatenation donor balanced accuracy is
**+0.0067** on the historical corrected 480-region representation
(95% interval **[−0.025, +0.035]**, margin 0.07, advantage **false**) and
**−0.0200** on the 465-region sha256 tie-break representation
(95% interval **[−0.0533, +0.0113]**, advantage **false**). The corrected null
persists when the lexicographic tie-break is removed. Simple RNA-only and
concatenated logistic controls (≈0.62) outperform the neural token-concat reference
(≈0.53); this is an estimator-level observation, not a cross-attention result.

## Limits

- The sha256 set is an ordering control, not genome-wide coverage or a validated
  regulatory panel.
- The cell-state tables are model-free and descriptive; author cell-type labels are
  context, not independent truth.
- Only 1 of 13 prespecified maturation-program loci has an overlapping measured ATAC
  region, so the within-lineage program question is not supported by the current
  panels.
- External paired evaluation remains blocked (transport/access; no common
  measurement space); no external outcome was used.
- The Lattke paper is the same cohort (annotation support only); the separate
  completed RNA replication remains INCONCLUSIVE.

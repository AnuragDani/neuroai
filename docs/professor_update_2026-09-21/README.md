# P22 professor update package — 21 September 2026

Start with [one_pager.md](one_pager.md). [email.md](email.md) is an **unsent**
draft. This is a local review package, not a new experiment and not a claim that
P22 is complete.

## Status

**PARTIAL.** The corrected internal paired comparison has been executed on the
repaired RNA (`raw/X`) and ATAC (`unique_fragment_overlap`) inputs, bound to a
measured-artifact manifest and passed through the shared acceptance gate. External
paired evaluation and biological validation remain blocked and are not claimed.

## What is included

| Material | Path |
|---|---|
| Repair record (finding-to-evidence table) | `MOM/2026-09-21/GNHF_P22_CORRECTED_RESULTS_AND_HANDOFF.md` |
| Safe-mode executed canonical notebook | `MOM/2026-09-21/P22_down_syndrome_all_in_one.corrected.executed.ipynb` |
| Canonical notebook source (corrected workflow exposed) | `P22_down_syndrome_all_in_one.ipynb` |
| Corrected internal comparison record | `docs/repeated_internal_comparison_corrected_2026-09-21.json` |
| Corrected faithfulness record | `docs/real_paired_faithfulness_frozen_corrected_2026-09-21.json` |
| Corrected normalization sensitivity | `docs/real_paired_normalization_sensitivity_corrected_2026-09-21.json` |
| Measured-artifact manifest | `configs/real_paired_input_manifest_2026-09-21.json` |

## Corrected result

Cross-attention minus matched token-concatenation donor balanced accuracy is
**+0.0067** (95% donor-bootstrap interval **[−0.025, +0.035]**, margin 0.07,
advantage **false**) — a null. The historical +0.0333 estimate was measured on the
defective inputs and is preserved as exploratory history.

## Limits

- External paired evaluation remains blocked (transport/access; no common
  measurement space); no external outcome was used.
- No causal or biological claim; interventions are model dependence only.
- The retained region rule is chromosome-1 biased; the limited coverage bounds any
  architecture conclusion.
- The separate completed RNA replication remains INCONCLUSIVE.

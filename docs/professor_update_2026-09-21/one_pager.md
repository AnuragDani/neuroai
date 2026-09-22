# P22: corrected paired inputs, rerun internal comparison, remaining limits

Prepared 21 September 2026. Status: **PARTIAL** — corrected internal work
executed; external paired evaluation and biological validation remain blocked.

## Question

Can accepted paired RNA+ATAC development inputs support a donor-aware comparison
of cross-attention against matched token concatenation?

## What changed since 19 September

Two independently reproduced input defects were repaired before rerunning:

| Input | Before (exploratory, superseded) | Corrected |
|---|---|---|
| RNA | processed H5AD `X` consumed while labelled raw counts | integer `raw/X` with the `raw/var` gene axis |
| ATAC overlap unit | read-support-weighted (column five summed) | `unique_fragment_overlap` (one per unique qualifying fragment record) |
| ATAC reader | records split across BGZF members dropped; chunk-end virtual offset unenforced; unbounded `response.read()` | members concatenated before line splitting; chunk-end offsets enforced; HTTP range verified and size-bounded |

The corrected reader agrees with HTSlib (pysam 0.24.1) on local fixtures
(including a record split across two BGZF members and a true zero-count region)
and on real remote regions. A shared acceptance gate now replaces the automatic
scientific-claim promotion; the corrected run is `ACCEPTED` (10/10 checks) and the
historical inputs are `REFUSED`.

## Corrected internal result (null)

| Quantity | Old (exploratory) | Corrected |
|---|---|---|
| Cross-attention − token-concat donor balanced accuracy | +0.0333 | **+0.0067** |
| 95% donor-bootstrap interval | [−0.0133, +0.0806] | **[−0.025, +0.0350]** |
| Practical margin / advantage | 0.07 / false | 0.07 / **false** |

The corrected matrix has identical sparsity but 5,601,677 of 9,513,875 stored
counts differ from the historical read-support-weighted matrix, so the correction
is a real measurement change, not a relabel. Normalization sensitivity (raw vs
log1p) stays null, and the null holds across the five specified initialization
seeds 0-4 measured on the same pooled-donor estimand as the primary contrast
(per-seed deltas +0.0067, +0.0067, -0.0067, -0.0067, 0.0; spread 0.013; seed 0
reproduces the primary interval exactly).

## What remains unresolved (external and biological)

- **External paired evaluation is blocked.** Transport failure, contradictory
  access declarations and no established common measurement space. No external
  outcome was used and no access control was bypassed.
- **No biological validation.** Interventions are model dependence under a stated
  manipulation, not causal biology. There is no attention-as-mechanism claim.
- **Feature coverage is limited.** The retained 256-region rule remains
  chromosome-1 biased (163-219 of 256 regions per fold); it is retained so input
  correctness is not confounded with outcome-driven feature redesign.
- The completed separate RNA replication remains **INCONCLUSIVE**.

## Evidence to open first

- Repair record: `MOM/2026-09-21/GNHF_P22_CORRECTED_RESULTS_AND_HANDOFF.md`.
- Safe-mode executed canonical notebook:
  `MOM/2026-09-21/P22_down_syndrome_all_in_one.corrected.executed.ipynb`.
- Corrected result records: `docs/repeated_internal_comparison_corrected_2026-09-21.json`,
  `docs/real_paired_faithfulness_frozen_corrected_2026-09-21.json`,
  `docs/real_paired_normalization_sensitivity_corrected_2026-09-21.json`.

This is a corrected internal result, not a new external experiment.

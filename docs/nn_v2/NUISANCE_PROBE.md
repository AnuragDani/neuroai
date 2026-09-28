# Nuisance-probe diagnostics (N14)

Source models: `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v3` (canonical ladder_v3; not copied into finish-base).

**Decision:** `R2_REJECTED` with `PROBE_DROP_INSUFFICIENT`. No `ADVERSARY_ERASES_SIGNAL`.

Rule (plan §4.2 / decision_tree N14): reject R2 if held-out within-disease nuisance-probe accuracy does not drop ≥ 5 points vs R1, or donor BA drops > 0.05 vs R1.

| Arm | Batch probe (held-out) | Library probe | QC R² | Mean fold donor BA | Params |
|---|---|---|---|---|---|
| R1_ca | 0.0562 | N/A (0/150 scorable) | -0.126 | 0.512 | 367876 |
| R1_tc | 0.0539 | N/A (0/150 scorable) | -0.128 | 0.524 | 363652 |
| R2_ca | 0.0661 | N/A (0/150 scorable) | -0.054 | 0.539 | 384250 |
| R2_tc | 0.0603 | N/A (0/150 scorable) | -0.059 | 0.519 | 380026 |
| R3_ca | 0.0556 | N/A (0/150 scorable) | -0.034 | 0.539 | 384250 |
| R3_tc | 0.0535 | N/A (0/150 scorable) | -0.040 | 0.523 | 380026 |

Probe drop (R1−R2, percentage points): CA ≈ -0.99; TC ≈ -0.64. Donor BA drop: CA ≈ -0.028; TC ≈ 0.004.

**Caveats:** Library probe is not scorable under donor-held-out splits (scorable on 0/150 fold-arm rows). Primary probe therefore uses batch_seq when library is unscorable. Fold-mean donor BA here is not the same pooling as `ladder_summary.json` arm BA; the R1−R2 *delta* is what the rejection rule uses. R2 remains reported on the ladder; rejection means the adversary refinement is not carried as evidence.

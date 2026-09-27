# Nuisance-probe diagnostics (N14)

Source models: `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v2` (accepted ladder_v2; not copied into finish-base).

**Decision:** `R2_REJECTED` with `PROBE_DROP_INSUFFICIENT` (CA and TC). No `ADVERSARY_ERASES_SIGNAL`.

Rule (plan §4.2 / decision_tree N14): reject R2 if held-out within-disease nuisance-probe accuracy does not drop ≥ 5 points vs R1, or donor BA drops > 0.05 vs R1.

| Arm | Batch probe (held-out) | Library probe | QC R² | Mean fold donor BA | Params |
|---|---|---|---|---|---|
| R1_ca | 0.0558 | N/A (0/25 scorable) | −0.132 | 0.504 | 367876 |
| R1_tc | 0.0553 | N/A | −0.125 | 0.532 | 363652 |
| R2_ca | 0.0633 | N/A | −0.059 | 0.517 | 384250 |
| R2_tc | 0.0618 | N/A | −0.066 | 0.515 | 380026 |
| R3_ca | 0.0569 | N/A | −0.046 | 0.540 | 384250 |
| R3_tc | 0.0543 | N/A | −0.044 | 0.516 | 380026 |

Probe drop (R1−R2, percentage points): CA ≈ −0.75; TC ≈ −0.65 (R2 slightly *higher* than R1; both near chance for 12-way batch). Donor BA drop: CA ≈ −0.013; TC ≈ 0.017 (both ≤ 0.05).

**Caveats:** Library probe is not scorable under donor-held-out splits (test libraries unseen within disease). Primary probe therefore uses batch_seq only. Fold-mean donor BA here is not the same pooling as `ladder_summary.json` arm BA; the R1−R2 *delta* is what the rejection rule uses. R2 remains reported on the ladder; rejection means the adversary refinement is not carried as evidence.

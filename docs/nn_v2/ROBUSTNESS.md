# NN-v2 robustness (D13, D9) — tasks N11, N12

## Source binding

- Accepted with-chr21 ladder: `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v3` (canonical; P1 N11 vs ladder_v3).
- N11 no-chr21 folds: `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/chr21_excluded_v3` (`n_folds=100`; arms R3_ca, R3_tc, logreg_rna, logreg_concat).
- Prior ladder_v2 / chr21_excluded paths retained on disk; docs now bind to `_v3`.
- N12 seed rerun for ladder_v3 is pending under P1 (`seeds_v3`).

## chr21-excluded sensitivity (N11)

Rebuilt `docs/nn_v2/chr21_excluded.json` against the canonical ladder. Decision-tree N11 label **DOSAGE_DOMINATED**. Per-arm no-chr21 BA: R3_ca 0.333, R3_tc 0.373, logreg_rna 0.407, logreg_concat 0.400. Interpretation limited to this internal 30-donor cohort.

## Init-seed and sampling-seed sensitivity (N12)

Accepted against ladder_v2 frozen widths. Primary contrast (R3_ca−R3_tc) across model seeds 0–4 at sampling seed 22 and sampling seeds {22,23,24} at model seed 0:

| run | estimate | CI |
|---|---:|---|
| m_0_s_22 (ladder reuse) | −0.0067 | [−0.0533, 0.0348] |
| m_1_s_22 | 0.0133 | [−0.0375, 0.0652] |
| m_2_s_22 | 0.0067 | [−0.0302, 0.0431] |
| m_3_s_22 | ≈0 | [−0.0616, 0.0590] |
| m_4_s_22 | ≈0 | [−0.0407, 0.0438] |
| m_0_s_23 | 0.0067 | [−0.0333, 0.0493] |
| m_0_s_24 | 0.0333 | [−0.0213, 0.0861] |

Model-seed spread = 0.020; sampling-seed spread = 0.040. Ladder outcome is `B_NULL`, so decision-tree N12 reports spread only (`SPREAD_ONLY`); sampling spread ≤ 0.07 so **not** `SAMPLING_SENSITIVE`. Evidence: `docs/nn_v2/seed_sensitivity.json`.


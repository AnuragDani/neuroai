# NN-v2 robustness (D13, D9) — tasks N11, N12

## Source binding

- Accepted with-chr21 ladder: `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v3` (canonical; P1 N11 vs ladder_v3).
- N11 no-chr21 folds: `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/chr21_excluded_v3` (`n_folds=100`; arms R3_ca, R3_tc, logreg_rna, logreg_concat).
- N12 seeds: `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/seeds_v3` (m_0_s_22 reuses `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v3`).
- Prior ladder_v2 / chr21_excluded paths retained on disk; docs now bind to `_v3`.

## chr21-excluded sensitivity (N11)

Rebuilt `docs/nn_v2/chr21_excluded.json` against the canonical ladder. Decision-tree N11 label **DOSAGE_DOMINATED**. Per-arm no-chr21 BA: R3_ca 0.333, R3_tc 0.373, logreg_rna 0.407, logreg_concat 0.400. Interpretation limited to this internal 30-donor cohort.

## Init-seed and sampling-seed sensitivity (N12)

Accepted against `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v3` frozen widths (`seeds_v3`). Primary contrast (R3_ca−R3_tc) across model seeds 0–4 at sampling seed 22 and sampling seeds {22,23,24} at model seed 0:

| run | estimate | CI |
|---|---:|---|
| m_0_s_22 (ladder reuse) | 0.0267 | [-0.0267, 0.0770] |
| m_1_s_22 | -0.0067 | [-0.0498, 0.0306] |
| m_2_s_22 | 0.0000 | [-0.0545, 0.0472] |
| m_3_s_22 | -0.0467 | [-0.1019, 0.0000] |
| m_4_s_22 | -0.0067 | [-0.0685, 0.0467] |
| m_0_s_23 | -0.0067 | [-0.0455, 0.0308] |
| m_0_s_24 | 0.0200 | [-0.0133, 0.0550] |

Model-seed spread = 0.073; sampling-seed spread = 0.033. Ladder outcome is `B_NULL`, so decision-tree N12 reports `SPREAD_ONLY`. Evidence: `docs/nn_v2/seed_sensitivity.json`.

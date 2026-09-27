# N15 out-of-fold cell scores

Source models: `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v2` (accepted S6; not copied into finish-base). Prior `cell_scores.buggy_ladder.csv.gz` is superseded and unused.

| Item | Value |
|---|---|
| Arms | R1_ca, R3_ca, R3_tc, R4_ca |
| Folds used | 100 (25 × 4) |
| Cell×arm rows | 120000 (30000 cells × 4) |
| Repeats per cell×arm | 5 (asserted before averaging) |
| Donor×cell-type rows | 1800 |
| R3_ca parameter_count | 384250 |
| n_library / n_batch | 37 / 12 |

Outputs: `reports/generated/nn_20260923/spectrum/cell_scores.csv.gz`, `docs/nn_v2/donor_celltype_scores.csv.gz`, `docs/nn_v2/cell_scores_export.json`.

Chr21-excluded arm export is **DEFERRED** (models exist under `chr21_excluded/`; optional for N16 compare; pass `--include-chr21-excluded` to add).

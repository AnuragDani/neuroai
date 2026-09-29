# N15 out-of-fold cell scores

Source models: `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v3` (canonical ladder_v3; not copied into finish-base).

| Item | Value |
|---|---|
| Arms | R1_ca, R3_ca, R3_tc, R4_ca |
| Folds used | 100 |
| Cell×arm rows | 120000 |
| Repeats per cell×arm | 5 (asserted=True) |
| Donor×cell-type rows | 1800 |
| R3_ca parameter_count | 384250 |
| n_library / n_batch | 37 / 12 |

Outputs: `reports/generated/nn_20260923/spectrum_v3/cell_scores.csv.gz`, `docs/nn_v2/donor_celltype_scores.csv.gz`, `docs/nn_v2/cell_scores_export.json`.

Chr21-excluded export: 60000 cell×arm rows from `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/chr21_excluded_v3`.

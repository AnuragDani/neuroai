# Faithfulness interventions (N13)

**Status: BLOCKED — `N10_ladder_missing`.** No intervention was run.

The N10 real-data ladder is `BLOCKED:lane_stalled:no commit in 3 attempts`: it produced
no `reports/generated/nn_20260923/ladder/` directory, no saved fold `state_dict` models,
and no runner (`scripts/run_nn_v2_comparison.py` is absent). The N13 spec permits refitting
with the recorded grid point, but the grid point is recorded only inside the N10 fold JSONs
that do not exist, so there is nothing to refit against. N4 saved planted-task results
(`results.csv.gz`) but no fitted planted model, so the positive control has no model either.

**Rule.** An attention/gate/pairing/MIL readout may be described as *used by the model* only
if its intervention Δ log-loss donor-bootstrap CI excludes 0. Because no intervention was
run, **no readout is shown as used**. Per `decision_tree.md` N17, every readout is
`NOT_SHOWN_USED`.

| ID | Applies to | Manipulation | Status |
|---|---|---|---|
| I1 | all fusion | ablate ATAC branch (`z_A` → outer-train mean) | N/A: N10_ladder_missing |
| I2 | all fusion | ablate RNA branch (`z_B` → outer-train mean) | N/A: N10_ladder_missing |
| I3 | CA, gated, program-CA | permute ATAC rows within donor × author_cell_type (20 draws) | N/A: N10_ladder_missing |
| I4 | CA, program-CA | attention knockout (context → outer-train mean) | N/A: N10_ladder_missing |
| I5 | MIL arms | uniform mean pooling instead of attention | N/A: N10_ladder_missing |
| I6 | gated | clamp routing to [1,0], [0,1], [0.5,0.5] | N/A: N10_ladder_missing |
| NC | all | identity permutation must give Δ = 0 exactly | N/A: N10_ladder_missing |
| PC | N4 S5/S4 at δ=1.0 | I3 must reduce planted-task BA if pairing was used | N/A: no saved planted model |

Acceptance: `NC exact zero` **NOT MET** (no model); `all applicable cells filled or N/A with
reason` **MET**. Full record: `docs/nn_v2/faithfulness.json`.
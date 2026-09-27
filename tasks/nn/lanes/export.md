# Lane export log (N15)

- iter1 N15: read brief, todo.md N15, decision_tree.md N15 + G2, swarm plan S2/S3, and
  status files. Confirmed the input N15 needs (per-fold fitted ladder models) does not
  exist: `reports/generated/nn_20260923/` (symlink to main checkout) has only `N2/`,
  `planted/`, `gene_activity/`, `logs/`, `N2_smoke.log`, `gene_activity.pid`; no `ladder/`
  dir, and `find` over the repo shows no ladder `*.pt`/`*.npz` (only unrelated
  `artifacts/*.pt` from the older pilot). `tasks/nn/status/N10` =
  `BLOCKED:lane_stalled:no commit in 3 attempts`; the ladder lane log ends at "N9 DONE.
  Next: N10." and N10's runner/summarizer were never written (commit 0f9fbbe).
  N15's decision-tree section has no fallback for a blocked dependency, and G2 says
  "ELSE mark BLOCKED:upstream <id>". Resolved N15 = `BLOCKED:upstream N10`. The
  chr21-excluded-arm export sub-part is `NOT_NEEDED` (no models exist to read).
  No code files touched; no `spectrum/cell_scores.csv.gz` or
  `docs/nn_v2/donor_celltype_scores.csv.gz` written. Learnings: (a) the N10->N15 artifact
  contract was never implemented — N15 needs saved per-fold models to recompute per-cell
  `s_i`/`a_i` via `MILWrapper.forward_bag_full`; (b) the `ladder_summary.json` gate file
  for S2 is also absent, so S3+ downstream of the ladder (N11–N17) is blocked at source.
  Verified N15's would-be dependencies are healthy in code: `tests/test_nn_factory.py`,
  `tests/test_nn_mil.py`, `tests/test_nn_contrastive.py` pass and ruff is clean on
  `src/p22/eval/nn_factory.py` + `src/p22/models/mil.py`.
- iter2 N15: N10 is now DONE. Wrote `scripts/export_nn_v2_cell_scores.py` and `tests/test_nn_export.py`. Wrote `tasks/nn/run/N15.json` to execute the export script and compute cell scores. Status remains TODO pending run completion.
- iter3 N15: Fixed KeyError 'cell_id' in scripts/export_nn_v2_cell_scores.py by using metadata.index instead of column access. Requesting re-run via tasks/nn/run/N15.json. Status remains TODO.
- iter4 N15: The background run N15 ended with exit 0 and successfully exported 120,000 rows to reports/generated/nn_20260923/spectrum/cell_scores.csv.gz and 1800 rows to docs/nn_v2/donor_celltype_scores.csv.gz. Marked N15 as DONE.
- iter5 N15: Wrote `scripts/export_nn_v2_cell_scores.py` and `tests/test_nn_export.py`. Recomputed `chr21_dosage` using outer-train fit standard scaler. Saved model loop iterates over testing cells. Requested run via `tasks/nn/run/N15.json`. Status set to TODO pending execution.
- iter6 N15: Fixed KeyError 'data' in scripts/export_nn_v2_cell_scores.py by changing protocol["data"]["cell_cap"] to protocol["sampling"]["cap_per_donor"] and protocol["data"]["sampling_seed"] to protocol["sampling"]["seed"]. Requested run via tasks/nn/run/N15.json. Status remains TODO pending execution.
- iter7 N15: Fixed missing union_bed argument and IndexError for parsing regions in scripts/export_nn_v2_cell_scores.py. Requested run again via tasks/nn/run/N15.json. Status remains TODO pending execution.
N15: Fixed paths and added multi-ladder export support; requested run.
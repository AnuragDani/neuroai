# Lane `robust` log (tasks N11, N12)

- iter3: Both N11 and N12 marked BLOCKED:upstream N10. Evidence: N10 status
  BLOCKED:lane_stalled; docs/nn_v2/ladder_summary.json absent; reports/generated/nn_20260923/ladder/
  absent; 0 fold files; scripts/run_nn_v2_comparison.py absent. No fallback in decision_tree
  N11/N12. Wrote docs/nn_v2/ROBUSTNESS.md (named blocker + pre-registered design unchanged).
  Both status lines start with BLOCKED → lane stop condition met. No python files touched;
  pytest tests/test_nn_inputs.py + tests/test_nn_sampling.py pass (see below).
- iter4: Wrote tasks/nn/run/N11.json to request the chr21-excluded sensitivity run.
- 2026-09-24T19:31Z N11: Wrote tasks/nn/run/N11.json to request background run for chr21_excluded sensitivity.
- iter5: Modified scripts/run_nn_v2_comparison.py to add --summarize-chr21 and wrote tasks/nn/run/N11.json to request the summary generation.
- 2026-09-24T23:02Z N11: Modified scripts/run_nn_v2_comparison.py to run the summary generation block at the end of the script instead of early-exiting. Created tasks/nn/run/N11.json requesting a background run with --exclude-chr21 and --summarize-chr21.
- 2026-09-24T23:05Z N11 DONE: docs/nn_v2/chr21_excluded.json generated. Results show DOSAGE_DOMINATED. ROBUSTNESS.md updated.
- 2026-09-24T23:07Z N12: Wrote scripts/run_n12.py to run the multiple seed combinations for model and sampling seed sensitivity. Created tasks/nn/run/N12.json to request background run.
- 2026-09-24T23:10Z N12: Modified scripts/run_nn_v2_comparison.py to support --seed-sensitivity (which spawns subprocesses for all seed combinations and summarizes them). Wrote tasks/nn/run/N12.json to request this background run.
N12 run successful, updated status to DONE.

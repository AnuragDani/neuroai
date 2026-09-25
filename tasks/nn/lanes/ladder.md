# Lane ladder log (N9, N10)

- iter1 N9: recovered `src/p22/eval/nn_factory.py` + `tests/test_nn_factory.py` from the
  iteration-1 SSE log; fixed tests to pass `CFG` for adversary arms and accept the 10%
  parameter-match fallback. 29 passed, ruff clean.
- iter2 N9: gathered frozen inputs (tie-break 465 region set at
  `configs/atac_tiebreak_region_sets_2026-09-21.json`, A13 architecture defaults,
  data cardinalities library=37 batch=12, n_hvg=2000, per-fold regions=256). Generated
  `docs/nn_v2/parameter_counts.json` (18 arms; `R3_tc_parammatched` rel. err 1.10%),
  `configs/nn_protocol_v2_2026-09-23.json` (protocol_sha256
  `80931bfc05c403804db47f53b02b29989204a6c04720476cb752dd62968b7161`), and
  `docs/nn_v2/PROTOCOL_FREEZE.md`. 29 passed, ruff clean. N9 DONE. Next: N10.
- 2026-09-24T18:12Z N10a DONE: wrote scripts/run_nn_v2_comparison.py, scripts/summarize_nn_v2.py, tests/test_nn_runner.py
- 2026-09-24T18:17Z N10a DONE (retry): fixed cell_meta passing in scripts/run_nn_v2_comparison.py to fix test failure.
- 2026-09-24T18:27Z N10b RUN_REQUESTED: wrote scripts/n10b_checks.py and tasks/nn/run/N10b.json to run the reproduction check and timing probe.
- 2026-09-24T18:32Z N10b RUN_REQUESTED: wrote tasks/nn/run/N10b.json calling scripts/run_nn_v2_comparison.py --n10b.
- 2026-09-24T18:34Z N10b RUN_REQUESTED (retry): fixed missing atac_matrix path in reproduction run and re-requested N10b run.
- 2026-09-24T18:36Z N10b RUN_REQUESTED: fixed run_nn_v2_comparison.py to output the correct fields for the acceptance check, and wrote run request N10b.json.
- 2026-09-24T18:41Z N10b RUN_REQUESTED: wrote tasks/nn/run/N10b.json to trigger the driver. Did not use shell.
- 2026-09-24T18:44Z N10b RUN_REQUESTED: fixed atac_historical_counts to atac_tiebreak_counts in scripts/run_nn_v2_comparison.py.
- 2026-09-24T18:48Z N10b RUN_REQUESTED: recovered from accidental headless tool execution by writing run request N10b.json strictly as a file edit without invoking the shell.
- 2026-09-24T18:50Z N10b RUN_REQUESTED: Fixed n_folds=1 error in smoke test by changing to n_folds=5 in run_nn_v2_comparison.py and requested a background run.
- 2026-09-24T18:54Z N10b RUN_REQUESTED: Fixed missing NMF program fitting for R4 arms in run_nn_v2_comparison.py and requested foreground run for N10b.

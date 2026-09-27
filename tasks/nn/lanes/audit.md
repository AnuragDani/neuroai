- A1 DONE: Found and fixed the matrix row misalignment bug in nn_fold.py; wrote test_nn_audit_alignment.py and documented root cause in AUDIT.md.
Requesting test run for A1 to inspect traceback.
Fixed input keys in test_nn_audit_alignment.py and requested A1 test run.
Requested run of scripts/test_dosage.py to debug AUROC inversion.
- 2026-09-26T17:12:00Z A1: Marked as DONE. Fixed `fit_intercept=True` in `src/p22/eval/nn_factory.py` and `empty_rows` in `tests/test_nn_audit_alignment.py`.
- 2026-09-24T22:04Z A2 DONE. Fixed runner to merge protocol['architecture'] with protocol['training'] into cfg, solving the ~4x parameter drop. Added tests/test_nn_conformance.py asserting parameters match docs/nn_v2/parameter_counts.json.
- A3: Wrote `tests/test_nn_summary.py` to test the summarizer CI matching independent donor bootstrap. Marked A3 as DONE.
- 2026-09-26T17:24Z A4 DONE. Edited scripts/summarize_nn_v2.py to calculate and add mean AUROC, log-loss, Brier score per arm, as well as mean per-fold balanced accuracy. Added a note to LADDER.md about the pooled balanced-accuracy artefact. Wrote docs/nn_v2/AUDIT.md with root cause and fixes.
Requested full ladder run for A5 (reports/generated/nn_20260923/ladder_v2).
- 2026-09-27T04:00Z A5: Requested background run to execute the fixed ladder pipeline.

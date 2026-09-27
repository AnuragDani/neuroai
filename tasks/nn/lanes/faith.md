# Lane faith (N13, N14) — lane log

- iter1 — recon: read plan §4.2, decision_tree N13/N14/N17, todo N10/N13/N14, status files,
  `docs/nn_v2/`, `src/p22/eval/nn_factory.py`, `src/p22/models/{fusion,cross_attention,mil,program_tokens}.py`,
  `tests/test_nn_factory.py`. Confirmed N13/N14 = TODO; no `faith.md`; no `scripts/run_nn_v2_*`.
- iter2 — BLOCKED resolution. Evidence: N10 = `BLOCKED:lane_stalled:no commit in 3 attempts`;
  `reports/generated/nn_20260923/ladder/` absent; no `*.pt`/`*.pth` anywhere in worktree;
  `scripts/run_nn_v2_comparison.py` absent; N10 grid points (needed for N13's refit path) only
  existed inside the absent fold JSONs; N4 saved no planted model for PC. Wrote
  `docs/nn_v2/faithfulness.json` (all I1–I6/NC/PC = N/A: N10_ladder_missing; tags NOT_SHOWN_USED
  per decision_tree N17), `docs/nn_v2/FAITHFULNESS.md`, `docs/nn_v2/nuisance_probe.json`
  (R2_UNEVALUATED). Set status N13 = BLOCKED:N10_ladder_missing, N14 = BLOCKED:N10_ladder_missing.
  No Python written (real-data run infeasible; harness would be unverifiable dead code).
- Wrote scripts/run_nn_v2_faithfulness.py and requested driver to run it for N13
# S7-v2 T4 — executed-path audit (zero fits)

Date: 2026-09-29. Audit only; **zero model fits**. Does not authorize T6+. T5 live no-fit preflight remains required before Checkpoint B.

## Scope

Audit the reused S7 path that v2 will execute: generator labels → fold plant → fit/score → ledger → screen → pairing-PC → conditional confirmation → handoff. No speculative stack rewrite. Source modules under review: `s7_setup.py`, `s7_runner.py`, `s7_ledger.py`, `s7_screen.py`, `s7_pairing.py`, `s7_pairing_exec.py`, `s7_confirmation.py`, `s7_confirm_exec.py`, `s7_pipeline.py`, `s7_handoff.py`, `scripts/run_nn_s7_covariance.py`.

## Scientific risks and evidence

| Risk | Control in executed path | Evidence | Status |
|---|---|---|---|
| Screen treats missing or `single_class` rows as PASS | `_ok_frame` keeps only `status=="ok"`; `screen_coverage` requires all 105 cells; incomplete → `INCOMPLETE`, not eligible for PC | `s7_screen.py`; `tests/test_nn_s7_screen.py` (`test_screen_coverage_requires_all_105`, `test_evaluate_screen_labels` including explicit `single_class` case) | PASS |
| Null/marginal design failure labelled favourable | Failed null or marginal → `SCREEN_INVALID`; handoff maps to `INVALID` | `evaluate_screen`; `finalize_scientific_label` | PASS |
| Ordinary lack of CA advantage opens confirmation | `SCREEN_NEGATIVE` → pipeline skips confirmation (`ACTION_WRITE_HANDOFF`); handoff `CONTROL_NEGATIVE` | `next_stage_action`; `tests/test_nn_s7_pipeline.py` | PASS |
| PC runs / PASSes without CA rho=1 checkpoints | Missing selection → `PC_INCOMPLETE`, `eligible_for_confirmation=False`; no invented predictions | `run_pairing_pc_diagnostic`; pipeline PC_INCOMPLETE step test | PASS |
| Confirmation starts after failed screen/PC | `next_stage_action` sets `confirmation_eligible` only when `CA_FAVOURED_SCREEN` **and** `PC_PASS`; otherwise skip confirmation | `s7_pipeline.py`; confirm-not-in-actions pipeline tests | PASS |
| `CA_FAVOURED_CONTROL` without all three stages | Handoff requires `CA_FAVOURED_SCREEN` + `PC_PASS` + `CONFIRM_RELIABLE` only | `finalize_scientific_label`; `tests/test_nn_s7_handoff.py` | PASS |
| Fit budget / smoke overrun | Ledger refuses beyond 480 total and 14 smoke; smoke enumeration capped | `S7FitLedger.record_fit`; `tests/test_nn_s7_ledger.py` | PASS |
| Post-freeze hash change continues fitting | `assert_resume_hashes` marks invalid and refuses further writes | `s7_ledger.py`; resume-hash ledger tests | PASS |
| Disk / artifact caps bypassed on live v2 | `check_disk_resources` (≥11 GiB free, ≤2 GiB artifacts); `--split-v2` refuses `--skip-disk-check` | `s7_runner.py`; CLI `run_nn_s7_covariance.py` | PASS |
| V2 CLI aliases v1 durable root | `resolve_s7_paths(protocol_version="v2")` + path disjointness | Checkpoint A; T3 path tests | PASS |
| Preflight class support skipped (v1 defect) | V2 all-seed no-fit preflight validates 11×5 partitions before ledger freeze / fits | T2 helpers + refusal tests; live run still T5 | PASS (code); live T5 pending |
| Generator / planted label mismatch | Planted vs full-cohort label agreement in v2 preflight; runner plants with fold cell IDs | T2 preflight; `fold_cell_ids` + plant path | PASS (code) |
| CA/TC parameter gap >10% | Preflight `preflight_param_match(S7_PROTOCOL)` before fits | CLI `run_preflight` | PASS (code); live T5 pending |
| Redundant / dead code bloating review | No clearly redundant executed-path deletions found without behavior risk; leave stack intact | Code review this audit | No deletion (intentional) |

## Targeted repairs this audit

| Change | Why | Behavior impact |
|---|---|---|
| Explicit `single_class` case in `tests/test_nn_s7_screen.py` | T4 acceptance requires proof that unscorable rows cannot PASS screen; prior tests covered missing rows only | Test-only; production gates unchanged |
| Symlink `reports/generated/nn_20260923` → main P22 generated ladder tree | Worktree initially had 0 ladder folds; full suite 21 failures were all canonical-path resolution, not S7 regressions | Gitignored local artifact link; no source/spec change |

No fitting-source edits. No scenario/margin/seed/model changes. No redundant-code deletion (would expand freeze surface without shrinking scientific risk).

## Verification commands and live counts (2026-09-29)

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts \
  /Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -m pytest \
  tests/test_nn_s7_*.py tests/test_nn_planted.py tests/test_nn_planted_benchmark.py -q
# → 110 passed in 7.36s; git diff --check clean

# Worktree initially lacked reports/generated/nn_20260923 (canonical ladder);
# first full suite: 21 failed / 1357 passed, all failures were ladder_v3/path
# resolution with 0 folds. Justified environment repair: symlink
# reports/generated/nn_20260923 → main P22 reports/generated/nn_20260923
# (gitignored artifacts; no scientific source change). Re-run:
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts \
  /Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -m pytest -q
# → 1378 passed, 22 warnings in 115.21s
```

V1 ledger fingerprints unchanged: `fit_ledger.jsonl` sha256 `5e23387a…`, `provenance.json` `d9e941d2…`. V2 durable root still absent. **Zero fits.**

## Gate decision

**T4 PASS.** Executed-path gates refuse missing/`single_class` screen PASS, missing-checkpoint PC PASS, confirmation after failed screen/PC, and `CA_FAVOURED_CONTROL` without screen+PC+reliability. Focused+adjacent 110 passed; full suite 1378 passed after artifact symlink. Authorize T5 live no-fit preflight only (still zero fits until 55/55).

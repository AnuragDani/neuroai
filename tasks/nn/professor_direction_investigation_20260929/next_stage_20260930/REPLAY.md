# Q1 REPLAY — next_stage diagnostics 2026-09-30

**Disposition:** Q1 PASS.  
**Recorded:** 2026-09-30 (local worktree).  
**Scope:** reproducible replay of the three immutable diagnostic JSONs, focused refusal tests, and canonical ladder verifier without `--write`. No fits, downloads, or package installs.

## Commands and exit codes

Interpreter: `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python`  
`PYTHONPATH=<this worktree>/src`  
`p22.__file__` = this worktree `src/p22/__init__.py`

| Step | Command | Exit | Wall |
|---|---|---|---|
| Fresh replay + golden exact compare | `scripts/replay_next_stage_diagnostics.py --output-dir reports/generated/nn_next_stage_q1_replay_20260930 --require-matrix-sha256 5f13c089…f969 --require-ordered-cells-sha256 7a56c2a9…9e53 --require-bed-sha256 d20d437a…bc23` | **0** | ~2.4 s |
| Overwrite refusal | same `--output-dir` re-invoked | **2** | — |
| Focused + inherited tests | `pytest tests/test_next_stage_diagnostic_replay.py tests/test_nn_sampling.py tests/test_nn_inputs.py -q` | **0** (17 passed) | ~1.7 s |
| Ladder verifier (no `--write`) | `gnhf/verify_ladder.py --run <shared ladder_v3> --summary docs/nn_v2/ladder_summary.json --protocol configs/nn_protocol_v2_2026-09-23.json --counts docs/nn_v2/parameter_counts.json` | **0** (`verdict=PASS`, `advantage=false`) | — |

Shared ladder_v3 root (read-only):  
`/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v3/`

## Fresh raw root (gitignored)

`reports/generated/nn_next_stage_q1_replay_20260930/`

| Fresh file | SHA-256 | Exact match to immutable expected |
|---|---|---|
| `DATA_DIAGNOSTIC.json` | `74e0dc0d7b40eab927769ce505e1daba8520d584e9eed078e5d0f84f91d78782` | yes (byte-identical) |
| `MEASUREMENT_AUDIT.json` | `f94deb5f81e1a2f6fca7175ab939ba4fb02035f363683e6bf0120c56d45d25d0` | yes (byte-identical) |
| `TARGETED_SAMPLING_FEASIBILITY.json` | `5c0fbd58d6c33db43c005e1c34fb6f82990efbe4d0fbe4c8ab2a0599a662b8d9` | yes (byte-identical) |
| `REPLAY_COMPARISON.json` | status `PASS`; records per-file match | n/a |

Immutable expected copies remain under  
`tasks/nn/professor_direction_investigation_20260929/next_stage_20260930/` (not modified).

## Exact comparisons recorded

- Donor/class/cell totals, age-from-donor-id table, and all donor×type ≥20 support counts: exact.
- Targeted sample IDs (`cap=64`, `seed=22`, `sample_donor_stratified_cells`): exact.
- Matrix / ordered-cell / BED SHA-256 and panel descriptive stats: exact.
- Floating fields compared with zero absolute/relative tolerance (exact equality); no declared float slack needed because fresh payloads matched golden bit-for-bit after JSON round-trip.

## Ladder verifier

Fresh `gnhf/verify_ladder.py` (no `--write`) returned **`PASS`** with primary `advantage=false` (`B_NULL` preserved). Recomputed CI endpoints can differ at last ULP from the tracked `docs/nn_v2/ladder_verification.json` because bootstrap resampling is not bit-frozen across process runs; the gate verdict and `advantage=false` are what authorize the verifier claim. `DATA_DIAGNOSTIC.primary` continues to cite the tracked verification record (exact match to golden).

## Refusal regressions (new)

`tests/test_next_stage_diagnostic_replay.py` covers:

1. Existing output directory → nonzero exit / `refusing to overwrite`
2. Missing required obs columns → `DiagnosticReplayError`
3. Tampered required matrix SHA-256 → refuse
4. Changed cell order vs ATAC sidecar `cells_sha256` → refuse
5. Golden-record drift detection via `compare_records`

## Preserved scientific labels

Primary `B_NULL`; study `STUDY_PARTIAL`; power `POWER_UNESTABLISHED`; S7-v1/v2 `INVALID`; prior S8 `NO FIT`. No experiment protocol frozen; no fits authorized.

## Next

Q2–Q5 independent read-only reports (endpoint / regulatory coverage / sampling-age support / external feasibility). Checkpoint A after Q1–Q3.

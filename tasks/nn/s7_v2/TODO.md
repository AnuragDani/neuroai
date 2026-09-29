# S7-v2 Cursor task list

Source of truth: [PLAN.md](PLAN.md) and frozen [BENCHMARK_SPEC.json](BENCHMARK_SPEC.json). Check boxes only after acceptance evidence saved. Current state: T1–T5 + Checkpoint A DONE (live no-fit preflight 55/55 PASS; zero fits); Checkpoint B–T10 not started. Old S7-v1 is `INVALID`, immutable. Run tasks in order; fail-fast dependencies apply.

## Phase 1 — zero-fit implementation

### T1: Deterministic donor allocation — S; depends: none

Description: Implement S7-v2-only SHA256 donor rank/quota splitter in existing S7 setup path. No change to real-data or v1 split code. Likely files: `src/p22/eval/s7_setup.py`, `tests/test_nn_s7_setup.py`.

- [x] Acceptance: 16/14 donor labels allocate outer quotas 4/2 then 3/3×4, six test donors/fold, once-only coverage; inner validation four/class, 16 train donors.
- [x] Acceptance: donor overlap/purity refusal; metadata row-order invariance and deterministic replay.
- [x] Verify: focused splitter tests, including refusal of duplicate/mixed-label donors; zero model fits.
  Evidence: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts …/.venv-p22/bin/python -m pytest tests/test_nn_s7_setup.py -q` → **15 passed**; `git diff --check` clean. Helpers: `allocate_s7_v2_donor_folds`, `collect_s7_v2_donor_labels`, `s7_v2_split_digest` in `src/p22/eval/s7_setup.py`. v1 StratifiedGroupKFold path unchanged.

### T2: All-seed no-fit preflight — M; depends: T1

Description: Validate screen plus all ten confirmation seeds before opening result ledger. Likely files: `src/p22/eval/s7_setup.py`, `scripts/run_nn_s7_covariance.py`, `tests/test_nn_s7_setup.py`.

- [x] Acceptance: manifest covers 11 seeds × five folds, each train/val/test 16/8/6 donors and both classes; no overlap, once-only tests, cell-ID and planted/full-label match.
- [x] Acceptance: injected single-class fold prevents any fit call/row/checkpoint; one invalid confirmation seed blocks entire batch.
- [x] Verify: focused negative test and independent manifest re-count; no model fits.
  Evidence: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts …/.venv-p22/bin/python -m pytest tests/test_nn_s7_setup.py -q` → **19 passed**; `git diff --check` clean. Helpers: `build_s7_v2_all_seed_split_manifest`, `validate_s7_v2_allocation`, `run_s7_v2_all_seed_nofit_preflight`, `guarded_s7_v2_call`, `S7V2PreflightError`/`INVALID_PREFLIGHT`; `prepare_s7_folds(..., split_method="v2")`; CLI `--split-v2` / `--all-seed-preflight`. Versioned durable root remains T3.
### T3: Versioned CLI, root and provenance — M; depends: T1–T2

Description: Use v2 protocol ID/spec/result root and fresh durable ledger; old path read-only. Likely files: `src/p22/eval/s7_setup.py`, `scripts/run_nn_s7_covariance.py`, `tests/test_nn_s7_setup.py` or `tests/test_nn_s7_ledger.py`.

- [x] Acceptance: v2 absolute paths cannot alias v1; new ledger empty; v1 ledger/result hashes unchanged.
- [x] Acceptance: spec/source/input/split-manifest hashes frozen before fit; changed hash refuses resume.
- [x] Verify: path/provenance tests and `realpath` audit; no model fits.
  Evidence: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts …/.venv-p22/bin/python -m pytest tests/test_nn_s7_setup.py -q` → **24 passed**; `git diff --check` clean. Helpers: `S7_V2_PROTOCOL_ID` / `S7_V2_DURABLE_ROOT` / `S7_V2_SPEC_REL` / `S7_V2_RESULT_REL`, `resolve_s7_paths(..., protocol_version=)`, `assert_s7_v2_paths_disjoint`, `build_provenance(..., protocol_version=, split_manifest_sha256=)`; CLI `--split-v2` resolves v2 durable/result roots and refuses `--skip-disk-check`. V1 ledger hashes unchanged; v2 durable root not created by path tests (empty until live preflight).

### Checkpoint A — zero-fit code gate

- [x] T1–T3 focused checks pass; `git diff --check` pass.
- [x] V2 spec diff versus v1 limited to split, all-seed preflight, identity/paths. No model, margin, scenario or seed changes.
- [x] Old v1 result/ledger unchanged. Any conflict or unplanned scientific change stops before fitting.
  Evidence: [CHECKPOINT_A.md](../../../docs/nn_v2/s7_v2/CHECKPOINT_A.md). `pytest tests/test_nn_s7_setup.py -q` → **24 passed**; `git diff --check` clean. Scientific blocks identical (models/screen/PC/confirmation/evaluation.margin/scenario/seeds); only id/paths/split/preflight/scope+resumption prose differ. V1 `fit_ledger.jsonl` sha256 `5e23387a…`, `provenance.json` `d9e941d2…`; v2 durable root still absent; **zero fits**.

### T4: Executed-path audit — S–M; depends: checkpoint A

Description: Audit reused S7 generator→fit→ledger→score→PC→confirmation→handoff path; targeted deletion/repair only before freeze. Likely files: `src/p22/eval/s7_*.py`, existing S7 tests, short audit report. Limit each edit slice to ≤5 files.

- [x] Acceptance: coverage requires all scoreable jobs; PC requires checkpoint identity; confirmation gate cannot bypass screen+PC; no post-fit source edits.
- [x] Acceptance: redundant code removal is behavior-preserving; no speculative stack rewrite.
- [x] Verify: focused S7 tests, adjacent N3/N4 planted tests, full suite once after final source edit, `git diff --check`; save test counts and audit.
  Evidence: [T4_EXECUTED_PATH_AUDIT.md](../../../docs/nn_v2/s7_v2/T4_EXECUTED_PATH_AUDIT.md). Explicit `single_class` screen INCOMPLETE assertion added in `tests/test_nn_s7_screen.py` (test-only). No fitting-source edits; no redundant deletions. Focused `tests/test_nn_s7_*.py` + planted → **110 passed**; full suite → **1378 passed** after justified worktree symlink `reports/generated/nn_20260923` → main P22 artifacts (first full run had 21 ladder-path fails with 0 folds). `git diff --check` clean. V1 ledger hashes unchanged; **zero fits**.

### T5: Live no-fit preflight — S; depends: T4

Description: Run v2 `--preflight-only` on real configured inputs, inspect all declared seed splits, hashes and resource headroom. Likely outputs: v2 preflight/split manifest and audit log; no code edits after PASS without repeating T4.

- [x] Acceptance: 55/55 train/val/test triplets class-valid; 30 donors/seed; CA/TC ≤10%; input hashes and cell mappings recorded.
- [x] Acceptance: v2 ledger has zero fit rows; old result/ledger unchanged; disk ≥11 GiB and path separation confirmed.
- [x] Verify: independent manifest parser prints per-seed/fold class counts, unique test donors, split hash; zero-fit evidence saved. Any fail → `INVALID_PREFLIGHT`, stop.
  Evidence: [T5_LIVE_NOFIT_PREFLIGHT.md](../../../docs/nn_v2/s7_v2/T5_LIVE_NOFIT_PREFLIGHT.md), [T5_LIVE_NOFIT_PREFLIGHT.json](../../../docs/nn_v2/s7_v2/T5_LIVE_NOFIT_PREFLIGHT.json), [T5_PREFLIGHT_STDOUT.json](../../../docs/nn_v2/s7_v2/T5_PREFLIGHT_STDOUT.json). CLI `--split-v2 --preflight-only` exit 0; `split_manifest_ok=true`, `n_seeds=11`, `n_triplets=55`, independent recount PASS with empty problems; seed 1001 fold-0 test classes `{0:4,1:2}` (v1 was `{6,0}`); CA/TC relative_error=0.011752 matched; free_gib=26.647; v2 fit_ledger absent/0 rows; v1 ledger `5e23387a…` / provenance `d9e941d2…` unchanged; durable `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929/`; `split_manifest_sha256=9a845b5c…`. **Zero fits.** Checkpoint B still required before T6.

### Checkpoint B — fit authorization by frozen evidence

- [ ] Record clean source/spec/config/input/split hashes, Git commit, zero-fit ledger, passed tests and resource snapshot.
- [ ] Freeze code before T6; post-fit fitting-source change invalidates v2, no same-task restart.

## Phase 2 — one bounded synthetic batch

### T6: Smoke — S; depends: checkpoint B

Description: Fit fixed rho 0/1 × fold 0 × seven models only. Likely outputs: v2 ledger, CA/TC checkpoints and prediction sidecars.

- [ ] Acceptance: 14/14 scoreable rows, finite donor metrics, both held-out classes and reload identity ≤1e-6.
- [ ] Verify: ledger/checkpoint/sidecar audit; cumulative fits ≤14. Any invalid/missing/changed hash stops before T7.

### T7: Complete fixed screen — S; depends: T6

Description: Run 105 declared screen jobs only; fixed rho-1 decision after coverage.

- [ ] Acceptance: 105/105 scoreable rows; rho-0 BA 0.35–0.65 all arms; rho-1 single-view BA ≤0.60; CA minus best non-attention ≥0.07 plus existing N4 regime for PASS.
- [ ] Verify: recompute pooled/fold metrics, CIs, control gates from raw rows; cumulative attempts ≤119. Negative/invalid gate prevents confirmation.

### T8: Pairing PC — S; depends: T7

Description: Reload saved rho-1 CA/TC; 32 within-donor ATAC shuffles, no new fits.

- [ ] Acceptance: checkpoint identity, ATAC within-donor marginal preservation and predeclared seed list; CA donor log-loss drop CI lower >0 for PASS.
- [ ] Verify: donor/seed coverage, 1000 bootstrap draws and ≥950 valid draws; report BA drop secondary. PC diagnostic after negative screen cannot unlock T9.

### T9: Conditional confirmation — M; depends: T7 PASS + T8 PASS

Description: Run fixed ten seeds × five folds × seven models, rho 1; skip entirely unless eligible.

- [ ] Acceptance: 350/350 scoreable distinct jobs, pooled 30 donors/seed; frozen joint CA−TC and six-baseline contrasts, count/10 plus Wilson intervals.
- [ ] Verify: independent paired-bootstrap recomputation; planned total ≤469 and absolute ≤480; ≥8/10 is synthetic reliability only. Ineligible/partial run records precise skip/incomplete reason.

### Checkpoint C — scientific gate

- [ ] Scientific label derived from raw coverage and gates: `CA_FAVOURED_CONTROL`, `CONTROL_NEGATIVE`, `INVALID`, or `INCOMPLETE`.
- [ ] `CA_FAVOURED_CONTROL` requires complete screen+PC+confirmation; no biological `A_ADVANTAGE` claim.

## Phase 3 — handoff

### T10: Report, verify, commit locally — M; depends: T6–T9 as applicable

Description: Produce versioned v2 Markdown/JSON result with evidence links, budget, hashes, and stop reason; update status/index only at gate or blocker. Likely files: `docs/nn_v2/s7_v2/S7_V2_RESULT.md`, JSON, `status.md`, `docs/INDEX.md`.

- [ ] Acceptance: all numbers trace to ledger; v1 `INVALID` remains; biological `B_NULL`, `POWER_UNESTABLISHED`, `STUDY_PARTIAL` explicit.
- [ ] Acceptance: no canonical JSON/gate, real-label, professor packet/MOM, push, merge, acquisition or new package changes.
- [ ] Verify: focused checks, saved-record recount, `git diff --check`, local commit and clean worktree; precise blocker if incomplete.

### Checkpoint D — done

- [ ] T10 result/handoff complete even if control negative or invalid; GNHF stopped, no new jobs pending under frozen rules.
- [ ] User can review branch, raw v2 ledger and scientific label without consulting GNHF iteration count or notes.

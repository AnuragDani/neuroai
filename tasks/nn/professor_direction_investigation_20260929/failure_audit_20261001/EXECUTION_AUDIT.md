# EXECUTION_AUDIT — R3 RNG / execution / resource accounting

**Disposition:** `EXECUTION_AUDIT_PASS`
**Date:** 2026-10-01
**Diagnostic fits this run:** 12
**Cumulative diagnostic fits:** 12 ≤ 12
**Research fits:** 0
**Shared S9 raw unchanged:** `True`
**Review status:** `PASS`

## Executor dependency hashes

Chain SHA-256: `05945cafb97aa18dd30e6c4597ca7b00ed48f33a0e95a3e8c82a7184c9cc3192`

| Rel path | SHA-256 |
|---|---|
| `src/p22/eval/multiome_protocol.py` | `422d77621fb301377df8d231a3f582f1b93c29c14d4e2fa4b371bd71566632b1` |
| `src/p22/eval/multiome_runner.py` | `119f93e269eee11a27b93e29f1c85a192b25793d9fad28e546bba99c93abd0b5` |
| `src/p22/eval/s7_ledger.py` | `e018cd03d5ea9353a10f71afd8b636576f4e0a50207b84d5624a8890a93467f7` |
| `src/p22/eval/s7_pairing.py` | `6475afd4d3d9e21ded6ce73b61e629a21ab10b8a11977cb2b56ed83652cef61e` |
| `src/p22/eval/s7_runner.py` | `b86a495a66771b8b736dbd4aba61d12b2b603d73a6138f406e24e37b4679d6e9` |
| `src/p22/eval/s9_analytic.py` | `dad126cd6dc33e9e8226b9924baa7c0b0fd3e88f8b413a6b06c9313c06d4ea02` |
| `src/p22/eval/s9_execute.py` | `b05eeb67a6742da6df596abbbc1979619871682eb7bf77bf814235b76748390a` |
| `src/p22/models/baselines.py` | `64258573821aae8f88ba5e69ba1d2035c99516c68c1201456abb6f426ddaf625` |
| `src/p22/models/cross_attention.py` | `b7c37e412f2c535b77a3962c58c3873f0e9ddbd6e0bed4f0a9d46f2740566e67` |
| `src/p22/models/fusion.py` | `6af42731f310ce0798aa092aeca3a21c728ad54414eba767fce4047a1a3d0987` |
| `src/p22/training/loop.py` | `195274bf29284e17746bef20020394737d175666361c5537fb0cdac1df347c1a` |

## Global seed / fit caller inventory

Files with relevant defs/calls: **10**.

Primary S9 path: `s9_execute.run_one_s9_fit` → `fit_s7_arm` → `paired_model` (`set_all_seeds`) → `train_model` (`set_all_seeds` + local `torch.Generator` for batch shuffle).

### Concurrent RNG risk (code path; effect unmeasured here)

- Default workers×threads: **2×2**
- ThreadPoolExecutor used: `True`
- Process-global `set_all_seeds`: `True`
- Interference code path exists: `True`
- Effect on outcomes: **NO_DIVERGENCE_OBSERVED_UNDER_SPEC**
- Inferred from threading alone: `False`

S9 execute_jobs with workers=2 submits run_one_s9_fit → fit_s7_arm → paired_model(set_all_seeds) → train_model(set_all_seeds) on concurrent threads sharing process-global RNG. Code path permits cross-job races; outcome impact requires frozen diagnostic fits after independent review.

## Ledger / resume / resource enforcement

- Pre-dispatch total attempt-cap check: `True`
- Per-job reserve before `pool.submit`: `False`
- Failed attempts counted: `True`
- Resume skips done fit_ids: `True`
- Hours tracked post-hoc: `True`
- Hours hard-stop mid-batch: `False`
- Artifact cap checked: `True`
- Checkpoint learning history persisted: `False`

### Notes

execute_jobs checks planned remaining against cap once before the batch, then submits all remaining jobs; counter increments only in _persist after each fit returns (serial on main via as_completed). No per-job pre-increment/reserve before pool.submit.

fitting_seconds accumulate in _persist; within_fitting_hours is reported in the batch summary. No mid-batch break when hours exceed SYNTHETIC_FITTING_HOURS_CAP during execute_jobs.

save_s9_checkpoint stores state_dict + protocol dims; no learning history/epochs (R1 uncertain_optimization retained).

## Frozen diagnostic fit spec

- Spec id: `r3_rng_thread_diag_20261001`
- Path: `tasks/nn/professor_direction_investigation_20260929/failure_audit_20261001/R3_DIAGNOSTIC_FIT_SPEC.json`
- SHA-256: `9e534c6132a1f2a6c003671a811a5eda3e762db6fe4a8a26604529583abba123`
- Attempt cap: 12
- Status: **frozen; diagnostic fits gated on independent PASS review**

## Repair posture (conditional)

No runner repair in this read-only pass. If diagnostic fits later confirm cross-job divergence under workers=2, smallest repair is serial default (`workers=1`); process isolation only if serial cannot eliminate the interference. Any shared-code change needs caller search + regression.

## Scientific label

Prior S9 **`INVALID` retained**. R3 does not overturn INVALID.

## Diagnostic fit results (post-review)

- Attempts: 12 ≤ 12
- Wall seconds: 0.753
- RNG finding: **NO_DIVERGENCE_OBSERVED_UNDER_SPEC**
- Repair recommendation: `none_required_from_this_diagnostic`
- Deliberate fail status: `error: ValueError: donor_ids is empty`
- Resume skip status: `skipped_already_done:A11`
- Results: `tasks/nn/professor_direction_investigation_20260929/failure_audit_20261001/r3_diagnostic_results.json`

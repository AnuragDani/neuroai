# M8 — Independent full executor / dependency review (masked ATAC pilot)

**Reviewer identity:** cursor Task generalPurpose agent (independent of M0–M7 authoring session and of cycle-0 reviewer)  
**Agent ID:** `85a8e8e7-0d66-4336-91c1-d3e018ba54c8` (runtime agent transcript folder UUID)  
**Date:** 2026-10-01  
**Protocol under review:** `masked_atac_pilot_20261001`  
**Scope:** claim-level-2 computational masked-measurement prediction (NOT biological state / causal / external)  
**Interpreter:** `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python`  
**PYTHONPATH:** `<workspace>/src`  
**git commit at review:** `8fe4d3858f0f936d03e01adf369265577c3775f0` (authorization binds **working-tree** file hashes)  
**Correction cycle:** 1 of max 2  
**Self-certification:** false

Worker self-assertion was not used. File SHA-256 digests, attempt arithmetic, CA/TC param counts, M6 lock validity, learning-gate behavior (including temporary fake locks, deleted after), reserve-before-dispatch durability, serial skip/replay, `skip_fits` authorization path, attempt counters, and focused M1–M7 + M8-correction tests were recomputed by this reviewer. No neural smoke/main research fits were run. Toy-array adapter unit learning inside dry-run/tests does not mutate owned attempt counters (still 0).

Machine record: [NO_FIT_REVIEW_M8.json](NO_FIT_REVIEW_M8.json). External lock: [M8_REVIEWED_HASHES.json](M8_REVIEWED_HASHES.json).

---

## Overall verdict

**PASS**

Cycle-0 critical findings **M8-C1 / M8-C2 / M8-C3 are resolved** in post-correction `masked_atac_execute.py`. Live digest verification against `REQUIRED_LOCK_KEYS`, durable reserve-before-dispatch, serial `workers=1` dispatch with completed-fit skip, and `run_authorized_pilot(skip_fits=True)` no-learning path were independently proved. M6 protocol lock still valid. Focused suite **30 PASS**, exit 0. Prior S10/S9/S7 `INVALID`, S8 `NO FIT`, primary `B_NULL`, Q2 `ENDPOINT_UNRESOLVED` unchanged. **`fits_authorized = true`**; **`smoke_learning_authorized = true`**; **`checkpoint_c_may_proceed = true`**. This review does **not** mark Checkpoint C (`checkpoint_c_marked = false`). No fits in this review. Authorization binds working-tree hashes below; any code/protocol change requires re-review.

---

## Cycle-0 findings — resolution status

1. **M8-C1 (learning gate / live hash match) — RESOLVED.**  
   `refuse_unreviewed_learning` → `verify_reviewed_hashes` requires `verdict==PASS`, `fits_authorized`, complete 64-hex digests for all `REQUIRED_LOCK_KEYS`, and live SHA-256 match. Independent proof with temporary fake locks under the task dir (deleted after): empty PASS refused; partial PASS refused; hash mismatch refused; current FAIL lock refused; complete matching PASS accepted.

2. **M8-C2 (reserve-before-dispatch / crash-safe counters) — RESOLVED.**  
   `reserve_attempt_before_dispatch` increments and writes `reserved_fit_ids` / used counters to disk **before** `fit_fn`. Re-read from disk confirmed. Owned production counter untouched (tmp counters only).

3. **M8-C3 (serial dispatch / skip_fits replay) — RESOLVED.**  
   `execute_jobs_serial` runs with `workers=1`, `parallel_dispatch=False`, skips `completed_fit_ids` without refit. `run_authorized_pilot(skip_fits=True)` authorizes under matching PASS lock and returns `learning=False` / `n_executed_this_call=0` (no fit_fn dispatch). FAIL lock still refuses even with `skip_fits=True`. Implicit learning refused when `skip_fits=False` and `fit_fn is None`.

---

## Exact hashes recomputed (SHA-256)

| Artifact | Recomputed SHA-256 |
|---|---|
| `PLAN.md` | `a9bf38e474e868bd0b32403cce5998ee825bde78e6947e9b28bf19bfbbe0e834` |
| `PILOT_PROTOCOL.md` | `178b9927483f8487c563be39553bfe889bd1b9288fd481536a9c0169862c98b0` |
| `PILOT_PROTOCOL.json` | `925560d95c18c28d528ea61ee040849037393d643836ee1c61b3ba56e0638249` |
| `BUDGET_LEDGER.md` | `e9f0809afca5966b7fc42c10cec28688183f4dbaa5f322e43fd58dcc56e2002e` |
| `budget_ledger.json` | `0c1251d41d22921ef2f09fdd67752be349baa324f644620ec42fd279e2777980` |
| `FALSIFICATION.md` | `08f28f037e36596378db8f909ecd013d8675b4d94596f0dc6362b122931f62a2` |
| `FALSIFICATION.json` | `20514e94873b46faf99bebd0077e3e44765d5df0c4193dc2267ef342002f4341` |
| `TARGET_FEASIBILITY.md` | `d3dfce63abe64b256cee558a6bc09a357bd48a2514173374ac336f586ff930e0` |
| `target_feasibility.json` | `09b6a5cf6c809f8674e661821d1dff933849e33f205910415b243c36940f9c3a` |
| `INPUT_AND_MASKING.md` | `4b56ecca59e85cab71f02100b43e4c8c67b6d2688bbd47d70b98d8ff5144cf39` |
| `input_and_masking.json` | `bbd02573dce3c74ca6a0c86e79ec51dd55ee6987d99afc9b3a922f2b66510922` |
| `SPLITS_AND_SAMPLING.md` | `8bd75c14449e94f143afd3bbd3d3046c835e006d20f511fb9e02fd0d15a4137a` |
| `SPLITS_AND_SAMPLING.json` | `3375f744825e0c383aecb410c9d8af2d6eb9887e7671a0ff18e624753a46f64f` |
| `CHECKPOINT_A.md` | `f5f8b9c59b1cc3e3f727e4c70d3ace75e939d78b4dec18402abe4699a6f403e7` |
| `CHECKPOINT_B.md` | `407e16f23f45b742a860538f33368dd051fc3995dc53c7162cf1f8799155ba18` |
| `PREFLIGHT.md` | `81e4eddce459a940ee5650067535d367a553af25d2e62c784bf8fc10b84a6645` |
| `IMPLEMENT.md` | `b6d08f253871b9272bbf87c9a087785d4d51fd3c2cc46babc07685e49e0deac0` |
| `implement.json` | `bd4be2ab01929ba89b0cc11075905cce4089a7cd7bf51ab733d4da610a32660c` |
| `M6_REVIEWED_HASHES.json` | `865ca57d9bfd3ccffae89f9e4e838d4689ff544dd7a8e1a592dcd9fe0b81adc4` |
| `src/p22/eval/masked_atac_target.py` | `c771f1069a9a6d40c3107efd65131f762af4285799eb01ef07e395b555d0cd02` |
| `src/p22/eval/masked_atac_splits.py` | `9c54324234cd3cffd5f622604bda00aee966b1147e205179b83cf182f1e8f415` |
| `src/p22/eval/masked_atac_metrics.py` | `64553c501ac3a0619d97fcdc547d7fb98a96555ab3d3f8ccea9cee2fc019a9c5` |
| `src/p22/eval/masked_atac_protocol.py` | `1ad3fdb97a470573254569195e712a7376ce1f1e581722c7aa3eb5939d22fb5d` |
| `src/p22/eval/masked_atac_adapter.py` | `cda024a4e0812c7ba76cb435b6e4cfd66de2879d408413f4a6a2d5f19068aae6` |
| `src/p22/eval/masked_atac_execute.py` | `a9798c008689489ac913563a978726e2011a3e10cdb08f77d42df954a93987aa` |
| `tests/test_masked_atac_input_and_masking_m1.py` | `fe0dd488e5a086c33adc0d280f4616ae4fc0d385ab8d26e3076e80a6062956ad` |
| `tests/test_masked_atac_target_feasibility_m2.py` | `f4ab6ddcaf859ffcd3c7cda030435cd108235d0236b3998427d16b76124ab0a1` |
| `tests/test_masked_atac_splits_m3.py` | `56dee1036b36fcf7d75e5b9339c63da5e6ce9f0c84405395e6cbdb81b8f61c9f` |
| `tests/test_masked_atac_falsification_m4.py` | `373fca78764affeb1941094b9dde6391c55ab5fdfe9dbd8820ec5297b5d7ab2a` |
| `tests/test_masked_atac_protocol_m5.py` | `986e301284fe6e43a45001078a4def5aadb40a5ffe938e1650f4cf9a136d82d0` |
| `tests/test_masked_atac_implement_m7.py` | `fb4f9d3d092061b61ba7d86738cc1152a07fe39ba68ed70ecd41eb21fe3e55e8` |
| `tests/test_masked_atac_executor_m8_correction.py` | `d669c8a0bd824531bae631fff5f6a9f32b59985422485cee8dcfef46a18d6e69` |
| `reports/generated/.../attempt_counter.json` | `5a801b6c1aa821b4e11ad8058f044c11efb3b65d0ff8af1112b00b606e1b8be1` |

**M6 protocol lock still valid:** `true` (all M6-locked digests including `PILOT_PROTOCOL.json` unchanged). Executor digest changed vs cycle-0 (expected post-correction).

**External lock keys (`REQUIRED_LOCK_KEYS` / `M8_REVIEWED_HASHES.reviewed_hashes`):** the ten keys verified by the live gate (short basenames / `src/` / `reports/` paths). This file’s own digest is **not** included.

**Optional dependency digests (not lock keys):**  
`multiome_runner.py` `119f93e2…abd0b5`; `s7_runner.py` `290b5e27…d84790`; `training/loop.py` `195274bf…347c1a`; `mil_loop.py` `6956d200…d428e0`.

---

## Checklist (PLAN M8 / acceptance)

1. **Executor full path exists — PASS.** `masked_atac_execute.py` + adapter; `run_authorized_pilot` / `execute_jobs_serial` / dry-run present.
2. **M6 protocol lock still valid — PASS.** Recomputed M6-locked hashes match `M6_REVIEWED_HASHES.json`.
3. **Attempt arithmetic — PASS.** 25 main + 5 smoke ≤ 40; constant arm 0 fits; headroom 10; 30 planned jobs.
4. **Serial workers / threads — PASS.** `WORKERS=1`, `TORCH_THREADS=2`; serial loop `parallel_dispatch=False`.
5. **Reserve / crash-safe / overwrite / unique root — PASS.** Reserve writes before `fit_fn`; overwrite + owned raw-root refusals intact.
6. **Learning blocked unless M8 lock present and matches — PASS.** Empty/partial/mismatch/FAIL refuse; matching PASS accepts (proved with temp locks).
7. **Mixed-label adapter — PASS.** Equal-donor mean cell log-loss; disease APIs still refuse mixed labels (M7 tests + dry-run contracts).
8. **Chromosome-mask / visible-only TF-IDF — PASS.** Intact via M1–M5 contracts + focused tests.
9. **CA/TC param-match ≤10% — PASS.** Live recompute RNA128×ATAC{423,430,440}: rel_err ≈0.0472 / 0.0467 / 0.0461.
10. **Replay/skip-fits / dry-run zero learning — PASS.** `skip_fits` no-learning path; serial skip completed; owned counters still 0 after this review.
11. **Claim level 2 + prior labels — PASS.** Claim level 2; `B_NULL` / S7·S9·S10 `INVALID` / S8 `NO FIT` / Q2 `ENDPOINT_UNRESOLVED` preserved; no biological/causal/external promotion.
12. **Focused tests M1–M8-correction — PASS.** 30 passed, exit 0 (run under pre-PASS FAIL lock state).

---

## Focused tests (reviewer)

```bash
cd <workspace> && PYTHONPATH=<workspace>/src \
  /Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -m pytest \
  tests/test_masked_atac_input_and_masking_m1.py \
  tests/test_masked_atac_target_feasibility_m2.py \
  tests/test_masked_atac_splits_m3.py \
  tests/test_masked_atac_falsification_m4.py \
  tests/test_masked_atac_protocol_m5.py \
  tests/test_masked_atac_implement_m7.py \
  tests/test_masked_atac_executor_m8_correction.py -q
```

Exit 0; **30 passed**.

---

## Independent recompute

| Quantity | Value |
|---|---|
| Main fits | 25 (5 learned × 5 folds) |
| Smoke fits | 5 |
| Constant arm fits | 0 |
| Intended total / hard cap / headroom | 30 / 40 / 10 |
| Workers × torch threads | 1 × 2 |
| CA/TC param-match (423/430/440) | matched; rel_err ≈0.0472 / 0.0467 / 0.0461 |
| attempt_counter used | scientific/smoke/total = 0 (unchanged after review) |
| Protocol SHA-256 vs M6 | match `925560d95c18c28d528ea61ee040849037393d643836ee1c61b3ba56e0638249` |
| Gate empty/partial/mismatch/FAIL | all refuse |
| Gate complete matching PASS | accepts |
| `verify_reviewed_hashes` / reserve / `skip_fits` / serial | present and verified |
| Critical findings remaining | none |

---

## Non-critical notes

- Correction tests that hardcode “live lock is FAIL” will need authoring-session update after this PASS lock write; they do not indicate a fit-safety gap (suite was 30 PASS before writing PASS).
- M7 dry-run still reports `trainability_with_learning: REFUSED_UNTIL_M8` in its static field; post-PASS, `learning_refused_until_m8` check semantics change — authoring session should refresh dry-run reporting when marking Checkpoint C.
- Dependency modules (`multiome_runner`, `mil_loop`, etc.) remain outside `REQUIRED_LOCK_KEYS` (same pattern as cycle-0 / R8); changing them without re-review is still forbidden by policy even if the live gate does not hash them.
- This review does not edit `status.md` / `tasks/todo.md` and does not write `CHECKPOINT_C.md`.

---

## Checkpoint C authorization statement

**`checkpoint_c_may_proceed`:** true  
**`checkpoint_c_marked`:** false  
**`fits_authorized`:** true  
**`smoke_learning_authorized`:** true  

Checkpoint C may be marked by the **authoring session only** after verifying M6+M8 PASS locks still match live digests. No smoke/main fits were run in this review. No code/protocol change without re-review.

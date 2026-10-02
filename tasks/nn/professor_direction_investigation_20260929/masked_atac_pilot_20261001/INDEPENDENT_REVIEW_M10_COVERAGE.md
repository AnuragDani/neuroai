# M10 — Independent review-coverage audit (masked ATAC pilot)

**Reviewer identity:** cursor Task agent (independent scientific reviewer; not M0–M9 authoring / GNHF worker)  
**Agent ID:** `68919dae-61a9-4c39-80f7-5ad0845bbc03` (runtime agent transcript folder UUID)  
**Date:** 2026-10-02  
**Protocol:** `masked_atac_pilot_20261001`  
**Scope:** review-coverage audit only — no fits, smoke, refits, counter mutations, or M8 lock edits  
**Self-certification:** false  
**Fits run:** 0  
**Counters modified:** false  

**Review wall-clock (ISO UTC):**  
- start: `2026-10-02T14:41:23Z`  
- end: `2026-10-02T14:44:22Z`  
- duration: **2.98 minutes**

Machine record: [M10_COVERAGE_REVIEW.json](M10_COVERAGE_REVIEW.json).

Authority: PLAN “Resume amendment — 2026-10-02: M10 closeout only”. Matching the older locked wrapper does **not** establish review of the post-M8 real-data path. Retrospective inspection cannot retroactively satisfy the prospective executor-review gate.

---

## Verdicts

| Gate | Verdict |
|---|---|
| `prospective_executor_review_gate` | **FAIL** |
| `retrospective_path_inspection` | **PARTIAL** |
| `scientific_acceptance_of_M9` | **NOT_AUTHORIZED** (provisional diagnostic only) |

Historical **M8 PASS** for the wrapper it locked (`masked_atac_execute` / adapter / protocol helpers / zeroed counter) is left unchanged. This audit does not rewrite `INDEPENDENT_REVIEW_M8.md`, `NO_FIT_REVIEW_M8.json`, or `M8_REVIEWED_HASHES.json`.

---

## 1. Prospective executor-review gate — FAIL

**Rule:** PASS only if documented pre-fit independent review covered the real-data execution files with locked digests before learning began.

**Finding:** Commit `315d6a9` (2026-10-01 18:05:55 −0700) introduced `src/p22/eval/masked_atac_pilot.py` (733 lines) and `scripts/run_masked_atac_m9.py` **after** M8 PASS (`ff0f770`) and Checkpoint C (`2c3e85e`). Smoke learning is in the **same** commit that first added those files. No independent pre-fit review hashed or locked them.

Evidence:

1. At M8 review commit `8fe4d38` / M8 PASS `ff0f770` / Checkpoint C `2c3e85e`: `git cat-file` reports both files **absent**.
2. Live `M8_REVIEWED_HASHES.json` `reviewed_hashes` / executor `REQUIRED_LOCK_KEYS` list ten keys — neither `masked_atac_pilot.py` nor `run_masked_atac_m9.py` is among them; dependency notes likewise omit them.
3. Independent M6 (`d3e35bc3-…`) and M8 cycle-0/1 (`64da0eef-…`, `85a8e8e7-…`) transcripts contain **zero** mentions of `masked_atac_pilot.py` / `run_masked_atac_m9`.
4. Transcript `5065f65e-…` (GNHF iteration 16 worker) **authored** the new modules and dispatched smoke — authorship/execution, not independent pre-fit review.
5. Module docstring itself states the new path is “deliberately outside M8 `REQUIRED_LOCK_KEYS`”.

Therefore the prospective gate **FAIL**s. This retrospective audit does not upgrade it.

---

## 2. Recomputed SHA-256 (live worktree)

| Path | SHA-256 | Notes |
|---|---|---|
| `src/p22/eval/masked_atac_pilot.py` | `f8d86654b963011a03f94f31a8d91b3b3e003b4c818f7ccbfdee20685a51ffc1` | 733 lines; **absent from M8 lock** |
| `scripts/run_masked_atac_m9.py` | `f31374774d609c7ac62ebfbdffb5f0e506590d6654cdb81f44711b23b565c281` | 83 lines; **absent from M8 lock** |
| `src/p22/eval/masked_atac_execute.py` | `a9798c008689489ac913563a978726e2011a3e10cdb08f77d42df954a93987aa` | MATCH M8 lock |
| `src/p22/eval/masked_atac_adapter.py` | `cda024a4e0812c7ba76cb435b6e4cfd66de2879d408413f4a6a2d5f19068aae6` | MATCH M8 lock |
| `reports/generated/.../attempt_counter.json` | `2b4bd43c81460a7945bd5374ab2822d6bbf3440031f00639313387170857112a` | MISMATCH vs M8 zero digest `5a801b6c…` (expected after 30 progressed fits) |

Other `REQUIRED_LOCK_KEYS` rematched live and still MATCH M8 (protocol JSON, implement.json, M6 lock, protocol/metrics/splits/target modules). Counter progression alone does not restore review of the unlocked pilot path.

**Files absent from M8 lock (critical):**

- `src/p22/eval/masked_atac_pilot.py` → `f8d86654…51ffc1`
- `scripts/run_masked_atac_m9.py` → `f3137477…565c281`

---

## 3. Git timeline

| Commit | Time (local −0700) | Role | `masked_atac_pilot.py` / `run_masked_atac_m9.py` |
|---|---|---|---|
| `8fe4d38` | 2026-10-01 17:45:20 | M8 cycle-1 correction; `git_commit_at_review` in lock | **ABSENT** |
| `ff0f770` | 2026-10-01 17:51:39 | M8 independent PASS recorded | **ABSENT** |
| `2c3e85e` | 2026-10-01 17:54:12 | Checkpoint C fit authorization | **ABSENT** |
| `315d6a9` | 2026-10-01 18:05:55 | New unlocked real-data path + smoke 5/5 | **INTRODUCED** (same commit as learning) |
| `a221c67` | 2026-10-01 18:09:43 | M9 EXECUTE_COMPLETE (main 25/25) | present |

Order: M8 PASS → Checkpoint C → **new path + smoke** → main complete. No intervening independent review commit.

---

## 4. M8 artifacts vs new path

Read: `INDEPENDENT_REVIEW_M8.md`, `NO_FIT_REVIEW_M8.json`, `M8_REVIEWED_HASHES.json`.

- M8 locked and verified: executor wrapper, adapter, protocol/metrics/splits/target, M6 lock, implement/protocol JSON, **zeroed** attempt counter.
- M8 checklist covers dry-run / toy-array / `run_authorized_pilot` paths — **not** H5AD/NPZ real-data loaders, train-only variance selection, or `authorize_immutable_lock` / `allow_progressed_counter` resume that live only in the new module.
- `REQUIRED_LOCK_KEYS` and `dependency_hashes_not_in_lock` do **not** include the new pilot files.

Historical M8 PASS remains valid for what it locked. It does not cover M9’s actual fit dispatch entrypoint.

---

## 5. Transcript search (pre-fit coverage)

Searched worktree agent-transcripts for `masked_atac_pilot.py` / `run_masked_atac_m9` before/around learning:

| Transcript | Role | Pre-fit independent coverage of new path? |
|---|---|---|
| `d3e35bc3-…` (M6) | Independent protocol review | No (0 mentions of new files) |
| `64da0eef-…` (M8 cycle 0) | Independent executor FAIL | No |
| `85a8e8e7-…` (M8 cycle 1) | Independent executor PASS | No |
| `5065f65e-…` | GNHF iter 16 **worker** — wrote pilot module and ran smoke | Authorship/execution only |
| `a80bf4c6-…` / `85f9f814-…` | GNHF iters 17–18 M9 continuation | Post-introduction workers |

**No pre-fit independent review covering the real-data pilot path was found.**

---

## 6. Retrospective path inspection — PARTIAL

Inspected actual M9 path without running fits.

### Call chain

`scripts/run_masked_atac_m9.py` → `masked_atac_pilot.run_m9_jobs` → `authorize_immutable_lock` → `load_pilot_arrays` → `build_all_fold_features` / `build_fold_features` → `execute_jobs_serial(..., fit_fn=fit_one_job)` → adapter (`fit_logreg_cell_target` / `fit_neural_cell_target`) + metrics (`donor_average_cell_log_loss`, `visible_atac_tfidf_fit`).

### Contracts checked (descriptive)

1. **Chromosome masking:** Pilot refuses target index ∈ visible list and rematches M3 visible-index SHA. Whole-chromosome exclusivity is **not** re-asserted at fit time; it is inherited from frozen M3 visible indices (M1/M3 contracts). Sidecar targets match frozen labels (`chr19:…` / `chr3:…`); visible widths 423–440.
2. **Train-only preprocessing:** RNA top-variance + `fit_train_only` scaler on train rows; ATAC `visible_atac_tfidf_fit` with train-row IDF and visible-only panel depth, then train-only scale. Consistent with protocol intent.
3. **Mixed-label donor-average cell log-loss:** Used for train/val/test; selection metric `donor_average_cell_log_loss` / `donor_mean_of_cell_log_loss`. Sampled sidecars show mixed labels within all 6 test donors (fold 0 and fold 2).
4. **Budgets:** Protocol `NEURAL.feature_budget=128`, `max_epochs=20`, `patience=5`; sidecars show early stop (`epochs_run=6`, `stopped_early=true`). Workers=1 / torch_threads=2. Counter: smoke 5/5, scientific 25, total 30/40, failed 0.
5. **Counter / resume:** `authorize_immutable_lock` + `--allow-progressed-counter` rematches immutable keys excluding progressed counter; never requires resetting to the zero digest. Matches durable-resume design; still does not hash the pilot module itself.
6. **Prediction sidecars (sampled 2 smoke + 2 main):**  
   - `smoke__logreg_rna__fold0.json`  
   - `smoke__cross_attention__fold0.json`  
   - `main__token_concat__fold0.json`  
   - `main__cross_attention__fold2.json`  
   Schema: outer `{fit_id, stage, arm, fold, status, seconds, record}`; `record` carries target pins, encoded SHA pins, equal-length `test_cell_ids` / `test_donors` / `test_labels` / `test_probabilities` (1536), donor-average losses, `claim_level=2`, `preserved_labels` (`B_NULL` / S7·S9·S10 `INVALID` / S8 `NO FIT` / Q2 `ENDPOINT_UNRESOLVED`). Neural records add `initial_state_sha256`, `checkpoint_sha256`, `training` history.
7. **Attempt ledger:** `attempt_ledger.jsonl` has **30** lines matching the 30 completed fit_ids (status `ok`); same outer schema as sidecars.
8. **checkpoints/ and logs/:** directories exist under the raw root but contain **zero files**. Model state is pinned only via sidecar SHA fields, not on-disk checkpoint blobs. Recorded as an artifact-persistence gap relative to “preserve checkpoints” language.

### Why PARTIAL (not retrospective PASS)

- Path is largely consistent with frozen M1–M8 scientific contracts for masking inheritance, train-only transforms, mixed-label metrics, serial dispatch, and budget ceilings.
- Gaps: no runtime chromosome re-assert; empty `checkpoints/`/`logs/`; authorization deliberately excludes hashing the modules that actually load real data and build features; `artifacts_gib.used=0.0` is not a filesystem byte measurement (amendment already flags this).

Retrospective PARTIAL **does not** change prospective FAIL or authorize scientific acceptance.

---

## 7. Claim limits

- Claim level **2** (computational masked-measurement prediction) only.
- Prior labels **unchanged:** primary `B_NULL`; S7/S9/S10 `INVALID`; S8 `NO FIT`; Q2 `ENDPOINT_UNRESOLVED`.
- M9 numerical results (pooled TC−CA ≈ +0.00154, etc.) may be retained only as **diagnostic** evidence under prospective-gate failure.
- Do **not** silently promote scientific PASS / task DONE as scientific acceptance.

---

## 8. Evidence commands (executed; no fits)

```bash
date -u +"%Y-%m-%dT%H:%M:%SZ"
shasum -a 256 src/p22/eval/masked_atac_pilot.py scripts/run_masked_atac_m9.py \
  src/p22/eval/masked_atac_execute.py src/p22/eval/masked_atac_adapter.py \
  reports/generated/nn_masked_atac_pilot_20261001/attempt_counter.json
git log -1 --format="%H %ci %s" ff0f770 8fe4d38 2c3e85e 315d6a9 a221c67
git cat-file -e ff0f770:src/p22/eval/masked_atac_pilot.py   # ABSENT
git cat-file -e 2c3e85e:src/p22/eval/masked_atac_pilot.py   # ABSENT
git cat-file -e 315d6a9:src/p22/eval/masked_atac_pilot.py   # PRESENT
# live rematch of M8 reviewed_hashes (9 MATCH; counter MISMATCH as progressed)
# transcript rg for masked_atac_pilot.py among M6/M8/GNHF workers
# read pilot/execute/adapter/metrics; sample 4 prediction sidecars + ledger
find reports/generated/nn_masked_atac_pilot_20261001/checkpoints reports/generated/nn_masked_atac_pilot_20261001/logs -type f | wc -l  # 0
```

---

## Findings (numbered)

1. **Prospective executor-review gate FAIL:** real-data path (`masked_atac_pilot.py`, `run_masked_atac_m9.py`) was introduced and used for learning in `315d6a9` after M8/Checkpoint C without independent pre-fit hash lock.
2. Both new files are **absent** from git trees at `8fe4d38` / `ff0f770` / `2c3e85e`.
3. Live digests: pilot `f8d86654…51ffc1`, runner `f3137477…565c281` — not in `REQUIRED_LOCK_KEYS`.
4. M8 locked wrapper digests for `masked_atac_execute.py` / `masked_atac_adapter.py` still rematch; that rematch does **not** review the new path.
5. Attempt counter progressed to 30/40 (5 smoke + 25 main); live counter SHA ≠ M8 zero digest (expected).
6. No M6/M8 independent-reviewer transcript covered the new files; GNHF `5065f65e` authored and smoked them.
7. Retrospective inspection: train-only RNA/ATAC transforms, mixed-label donor-average losses, sidecar schema, and serial budget accounting appear protocol-consistent → **PARTIAL** (empty checkpoints/logs; no runtime chrom re-assert; unlocked modules).
8. `scientific_acceptance_of_M9` remains **NOT_AUTHORIZED**; M9 numbers are diagnostic only.
9. Historical M8 PASS left intact for the locked wrapper; not rewritten by this audit.
10. `fits_run=0`; `counters_modified=false`; M8 lock files not modified; `notes.md` not edited.

---

## Next decision implication

M10 closeout may continue with **diagnostic** replay under explicit prospective-gate failure. Scientific acceptance of M9 requires a separate prospective re-review/hash-lock of the real-data path **before** any further learning — which cannot be satisfied retrospectively for the already-completed fits.

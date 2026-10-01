# R3 — Independent review of frozen diagnostic fit spec

**Reviewer:** Task/generalPurpose (independent of authoring agent; `self_certification: false`)  
**Date:** 2026-10-01  
**Artifact under review:** `R3_DIAGNOSTIC_FIT_SPEC.json` (`spec_id: r3_rng_thread_diag_20261001`)  
**Scope:** Adequacy of the frozen diagnostic fit specification to authorize ≤12 code-path diagnostic fits. No diagnostic fits executed in this review. No S9 scientific performance authorization.

Authoring-agent self-certification was not used. Hashes, attempt counter, PLAN R3 acceptance language, audit gating script, and cited RNG/thread code paths were checked read-only by this reviewer.

---

## Overall verdict

**PASS**

The frozen spec is adequate to authorize the ≤12 diagnostic fits. Critical findings: none.

---

## Spec hash recompute

| Artifact | Audit SHA-256 | Recomputed | Match |
|---|---|---|---|
| `R3_DIAGNOSTIC_FIT_SPEC.json` | `9e534c6132a1f2a6c003671a811a5eda3e762db6fe4a8a26604529583abba123` | `9e534c6132a1f2a6c003671a811a5eda3e762db6fe4a8a26604529583abba123` | YES |

`attempt_counter.json` → `diagnostic_fit_attempts: 0` (cap 12). `scientific_fit_attempts: 0`.

---

## Checklist (must address each)

### 1. Spec frozen before fits — PASS

- `committed_before_any_diagnostic_fit: true`
- `attempt_cap: 12` (exactly 12 unique attempt ids A1–A12)
- `wall_minutes_cap: 15`
- `scientific_fits_allowed: 0`
- Live counter still 0; audit disposition `READ_ONLY_AUDIT_PASS` / `REVIEW_PENDING` before this review

### 2. Tensors / seeds / dims / epochs / jobs / tolerances fully specified, not outcome-driven — PASS

Frozen prospectively (attempts still 0): generator seed 7701, model seed 7701, 8 donors × 4 cells, RNA/ATAC width 4, labels `[0,0,0,0,1,1,1,1]`, frozen train/val/test donor indices (+ J2 swap), `gated_fusion` with embed/hidden 8, max_epochs 3, batch 8, lr 0.001, dropout 0, serial atol state `0.0` / preds `1e-12`, `report_all_differences: true`. Single fixed seed; not chosen from diagnostic outcomes.

### 3. Serial vs thread comparison probes global RNG race — PASS

Not a “threads exist” assertion. Spec schedules:

- Serial identity on J1 (A1/A2) and J2 (A3/A4)
- Concurrent `thread_pool_workers_2` pairs (A5/A6, A7/A8) compared to serial A1/A3 references
- Post-concurrent serial contamination check A9 vs A1
- Criteria: concurrent divergence ⇒ interference evidence; concurrent match does **not** prove absence of race

Code path reviewed: `s9_execute.WORKERS=2` + `ThreadPoolExecutor` → fit → `paired_model` (`set_all_seeds` before init) → `train_model` (`set_all_seeds` then local shuffle `Generator`). Process-global `random` / `np.random` / `torch.manual_seed` are shared across threads. Audit correctly leaves outcome effect `UNMEASURED_PENDING_DIAGNOSTIC_FITS`.

### 4. Deliberate failure + resume fixture inside 12-attempt cap — PASS

- A10: `serial_deliberate_fail` / `empty_train_indices`
- A11–A12: `serial_resume_fixture` (ledger write then resume skip / no double-count)
- Both consume named attempt ids within A1–A12 (12/12)

### 5. No S9 rescue / seed shopping / hidden calibration — PASS

`not_s9_rescue`, `not_favourable_seed_selection`, purpose limited to code diagnosis, `scientific_fits_allowed: 0`, fixed seed 7701, no S9 job list or performance gate in success criteria. Prior S9 `INVALID` retained in audit.

### 6. Repair posture prefers serial before process isolation — PASS

`repair_if_confirmed`: prefer `workers=1` serial default; process isolation only if serial cannot eliminate observed interference. Matches PLAN R3 and `EXECUTION_AUDIT.md`.

### 7. Self-certification forbidden; review gates fits — PASS

Spec `review_gate.required` + `self_certification_forbidden`. Script `audit_failure_audit_execution_r3.py` refuses `--run-diagnostic-fits` without `--review-json` whose `verdict == PASS`. This review is independent (`self_certification: false`).

### 8. Spec SHA-256 matches `execution_audit.json` — PASS

Recomputed digest equals `diagnostic_fit_spec.sha256`.

### 9. `diagnostic_fit_attempts` still 0 — PASS

Confirmed in `reports/generated/nn_failure_audit_20261001/attempt_counter.json`.

---

## Authorization

- **authorizes_diagnostic_fits:** `true`
- **max_diagnostic_attempts_authorized:** `12`
- Scientific / research fits remain **0** under this review
- Shared S9 raw must stay read-only; diagnostic outputs only under the audited raw root / ledger paths in the spec
- Operational note: the current script still exits that the diagnostic runner is not unlocked even after PASS; unlocking the runner is a separate implementation step and does not alter this spec PASS

---

## Non-critical findings

1. Tensor construction is recipe + seed, not byte-frozen arrays; runner should build arrays once and reuse the same buffers across serial/thread routes.
2. `torch_threads`, device, `gate_hidden_dim`, and donor-vs-cell selection unit rely on code defaults; pin them in the runner for serial bit-identity (`atol_state=0.0`).
3. Concurrent job_key zip order (A5→J1, A6→J2) is conventional, not spelled out field-by-field.
4. Gate script checks `verdict == PASS` only; reviewers must keep `self_certification: false` as required by the frozen spec.

## Critical findings

None.

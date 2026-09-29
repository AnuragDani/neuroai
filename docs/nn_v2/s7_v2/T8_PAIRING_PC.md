# S7-v2 T8 — Pairing PC diagnostic (no new fits) → `PC_FAIL`

Date: 2026-09-29. Depends on T7 COMPLETE (`screen_label=INVALID`). Machine audit: [T8_PAIRING_PC_AUDIT.json](T8_PAIRING_PC_AUDIT.json).

## Command

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts \
  /Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python \
  scripts/run_nn_s7_covariance.py --split-v2 --once
```

Logged at durable `pairing_pc_once.log`: START `2026-09-29T20:42:31Z` → END `2026-09-29T20:42:40Z`, EXIT=0 (~9s). CLI JSON reports planned action `run_pairing_pc` / reason `pairing-PC not evaluated (diagnostic allowed after any complete screen)`; post-run `stage_state.json` has `pc_label=PC_FAIL`.

## Coverage / identity

| Check | Result |
|---|---|
| Retained CA rho-1 checkpoints | **5/5** present (`screen__1__1001__{0–4}__cross_attention.pt`) |
| Selection | complete; missing `[]` |
| Checkpoint reload identity | **PASS** — `max_abs_diff=0.0` ≤ `atol=1e-6` |
| Intervention seeds | frozen **3001–3032** (n=32) |
| Held-out donors | **30** (6/fold × 5 folds) |
| Bootstrap | 1000 draws requested; **1000** valid (≥950) |
| New fits | **0** (ledger still 119 rows; sha256 `53920364…` unchanged vs T7) |
| Resources | free `26.617` GiB; artifacts `0.016` GiB; under caps |
| Provenance freeze | file sha256 `52cde0ba…` matches Checkpoint B |
| V1 immutable | ledger `5e23387a…`, provenance `d9e941d2…` unchanged |

## Gate recomputation (independent)

| Gate | Result |
|---|---|
| Identity | PASS |
| Seed / donor coverage | PASS (32 seeds; 30 donors) |
| Valid bootstrap draws | PASS (1000 ≥ 950) |
| CA mean donor log-loss drop CI lower > 0 | **FAIL** — estimate `−1.434e-4`, 95% CI `[−3.847e-3, 4.451e-3]`, lower ≤ 0 |
| BA drop (descriptive only) | estimate `0.0`, CI `[0.0, 0.0]` |
| `pc_label` | **`PC_FAIL`** |
| Confirmation eligible | **false** (screen already `INVALID`; PC cannot unlock T9) |

## Artifacts

| Path | Role |
|---|---|
| `…/stage_state.json` | `pc_label=PC_FAIL`; full `pairing_pc` payload |
| `…/ledger/fit_ledger.jsonl` | unchanged 119 rows (no PC fits) |
| `…/checkpoints/screen__1__1001__*__cross_attention.pt` | reloaded CA models |
| `…/pairing_pc_once.log` | CLI once log |

## Gate decision

**COMPLETE — T8 diagnostic done with `PC_FAIL`.** Within-donor ATAC shuffle does not raise CA donor log-loss (CI lower ≤ 0). Screen remains `INVALID`; confirmation remains ineligible; **T9 skipped**. No retuning or seed search. Next authorized stage is **T10 handoff only**. Biological primary remains `B_NULL`; power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`.

# S7-v2 T6 — Smoke (≤14 fits)

Date: 2026-09-29. Depends on Checkpoint B PASS. Machine audit: [T6_SMOKE_AUDIT.json](T6_SMOKE_AUDIT.json).

## Command

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts \
  /Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python \
  scripts/run_nn_s7_covariance.py --split-v2 --once
```

Logged at durable `smoke_once.log`: START `2026-09-29T20:30:24Z` → END `2026-09-29T20:30:38Z`, `EXIT=0` (~14s). CLI JSON reports planned action `run_smoke` / reason `smoke fits not complete` (pre-completion planner text); post-run `stage_state.json` has `smoke_complete=true`.

## Acceptance

| Check | Result |
|---|---|
| Predeclared smoke jobs | 14/14 `fit_id` match `enumerate_smoke_jobs()` |
| Ledger statuses | **14/14 `ok`** (zero `single_class` / error) |
| Finite donor metrics | BA / AUROC / log-loss finite for all 14 |
| Held-out classes (fold 0) | **both present**: `{0:4, 1:2}` on all 14 sidecars (v1 was `{6:0}`) |
| `n_test_donors` | 6 each |
| CA/TC rho=1 checkpoints | `smoke__1__1001__0__cross_attention.pt`, `smoke__1__1001__0__token_concat.pt` |
| Checkpoint reload identity | donor-vs-sidecar and cell double-reload `max_abs_diff=0.0` ≤ `atol=1e-6` for CA and TC |
| Cumulative fits | **14** (`smoke_is_complete=true`; remaining budget 466 / 480) |
| Resources | free `26.755` GiB; artifacts `0.003` GiB; both under caps |
| Provenance freeze | unchanged vs Checkpoint B (`spec` `e8b127ad…`, split content `9a845b5c…`, provenance file `52cde0ba…`) |
| Fitting sources | 13/13 hashes match Checkpoint B freeze |
| V1 immutable | ledger `5e23387a…`, provenance `d9e941d2…` unchanged |

## Ledger metrics (donor-level)

| fit_id | BA | AUROC | log-loss |
|---|---:|---:|---:|
| `smoke\|0\|1001\|0\|cross_attention` | 0.3750 | 0.1250 | 0.805826 |
| `smoke\|0\|1001\|0\|token_concat` | 0.3750 | 0.1250 | 0.807664 |
| `smoke\|0\|1001\|0\|rna_atac_concat` | 0.3750 | 0.1250 | 0.806395 |
| `smoke\|0\|1001\|0\|gated_fusion` | 0.2500 | 0.0000 | 1.026002 |
| `smoke\|0\|1001\|0\|logreg_concat` | 0.1250 | 0.0000 | 0.889224 |
| `smoke\|0\|1001\|0\|logreg_rna` | 0.0000 | 0.0000 | 0.893747 |
| `smoke\|0\|1001\|0\|logreg_atac` | 0.3750 | 0.2500 | 0.706295 |
| `smoke\|1\|1001\|0\|cross_attention` | 0.1250 | 0.1250 | 0.958601 |
| `smoke\|1\|1001\|0\|token_concat` | 0.3750 | 0.1250 | 0.805063 |
| `smoke\|1\|1001\|0\|rna_atac_concat` | 0.3750 | 0.1250 | 0.806959 |
| `smoke\|1\|1001\|0\|gated_fusion` | 0.1250 | 0.0000 | 0.820455 |
| `smoke\|1\|1001\|0\|logreg_concat` | 0.0000 | 0.0000 | 0.882974 |
| `smoke\|1\|1001\|0\|logreg_rna` | 0.0000 | 0.0000 | 0.893747 |
| `smoke\|1\|1001\|0\|logreg_atac` | 0.3750 | 0.2500 | 0.706766 |

Smoke does **not** decide screen PASS/FAIL. Low fold-0 BA under rho 0/1 is descriptive only.

## Artifacts

| Path | Role |
|---|---|
| `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929/ledger/fit_ledger.jsonl` | 14 smoke rows; sha256 `332febea…` |
| `…/donor_predictions/smoke__{0,1}__1001__0__*.donors.json` | 14 sidecars |
| `…/checkpoints/smoke__1__1001__0__{cross_attention,token_concat}.pt` | retained CA/TC |
| `…/stage_state.json` | `smoke_complete=true` |
| `…/resources_{pre,post}_fit.json` | disk/artifact gates ok |

## Gate decision

**PASS — T6.** Authorizes **T7 fixed screen only** (105 declared jobs; cumulative attempts ≤119). No retuning. Do **not** run full pipeline without `--once` until T7 is the intentional next stage. Biological primary remains `B_NULL`; power `POWER_UNESTABLISHED`.

# S7-v2 T7 — Fixed screen (105 fits) → `INVALID`

Date: 2026-09-29. Depends on T6 PASS. Machine audit: [T7_SCREEN_AUDIT.json](T7_SCREEN_AUDIT.json).

## Command

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts \
  /Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python \
  scripts/run_nn_s7_covariance.py --split-v2 --once
```

Logged at durable `screen_once.log`: START `2026-09-29T20:38:51Z` → END `2026-09-29T20:39:53Z`, `EXIT=0` (~62s). CLI JSON reports planned action `run_screen` / reason `screen not evaluated` (pre-completion planner text); post-run `stage_state.json` has `screen_label=INVALID`.

## Coverage

| Check | Result |
|---|---|
| Predeclared screen jobs | **105/105** `fit_id` match `enumerate_screen_jobs()` |
| Ledger statuses | **105/105 `ok`** (plus prior 14 smoke; total **119** rows, all `ok`) |
| Finite donor metrics | BA / AUROC / log-loss finite for all 105 |
| `n_test_donors` | 6 each |
| Held-out classes (all folds) | **both present**: fold0 `{0:4,1:2}`; folds1–4 `{0:3,1:3}` (0 single-class sidecars) |
| Cumulative fits | **119** ≤119 smoke+screen budget; remaining 361 / 480 |
| Resources | free `26.617` GiB; artifacts `0.016` GiB; under caps |
| Provenance freeze | unchanged vs Checkpoint B (spec/source/split hashes; provenance file `52cde0ba…`) |
| V1 immutable | ledger `5e23387a…`, provenance `d9e941d2…` unchanged |
| Retuning | **none** |

## Gate recomputation (independent)

| Gate | Result |
|---|---|
| Coverage | PASS (`n_expected=105`, `n_ok=105`, missing `[]`) |
| Rho-0 null BA ∈ [0.35, 0.65] | **FAIL** — `token_concat` mean-fold donor BA **0.341667** (fold BAs: 0.375, 0.5, 0.5, 0.0, 0.333…) |
| Rho-1 single-view ≤0.60 | PASS (`logreg_rna` 0.367, `logreg_atac` 0.475) |
| Rho-1 N4 `CA_FAVOURED` + CA−best-non ≥0.07 | Not reached / not met — regime `NONE_DETECT`, CA−best-non = **−0.083333** (best non-attention `rna_atac_concat`) |
| `screen_label` | **`INVALID`** (null/marginal design-control failure precedence) |
| Confirmation eligible | **false** |

Rho-0 mean-fold donor BA (all arms): CA 0.375, TC **0.341667**, RAC 0.375, GF 0.35, LC 0.392, LR 0.367, LA 0.475.

Rho-1 mean-fold donor BA: CA 0.325, TC 0.375, RAC 0.408, GF 0.358, LC 0.367, LR 0.367, LA 0.475.

## Artifacts

| Path | Role |
|---|---|
| `…/ledger/fit_ledger.jsonl` | 14 smoke + 105 screen; sha256 `53920364…` |
| `…/donor_predictions/screen__*.donors.json` | 105 sidecars |
| `…/checkpoints/screen__1__1001__{0–4}__{cross_attention,token_concat}.pt` | 10 retained CA/TC rho-1 checkpoints |
| `…/stage_state.json` | `screen_label=INVALID`; `confirmation_eligible=false` |
| `…/resources_post_fit.json` | disk/artifact gates ok |

## Gate decision

**COMPLETE — T7 stage done with scientific label `INVALID`.** Rho-0 null control failed on `token_concat` (0.341667 < 0.35). No confirmation fits. No retuning or seed search. Next authorized stage is **T8 pairing-PC diagnostic only** (no new fits; cannot unlock T9). Final handoff remains T10. Biological primary remains `B_NULL`; power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`.

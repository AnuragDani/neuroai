# Q4 — Sampling and age/class support feasibility

**Disposition:** `SUPPORT_REPAIR_PASS`  
**Eligibility:** `ELIGIBILITY_FROZEN`  
**Date:** 2026-09-30  
**Branch:** `gnhf/execute-the-p22-data-146414`  
**Dependency:** Q1 PASS; Q2 `ENDPOINT_UNRESOLVED` blocks biological cell-state pilot. No fits, downloads, package installs, or scientific-gate weakening.

Machine-readable: [sampling_feasibility.json](sampling_feasibility.json).

## Decision: does targeted sampling repair measured support loss?

**Yes — `targeted_sampling_repairs_measured_loss_of_support`.** Global per-donor cap underrepresents rare types; targeted `cap=64` / `seed=22` restores selected ≥20-cell donor support to the available ≥20 counts for:

- **AST**: global selected ge20 1/4 → targeted 10/10 (available 10/10)
- **IPC**: global selected ge20 14/15 → targeted 15/15 (available 15/15)
- **IPC_prol**: global selected ge20 11/13 → targeted 15/15 (available 15/15)
- **MIC**: global selected ge20 0/0 → targeted 9/10 (available 9/10)
- **NEU_CALB2**: global selected ge20 12/10 → targeted 15/15 (available 15/15)
- **NEU_RELN**: global selected ge20 2/4 → targeted 13/15 (available 13/15)
- **NEU_RORB**: global selected ge20 10/9 → targeted 15/13 (available 15/13)
- **NEU_SST**: global selected ge20 13/12 → targeted 15/15 (available 15/15)
- **NEU_TLE4**: global selected ge20 14/13 → targeted 14/15 (available 14/15)
- **NEU_low**: global selected ge20 1/0 → targeted 12/13 (available 12/13)
- **OPC**: global selected ge20 0/0 → targeted 12/13 (available 12/13)
- **RG_prol**: global selected ge20 11/13 → targeted 15/15 (available 15/15)
- **VASC**: global selected ge20 0/0 → targeted 8/8 (available 8/8)

Do **not** rerun the full ladder merely with more cells. Donor count, not cell count, drives replication.

## Global vs targeted support (selected donors with ≥20 cells)

| Type | Global CON/DS | Targeted CON/DS | Available CON/DS |
|---|---:|---:|---:|
| AST | 1/4 | 10/10 | 10/10 |
| IPC | 14/15 | 15/15 | 15/15 |
| IPC_prol | 11/13 | 15/15 | 15/15 |
| MIC | 0/0 | 9/10 | 9/10 |
| NEU_CALB2 | 12/10 | 15/15 | 15/15 |
| NEU_CUX2 | 15/15 | 15/15 | 15/15 |
| NEU_RELN | 2/4 | 13/15 | 13/15 |
| NEU_RORB | 10/9 | 15/13 | 15/13 |
| NEU_SST | 13/12 | 15/15 | 15/15 |
| NEU_TLE4 | 14/13 | 14/15 | 14/15 |
| NEU_low | 1/0 | 12/13 | 12/13 |
| OPC | 0/0 | 12/13 | 12/13 |
| RG | 15/15 | 15/15 | 15/15 |
| RG_prol | 11/13 | 15/15 | 15/15 |
| VASC | 0/0 | 8/8 | 8/8 |

Global selected cells: **30000** (cap 1000/donor). Targeted selected cells: **23591** (cap 64/donor/type). Golden targeted IDs: **exact match** (SHA-256 by type in JSON).

Label-free check (disease permute): **True**.

## Age / sex / library support

- One-class ages (excluded from age-matched claims): `['10', '14', '15']` → {'10': {'CON': 1}, '14': {'CON': 1}, '15': {'DS': 1}}
- Common ages (both classes): `['11', '12', '13', '16', '17', '18', '20']`
- Sex counts by class: `{'male': {'CON': 8, 'DS': 9}, 'female': {'CON': 7, 'DS': 6}}`
- Two-library donors: **7** / 30

Age is a **covariate**, not a cell-state endpoint (Q2).

## Fold class support (targeted, ≥20 cells/donor, frozen 5×5)

| Type | Eligible CON/DS | Both classes every fold | practical_margin | Split-feasible |
|---|---:|:---:|---:|:---:|
| AST | 10/10 | False | 0.1 | False |
| IPC | 15/15 | True | 0.07 | True |
| IPC_prol | 15/15 | True | 0.07 | True |
| MIC | 9/10 | False | 0.12 | False |
| NEU_CALB2 | 15/15 | True | 0.07 | True |
| NEU_CUX2 | 15/15 | True | 0.07 | True |
| NEU_RELN | 13/15 | True | 0.08 | True |
| NEU_RORB | 15/13 | True | 0.08 | True |
| NEU_SST | 15/15 | True | 0.07 | True |
| NEU_TLE4 | 14/15 | False | 0.08 | False |
| NEU_low | 12/13 | False | 0.09 | False |
| OPC | 12/13 | False | 0.09 | False |
| RG | 15/15 | True | 0.07 | True |
| RG_prol | 15/15 | True | 0.07 | True |
| VASC | 8/8 | False | 0.13 | False |

## Eligibility freeze (before effect analysis)

- Split-feasible types under frozen 5×5: `['IPC', 'IPC_prol', 'NEU_CALB2', 'NEU_CUX2', 'NEU_RELN', 'NEU_RORB', 'NEU_SST', 'RG', 'RG_prol']`
- Both-class ≥20 support but not 5×5 both-class every fold: `['AST', 'MIC', 'NEU_TLE4', 'NEU_low', 'OPC', 'VASC']`
- Biological cell-state pilot: **BLOCKED** (Q2 ENDPOINT_UNRESOLVED — no independent cell-state endpoint)
- Power: **`POWER_UNESTABLISHED`** — practical_margin / score_resolution below are donor-count score-grid descriptions for a stated donor-balanced-accuracy contrast; they are not established biological power or CI-width proxies.

Full-cohort 15+15 score-resolution / practical_margin: `0.03333333333333333` / `0.07` under donor-balanced-accuracy + donor-bootstrap inference (descriptive grid only).

## What this does and does not authorize

| Allowed next | Not authorized |
|---|---|
| Continue Q5 read-only external feasibility | Biological cell-state fit |
| Use frozen eligibility in Q6 ranking | Full-ladder rerun for more cells only |
| Synthetic controls that do not need a state endpoint | Calling CI width or planted amplitude established power |

## Verification commands

```bash
export PYTHONPATH="$(pwd)/src"
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -c "import p22; print(p22.__file__)"
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python scripts/report_next_stage_sampling_feasibility.py
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -m pytest tests/test_next_stage_sampling_feasibility_q4.py tests/test_nn_sampling.py -q
```

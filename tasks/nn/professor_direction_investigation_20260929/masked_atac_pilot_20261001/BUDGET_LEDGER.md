# BUDGET_LEDGER — M5 masked ATAC pilot resource arithmetic

**Date:** 2026-10-01
**Protocol:** `masked_atac_pilot_20261001`
**Fit feasibility:** `PASS`
**Machine record:** [budget_ledger.json](budget_ledger.json)

M5 itself uses **0** scientific fits, **0** smoke fits, **0** payloads. Figures below are the **prospective** M7–M9 budget against stage caps.

## Counter snapshot (before any learning)

| Resource | Used | Cap |
|---|---:|---:|
| Total attempts | 0 | 40 |
| Smoke fits | 0 | 5 |
| Fitting hours | 0.0 | 6.0 |
| Artifact GiB | 0.0 | 4.0 |
| Network bytes | 0 | 0 planned |

## Planned consumption

| Item | Value |
|---|---|
| Smoke fits | 5 (one per learned arm, fold 0; count toward hard cap) |
| Main fits | 25 (5 arms × 5 folds) |
| Constant arm | 0 |
| **Total intended** | **30** |
| Hard cap / headroom | 40 / 10 |
| Workers × threads | 1 × 2 |
| Arithmetic | 5 learned arms × 5 folds = 25 main; + 5 reserved smoke (one per learned arm, fold 0) = 30 intended; hard cap 40; headroom 10; constant arm = 0 fits |

## Feasibility checks

- `25_main_plus_5_smoke_le_40`: **True**
- `remaining_attempts_cover_planned`: **True**
- `counters_still_zero`: **True**
- `protocol_frozen`: **True**

**Fit feasibility:** `PASS`. Fit feasibility is **not** established statistical power.

## Policy

- Reserve attempt counter before dispatch; failed/smoke/timeout count.
- Never reset counters after interruption; do not refit completed jobs.
- No neural smoke learning before M8 authorization.
- No hyperparameter/seed/target sweep.

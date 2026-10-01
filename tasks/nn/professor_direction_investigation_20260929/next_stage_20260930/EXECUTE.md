# Q10 — Bounded S9 analytic pairing-use synthetic batch

**Disposition:** `INVALID`  
**Protocol ID:** `S9_analytic_pairing_use_synthetic_20260930`  
**Date:** 2026-10-01  
**Branch:** `gnhf/execute-the-p22-data-146414`  
**Research fits:** 49  
**Raw root:** `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-engineering-20260928-gnhf-worktrees/read-tasks-nn-finish-ee2202-gnhf-worktrees/read-users-anuragdan-b61180-gnhf-worktrees/execute-the-p22-data-146414/reports/generated/nn_s9_analytic_pairing_20260930`

Machine-readable: [execute.json](execute.json).

## Coverage

- Planned: 49; attempted: 49; ok: 49; failed: 0
- Complete: `True`

## Primary pairing (CA)

- ρ=1 label: `PAIRING_NEGATIVE`
- ρ=0 null label: `PAIRING_POSITIVE`
- Interpretation: rho=1 unimodal marginal BA exceeds 0.60 (logreg_rna/logreg_atac shortcut)

- Secondary findings:
  - also: fitted rho=0 pairing-plant null yielded PAIRING_POSITIVE
  - also: CA rho=1 pairing was PAIRING_NEGATIVE

## Advantage contrast (SEPARATE_NON_PRIMARY)

- CA BA: 0.625
- token_concat BA: 0.625
- CA−TC: 0.0

## Marginal check (ρ=1)

- logreg_rna BA: 0.75
- logreg_atac BA: 0.7083333333333334
- pass (≤0.6): `False`

## Resources

- Fits: 49 ≤ 60 (`True`)
- Fitting hours: 0.0015 ≤ 4
- Artifacts GiB: 0.003378 ≤ 2
- Workers×threads: 2×2

## Scientific invariants (unchanged)

Primary `B_NULL`; S7-v1/v2 `INVALID`; prior S8 `NO FIT`; power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`.

Unresolved flags retained: ENDPOINT_UNRESOLVED; REGULATORY_ADEQUACY_UNRESOLVED; EXTERNAL confirmatory UNRESOLVED.

## Q11

- Biological pilot: **BLOCKED** — Q2 ENDPOINT_UNRESOLVED (and Q3/Q5 unresolved) cannot unlock Q11

## Next

Q11 SKIPPED/BLOCKED (endpoint unresolved) or Q12 handoff after disposition recorded.

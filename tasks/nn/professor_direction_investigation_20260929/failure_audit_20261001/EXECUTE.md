# R9 — Bounded S10 corrected-null pairing-use batch

**Disposition:** `INVALID`  
**Protocol ID:** `S10_corrected_null_pairing_use_20261001`  
**Date:** 2026-10-01  
**Branch:** `gnhf/execute-p22-s-failur-d8f02c`  
**Research fits:** 49  
**Raw root:** `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-engineering-20260928-gnhf-worktrees/read-tasks-nn-finish-ee2202-gnhf-worktrees/read-users-anuragdan-b61180-gnhf-worktrees/execute-the-p22-data-146414-gnhf-worktrees/execute-p22-s-failur-d8f02c/reports/generated/nn_failure_audit_20261001/s10_corrected_null_pairing_20261001`  
**Mode:** `replay_saved_sidecars` (skip_fits=`True`)

Machine-readable: [execute.json](execute.json).

## Coverage

- Planned: 49; attempted: 49; ok: 49; failed: 0
- Complete: `True`

## Primary pairing (CA)

- ρ=1 label: `PAIRING_NEGATIVE`
- ρ=0 null label: `PAIRING_NEGATIVE`
- Interpretation: rho=1 unimodal marginal BA exceeds 0.60 (logreg_rna/logreg_atac shortcut)

- Secondary findings:
  - also: CA rho=1 pairing was PAIRING_NEGATIVE

## Advantage contrast (SEPARATE_NON_PRIMARY)

- CA BA: 0.4166666666666667
- token_concat BA: 0.4166666666666667
- CA−TC: 0.0

## Marginal check (ρ=1)

- logreg_rna BA: 0.3333333333333333
- logreg_atac BA: 0.625
- pass (≤0.6): `False`

## Resources

- Fits: 49 ≤ 90 (`True`)
- Fitting hours: 0.000740 ≤ 6.0
- Artifacts GiB: 0.003407 ≤ 4.0
- Workers×threads: 1×2

## Ruled in / not established

- Ruled in: Under corrected independent-Gaussian null, ρ=0 pairing gate is PAIRING_NEGATIVE (supports that S9 ρ=0 PAIRING_POSITIVE is explained by broken orthogonal-null exchangeability rather than requiring a leak claim from that alone).
- Not established / ruled out as claim: Method claim / biology upgrade from this software control
- Not established / ruled out as claim: Unimodal marginal PASS at ρ=1 under frozen joint gate
- Not established / ruled out as claim: CA ρ=1 PAIRING_POSITIVE under corrected null (observed PAIRING_NEGATIVE)

## Scientific invariants (unchanged)

Primary `B_NULL`; S9 `INVALID` immutable; S7-v1/v2 `INVALID`; prior S8 `NO FIT`; Q2 `ENDPOINT_UNRESOLVED`; power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`.

## Next

R10 verified handoff (no further fits; no positive-result search).

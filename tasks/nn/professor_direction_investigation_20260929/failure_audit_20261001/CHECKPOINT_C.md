# Checkpoint C — S10 scientific-fit authorization

**Date:** 2026-10-01  
**Branch:** `gnhf/execute-p22-s-failur-d8f02c`  
**Protocol:** `S10_corrected_null_pairing_use_20261001`  
**Disposition:** `PASS`

## Gates

| Gate | Status | Evidence |
|---|---|---|
| R7 protocol freeze | PASS | [S10_PROTOCOL.md](S10_PROTOCOL.md) `PROTOCOL_FROZEN` |
| R7 implement | PASS | [IMPLEMENT.md](IMPLEMENT.md) `IMPLEMENT_PASS` |
| R8 independent full-path review | PASS | [INDEPENDENT_REVIEW_R8.md](INDEPENDENT_REVIEW_R8.md); agent `fd860419-c20a-4e11-8c6f-f56ddc15fdec`; no self-certification |
| Exact reviewed hashes | LOCKED | [R8_REVIEWED_HASHES.json](R8_REVIEWED_HASHES.json); [NO_FIT_REVIEW_R8.json](NO_FIT_REVIEW_R8.json) |
| Diagnostic allowance | Exhausted | 12/12 (separate R3); smoke counts as scientific |
| Scientific fits so far | 0 | attempt counter |

## Authorization

Research fits for frozen S10 are authorized **only** under:

- Exact five lock hashes in `R8_REVIEWED_HASHES.json`
- Serial `workers=1`, torch threads=2
- Raw root `reports/generated/nn_failure_audit_20261001/s10_corrected_null_pairing_20261001/`
- Planned 49 ≤ 90 scientific fits; ≤6 fitting hours; ≤4 GiB artifacts; 0 payloads
- `NO_FIT_REVIEW_R8.json` verdict/disposition PASS with `checkpoint_c.authorized_by_review=true`

Code changed after this review invalidates affected authorization until re-reviewed.

## Scientific invariants (unchanged)

Primary `B_NULL`; S9 `INVALID` immutable; S7-v1/v2 `INVALID`; prior S8 `NO FIT`; Q2 `ENDPOINT_UNRESOLVED`; study `STUDY_PARTIAL`. Claim level 1 only.

## Next

R9 bounded S10 experiment under frozen hashes (or precise NO FIT if blocked). No positive-result search.

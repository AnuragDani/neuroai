# M7 — Minimal measured-target adapter (masked ATAC pilot)

**Disposition:** `IMPLEMENT_PASS`
**Protocol ID:** `masked_atac_pilot_20261001`
**Claim level:** 2 (computational prediction)
**Date:** 2026-10-01
**Research fits:** 0 (trainability-with-learning `REFUSED_UNTIL_M8`).

Machine-readable: [implement.json](implement.json); frozen [PILOT_PROTOCOL.json](PILOT_PROTOCOL.json); [M6_REVIEWED_HASHES.json](M6_REVIEWED_HASHES.json).

## Reuse

- Existing `paired_model` / `model_inputs` / `predict` (multiome_runner).
- Existing `donor_cell_weights` (s7_runner) for equal-donor cell weighting.
- Existing `visible_atac_tfidf_fit` (masked_atac_metrics) for visible-only ATAC.
- New: `p22.eval.masked_atac_adapter` (mixed-label cell-loss train/select) + `p22.eval.masked_atac_execute` (dry-run / M8 gate / refusals).
- Disease classification APIs (`mil_loop`, `train_model` donor-mode) unchanged and still refuse mixed cell labels.

## Adapter contract

- Selection metric: `donor_average_cell_log_loss` (minimize; mixed labels allowed).
- Requirements: donor-average of within-donor mean cell-target binary log-loss (equal donor weighting); do not substitute donor-average probability or invent a fake donor disease class
- Forbidden: donor-average probability / fake disease class as primary.

## Verification summary

- `m6_pass_authorizes_implement`: **True**
- `attempt_arithmetic_within_caps`: **True**
- `planned_jobs_30`: **True**
- `planned_main_25`: **True**
- `planned_smoke_5`: **True**
- `counters_still_zero`: **True**
- `mil_mixed_refused`: **True**
- `train_model_donor_mode_refuses_mixed`: **True**
- `adapter_mixed_label_train_ok`: **True**
- `selection_prefers_cell_log_loss`: **True**
- `constant_arm_zero_params`: **True**
- `logreg_probabilities_finite`: **True**
- `finite_gradients_all_neural`: **True**
- `reload_identity_all_neural`: **True**
- `ca_tc_param_match_toy_widths`: **True**
- `protocol_hash_mismatch_refused`: **True**
- `forbidden_raw_roots_refused`: **True**
- `allowed_raw_root_accepted`: **True**
- `overwrite_refused`: **True**
- `learning_refused_until_m8`: **True**
- `no_smoke_main_fits`: **True**
- `claim_level_2`: **True**

## Toy adapter fit (unit verification only)

- Arm: `token_concat`; epochs_run=3; best_epoch=3
- initial_state_sha256: `d8910a4b21106a0e6363ade86ebbc639610f010ccdce297ce16e49c02d001a95`
- checkpoint_sha256: `4f8719511c1b75ef0086f96fe0819a78ee1c06196a01b566f2b69e742c5afbab`
- Note: Toy-array unit verification only; does not reserve attempt counters and is not a smoke/main research fit

## Attempt arithmetic (unchanged)

- 5 learned arms × 5 folds = 25 main; + 5 reserved smoke (one per learned arm, fold 0) = 30 intended; hard cap 40; headroom 10; constant arm = 0 fits
- Within caps: **True**
- Workers × threads: **1 × 2**

## Hashes

- `PILOT_PROTOCOL.json`: `925560d95c18c28d528ea61ee040849037393d643836ee1c61b3ba56e0638249`
- `M6_REVIEWED_HASHES.json`: `865ca57d9bfd3ccffae89f9e4e838d4689ff544dd7a8e1a592dcd9fe0b81adc4`

## Scientific invariants (unchanged)

- primary: `B_NULL`
- S7: `INVALID`
- S9: `INVALID`
- S10: `INVALID`
- S8: `NO FIT`
- Q2: `ENDPOINT_UNRESOLVED`

## Next

M8 independent full executor/dependency hash review before any learning.

# Q8 — Minimal implement and falsification (S9 analytic pairing-use)

**Disposition:** `IMPLEMENT_PASS`  
**Protocol ID:** `S9_analytic_pairing_use_synthetic_20260930`  
**Date:** 2026-09-30  
**Branch:** `gnhf/execute-the-p22-data-146414`  
**Research fits:** 0 (trainability-with-learning `REFUSED_UNTIL_CHECKPOINT_C`).

Machine-readable: [implement.json](implement.json); frozen [SYNTHETIC_PROTOCOL.json](SYNTHETIC_PROTOCOL.json).

## Reuse

- Existing `paired_model` / `model_inputs` / `predict` (multiome_runner).
- Existing `binary_log_loss` / `identity_check` (s7_pairing).
- Existing `make_fit_id` (s7_ledger).
- New pieces only: analytic generator module `p22.eval.s9_analytic` + dry-run job enumeration / refusal helpers.

## Verification summary

- Oracle gate: `PASS` (ρ=1 BA=1.0000; ρ=0 BA=0.6250; ρ=1 shuffled BA=0.5000)
- Job coverage: smoke 7 + screen 42 = **49 ≤ 60**
- Fit arithmetic: smoke 7 + screen ρ0 21 + screen ρ1 21 = 49
- CA/TC param match: pass=True (rel=0.0565)
- Finite gradients: all 4 neural arms
- Reload equality: all 4 neural arms (atol=1e-06)
- Donor isolation fold-0: PASS
- Within-donor ATAC marginal preservation: PASS
- Refusals: protocol-hash mismatch, S7/S8 raw roots, donor leakage, unreviewed trainability-with-learning

## Hashes (exact)

- `SYNTHETIC_PROTOCOL.json`: `eedf5e77c4ba08d8a801609e5a2bdfccc5d882e2d297d9469c4af364ad25ec7a`
- `SPLIT_MANIFEST.json`: `2d9a3b9fac7bfd8dd48b7517e0ad22e297eab9a4e9f775ac814dd99b8c50fd4d`
- `FIT_LEDGER.json`: `841c8468b6b17a43628d14af00f277ffb156b774264fe1dad0545b2ab5cd3563`

## Scientific invariants (unchanged)

Primary `B_NULL`; S7-v1/v2 `INVALID`; prior S8 `NO FIT`; power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`.

Unresolved flags retained: ENDPOINT_UNRESOLVED; REGULATORY_ADEQUACY_UNRESOLVED; EXTERNAL_FEASIBILITY_BOUNDED/confirmatory UNRESOLVED; POWER_UNESTABLISHED; fitted_ba_montecarlo_joint_calibration DESIGN_UNRESOLVED.

## Next

Q9 independent scientific/code review on exact hashes. No fits until Checkpoint C.

# R7 — Minimal implement (S10 corrected null)

**Disposition:** `IMPLEMENT_PASS`
**Protocol ID:** `S10_corrected_null_pairing_use_20261001`
**Date:** 2026-10-01
**Branch:** `gnhf/execute-p22-s-failur-d8f02c`
**Research fits:** 0 (`REFUSED_UNTIL_CHECKPOINT_C`).
**Generator draws this run:** 16 (R7 exchangeability panel).

Machine-readable: [implement.json](implement.json); frozen [S10_PROTOCOL.json](S10_PROTOCOL.json).

## Reuse

- Existing `paired_model` / `model_inputs` / `predict` / S7 pairing helpers.
- Existing S9 label/split/oracle-scoring/permute helpers via import.
- New: `p22.eval.s10_analytic` corrected generator + dry-run/refusals; `p22.eval.s10_execute` serial executor stub (fits refused until R8).

## Verification summary

- Oracle gate: `PASS` (ρ=1 BA=1.0000; ρ=0 BA=0.5417; ρ=1 shuffled=0.5417)
- Exchangeability panel: mean ratio=1.0043 (band [0.95, 1.05]; within=True)
- Job coverage: smoke 7 + screen 42 = **49 ≤ 90**
- CA/TC param match: pass=True (rel=0.0565)
- Finite gradients: all 4 neural arms
- Reload equality: all 4 neural arms
- Refusals: hash/S7/S9-raw/unreviewed-fits + allowed S10 root
- Workers: 1 (serial); torch threads: 2

## Hashes (exact)

- `S10_PROTOCOL.json`: `f16e503df4e4ba19029ddf06354b3c95aa1612a6ba0c49dbc2d891e8beb1798c`
- `S10_SPLIT_MANIFEST.json`: `ec210b253386938a62047728992c094107e6e65f0169aa04ef7e59ff6b676ba6`
- `S10_SEED_SCHEDULE.json`: `4ef154fe783db23aa0df09ba31d38e409a3efd2070cb581603a226b8b25c33ec`
- `src/p22/eval/s10_analytic.py`: `5440d8cd42feb69c4c8f0e6416620315b6916dd2d980d655b8ff1b409ad3fb9e`
- `src/p22/eval/s10_execute.py`: `2aed78eaf2f0e9ef9643acfad9ddc7a8e7d81afca35ac7e92ad426e012eefe77`

R8 prep note (post-R7, before fits): executor uses external `R8_REVIEWED_HASHES.json` (no self-embedded digests); serial path reserves attempts before dispatch; neural checkpoints carry `initial_state_sha256` / learning history via additive `fit_s7_arm` fields.

## Scientific invariants (unchanged)

Primary `B_NULL`; S9 `INVALID` immutable; prior S8 `NO FIT`; study `STUDY_PARTIAL`.

## Next

R8 independent full-path review on exact hashes (executor + dependencies). No fits until Checkpoint C.

# R7 — S10 corrected-null protocol freeze

**Disposition:** `PROTOCOL_FROZEN` + `IMPLEMENT_PASS`
**Protocol ID:** `S10_corrected_null_pairing_use_20261001`
**Kind:** `corrected_software_null_reproducibility_test`
**Null candidate:** `independent_gaussian_rho0_within_donor_shuffle_20261001`
**Claim level:** 1 (software / mechanism control)
**Date:** 2026-10-01
**Branch:** `gnhf/execute-p22-s-failur-d8f02c`
**Fits:** 0 scientific; 0 diagnostic (cap exhausted).

Machine-readable: [S10_PROTOCOL.json](S10_PROTOCOL.json); [S10_SPLIT_MANIFEST.json](S10_SPLIT_MANIFEST.json); [S10_SEED_SCHEDULE.json](S10_SEED_SCHEDULE.json); [IMPLEMENT.md](IMPLEMENT.md).

## Hypothesis

Under the corrected independent-Gaussian ρ=0 null (no exact orthogonalization), does the seven-arm NN factory detect planted within-cell RNA/ATAC pairing via CA donor log-loss drop under within-donor ATAC shuffle, with a VALID exchangeable ρ=0 null gate?

## Generator correction vs S9

- **S9 defect (immutable):** exact ρ=0 orthogonalization broke within-donor ATAC shuffle exchangeability (R2 ESTABLISHED).
- **S10 repair:** planted z,w are independently centre-scaled Gaussians (tags `z_s10`/`w_s10`); **no** `w⊥z` projection.
- At ρ=0: ATAC planted = independent w (exchangeable under within-donor shuffle).
- At ρ=1: ATAC planted = signed RNA (positive-control role unchanged).

## Seeds (prospective; disjoint from S9/R2 panels)

- Decision: generator `9301`, split `17`, model `9301`
- Headroom: `[9401, 9402, 9403]`
- Pairing shuffle: `[4001, 4002, 4003, 4004, 4005, 4006, 4007, 4008, 4009, 4010, 4011, 4012, 4013, 4014, 4015, 4016]` (intervention; not fits)
- R7 exchangeability panel: `[5301, 5302, 5303, 5304, 5305, 5306, 5307, 5308, 5309, 5310, 5311, 5312, 5313, 5314, 5315, 5316]` (generator-only; ≤64)

## Oracle (toy; decision seed)

- ρ=1 BA=1.0000; ρ=0 BA=0.5417; ρ=1 shuffled BA=0.5417
- ρ=0 max |product mean|=0.374128 (not machine-zero orthogonal)
- Gate: `PASS`

## Arms and budgets

- Seven equally supervised arms: cross_attention, token_concat, rna_atac_concat, gated_fusion, logreg_concat, logreg_rna, logreg_atac
- Smoke 7 + screen ρ=0 21 + screen ρ=1 21 = **49 ≤ 90** (headroom 41)
- Serial workers=`1`; torch threads=`2`
- Fitting hours ≤ 6.0; artifacts ≤ 4.0 GiB; payloads = 0
- Raw root: `reports/generated/nn_failure_audit_20261001/s10_corrected_null_pairing_20261001/`

## Primary statistic and null gate

- **Primary:** CA ρ=1 donor log-loss drop under within-donor ATAC shuffle (PAIRING_POSITIVE iff CI lower > 0).
- **Null gate:** same statistic at ρ=0 must have CI lower ≤ 0.
- **Advantage contrast:** CA−token_concat pooled BA = `SEPARATE_NON_PRIMARY`.
- Unimodal marginal BA ≤ 0.60 at ρ=1 for logreg_rna/atac.

## Scientific invariants (unchanged)

Primary `B_NULL`; S9 `INVALID` immutable; S7-v1/v2 `INVALID`; prior S8 `NO FIT`; Q2 `ENDPOINT_UNRESOLVED`; study `STUDY_PARTIAL`.

## Next

R8 independent full-path review on actual executor + dependency hashes. No scientific fits until Checkpoint C PASS.

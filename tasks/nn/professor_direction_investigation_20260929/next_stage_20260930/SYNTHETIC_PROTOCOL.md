# Q7 — Synthetic protocol freeze (S9 analytic pairing-use)

**Disposition:** `PROTOCOL_FROZEN`  
**Protocol ID:** `S9_analytic_pairing_use_synthetic_20260930`  
**Kind:** `analytic_synthetic_pairing_use_software_control`  
**Date:** 2026-09-30  
**Branch:** `gnhf/execute-the-p22-data-146414`  
**Fits:** 0 (protocol freeze only; Checkpoint C required before any research fit).

Machine-readable: [SYNTHETIC_PROTOCOL.json](SYNTHETIC_PROTOCOL.json); [SPLIT_MANIFEST.json](SPLIT_MANIFEST.json); [FIT_LEDGER.json](FIT_LEDGER.json).

## Hypothesis

Can the existing seven-arm NN factory, under equal supervision and the frozen analytic generator, detect planted within-cell RNA/ATAC pairing via donor log-loss drop under within-donor ATAC shuffle?

## Generator equations

- **Donor labels:** Rank donor_ids by SHA256('s9-label\n'+generator_seed+'\n'+donor_id); first 12 → class 0, remaining 12 → class 1. Labels are analytic and independent of any biological disease label.
- **Planted pairing:** For each donor d and planted channel k∈{0..3}: draw z,w ~ N(0,I) from SHA256(generator_seed, donor_id, channel, 'z'|'w') SeedSequence; centre/scale z to mean 0 variance 1; orthogonalize w against z then centre/scale. Set RNA[cells,k]=z and ATAC[cells,k]=(2*y_d-1)*rho*z + sqrt(1-rho^2)*w. Latent draws do not depend on fold index.
- **Nuisance:** For channels k∈{4..15}: independent Gaussian draws per view plus a donor-level mean shift (0.5 * SHA256-stable donor shift vector). Nuisance is independent of y_d and of planted z.
- **Interpretation:** At all rho, planted channels have mean 0 and variance 1 per donor. rho controls signed within-cell cross-view covariance. At rho=0 there is no planted pairing; at rho=1 ATAC planted equals signed RNA planted. Unimodal marginals of planted channels carry no label signal.

## Oracle

- Definition: Non-learned donor score = mean over cells of sum of planted-channel products RNA[k]*ATAC[k] for k=0..3. Predict class 1 iff score > 0.
- Role: Validates that the constructed pairing signal exists and is destroyed by the intended within-donor ATAC shuffle. Does not validate learned models.
- Toy gate: `PASS` (ρ=1 BA=1.0000; ρ=0 BA=0.6250; ρ=1 shuffled BA=0.5000)

## Fitted-mechanism null

Under the same fitted pipeline and within-donor ATAC shuffle intervention at rho=0, CA must not yield PAIRING_POSITIVE (donor log-loss-drop 95% CI lower <= 0).

Chance/Bernoulli BA bands remain rejected (prior S8 `NO FIT` unchanged).

## Seeds (decision vs headroom disjoint)

- Decision: generator `9001`, split `0`, model `9001`
- Pairing shuffle seeds (not fits): `4001`–`4016`
- Headroom (disjoint): `[9101, 9102, 9103]`
- Rule: Decision seeds (9001 / split 0 / model 9001) are frozen before any result. Headroom seeds 9101+ are disjoint and may only be used within remaining fit headroom after review; they cannot retune the frozen null threshold, oracle gates, or primary statistic.

## Splits

- F=3 donor-level class-quota SHA256; 8 test / 12 train / 4 val per fold; both classes required.
- Rationale: Prospective F=3 for analytic synthetic software/mechanism detectability of a planted pairing signal — not biological power and not a post-hoc shrink of the frozen S7 5-fold disease protocol.

## Arms and budgets

- Seven equally supervised arms: cross_attention, token_concat, rna_atac_concat, gated_fusion, logreg_concat, logreg_rna, logreg_atac
- Smoke 7 + screen ρ=0 21 + screen ρ=1 21 = **49 ≤ 60** (headroom 11)
- Fitting hours ≤ 4; artifacts ≤ 2 GiB; 2 workers × 2 torch threads

## Primary statistic vs advantage contrast

- **Primary (pairing-use):** For CA at rho=1: mean donor log-loss(shuffled ATAC) - log-loss(original); average shuffle outcomes within donor across PAIRING_SHUFFLE_SEEDS, then paired donor-bootstrap 95% CI (1000 draws, seed 22). PAIRING_POSITIVE iff CI lower > 0.
- **Null gate:** Same pairing statistic at rho=0 must have CI lower <= 0; otherwise label INVALID (design/optimization leak), not a method claim.
- **Advantage contrast (`SEPARATE_NON_PRIMARY`):** Pooled donor BA(CA) - BA(token_concat) at rho=1 with paired donor-bootstrap CI. Reported for description only; does not define PAIRING_POSITIVE and is not required for a valid pairing-use control.
- **Joint rule:** All seven arms must complete smoke+screen coverage before interpreting pairing. Incomplete coverage => INCOMPLETE, not a partial positive.

## Scientific invariants (unchanged)

Primary `B_NULL`; S7-v1/v2 `INVALID`; prior S8 `NO FIT`; power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`.

Unresolved flags retained: ENDPOINT_UNRESOLVED; REGULATORY_ADEQUACY_UNRESOLVED; EXTERNAL_FEASIBILITY_BOUNDED/confirmatory UNRESOLVED; POWER_UNESTABLISHED; fitted_ba_montecarlo_joint_calibration DESIGN_UNRESOLVED.

## Next

Q8 implements minimal generator/runner reuse and focused falsification tests. No fits until Checkpoint C.

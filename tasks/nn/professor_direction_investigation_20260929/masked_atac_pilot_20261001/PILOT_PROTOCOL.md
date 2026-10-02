# Masked ATAC pilot M5 — protocol freeze

**Disposition:** `PROTOCOL_FROZEN`
**Protocol ID:** `masked_atac_pilot_20261001`
**Claim level:** 2 (computational prediction; not state/causal/external)
**Date:** 2026-10-01
**Fits:** 0 (protocol freeze only; learning unauthorized until M8)

Machine-readable: [PILOT_PROTOCOL.json](PILOT_PROTOCOL.json); [BUDGET_LEDGER.md](BUDGET_LEDGER.md).

## Preserved labels

- primary: `B_NULL`
- S7: `INVALID`
- S9: `INVALID`
- S10: `INVALID`
- S8: `NO FIT`
- Q2: `ENDPOINT_UNRESOLVED`

## Primary estimand

- **Name:** `mean_donor_paired_cell_log_loss_tc_minus_ca`
- **Sign:** positive_means_ca_lower_loss_than_token_concat
- **Clip:** `1e-15`
- **Aggregation:** equal mean across donors of within-donor mean cell binary log-loss difference (TC − CA); same cells/targets within fold
- **Practical margin:** `0.01` (exploratory only)
- **Margin justification:** Absolute exploratory threshold 0.01 on paired mean donor cell-log-loss difference (TC−CA). Chosen before any pilot outcomes as larger than PROB_CLIP=1e-15 numerical scale and << ln(2)≈0.693 (constant-0.5 vs oracle gap). Disease BA practical_margin is not applicable to continuous mixed-label cell log-loss. This is not established power, confirmatory alpha, or training/selection uncertainty.
- **Selection:** Inner-validation checkpoint selection by equal-donor mean of within-donor mean cell-target binary log-loss (mixed labels allowed). Do not use donor-average probability, fake disease class, AUROC, BA, or disease labels for selection.

## Bootstrap

- Draws: **1000**; seed **601001**; level **0.95**
- Kind: fixed_prediction_paired_donor
- Single-class draws dropped: **False**
- Limits: Fixed-prediction donor bootstrap only: does not capture overlapping training sets across folds, training-only target selection variability, model-init/selection uncertainty, or hyperparameter uncertainty. Exploratory uncertainty display, not confirmatory inference.

## Models and epochs

| Arm | Role | Main fits | Notes |
|---|---|---:|---|
| `training_prevalence_constant` | sanity/descriptive baseline | 0 | Per-fold training-prevalence constant probability; zero learned params |
| `logreg_rna` | simple measured-modality control | 5 | sklearn LogisticRegression |
| `logreg_visible_atac` | simple measured-modality control | 5 | sklearn LogisticRegression |
| `feature_concat_mlp` | required simple fusion control | 5 | ConcatFusionModel via paired_model('rna_atac_concat'); max_epochs=20, patience=5 |
| `token_concat` | matched primary comparator | 5 | TokenConcatFusionModel via paired_model('token_concat'); max_epochs=20, patience=5 |
| `cross_attention` | primary model | 5 | CrossAttentionModel via paired_model('cross_attention'); max_epochs=20, patience=5 |

Neural fingerprint: `5517354c43d542731ef64f674ab3c90eac6a7b342973bc62c0996c717dc002f0`
CA/TC param-match tolerance: ≤0.1 (checked widths 423/430/440: all matched).

## Attempt arithmetic

- 5 learned arms × 5 folds = 25 main; + 5 reserved smoke (one per learned arm, fold 0) = 30 intended; hard cap 40; headroom 10; constant arm = 0 fits
- Within caps: **True**
- Workers × torch threads: **1 × 2**
- Fitting hours ≤ 6.0; artifacts ≤ 4.0 GiB

## Reserve / resume / RNG

- `reserve_attempt_counter_before_dispatch`: True
- `failed_and_smoke_count`: True
- `never_reset_counters_after_interruption`: True
- `do_not_refit_completed_jobs_after_token_cap_stop`: True
- `timeout_counts_as_attempt`: True
- `crash_before_sidecar_still_reserved`: True
- `resume_replays_completed_only`: True
- `serial_workers`: 1
- `torch_threads`: 2
- `rng_isolation`: Serial one-worker fits; set_all_seeds(model_seed) per job; no concurrent writers; global RNG not shared across parallel jobs
- `no_neural_smoke_before_m8`: True
- `no_hyperparameter_seed_target_sweep`: True

## Checks

- `attempt_arithmetic_within_caps`: **True**
- `planned_main_fits_is_25`: **True**
- `planned_jobs_count_matches_intended`: **True**
- `ca_tc_param_match_all_widths`: **True**
- `toy_contrast_matches_hand`: **True**
- `bootstrap_keeps_single_class_draws`: **True**
- `practical_margin_not_disease_ba`: **True**
- `m3_frozen_present`: **True**
- `m4_falsification_pass`: **True**
- `no_fits`: **True**

## Forbidden claim promotions

- `biological_state`
- `causal_mechanism`
- `external_validation`
- `single_locus_performance`
- `established_power`
- `confirmatory_inference`
- `S10_pairing_positive_as_gate`
- `Q2_endpoint_required`

## Next

M6 independent protocol/claim review on these frozen hashes. No implementation learning or smoke fits until M6+M8 PASS.

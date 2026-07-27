# Interim methods protocol

**Status:** synthetic-only implementation complete (C01–C13)
**Approval:** blocked pending Professor Fang
**Evidence labels:** verified, experimental result, proposed, inference, unknown

## Estimand under the synthetic protocol (proposed for real data later)

Compare predictive performance and routing-dependence evidence across six
baselines under donor-held-out evaluation, with transforms fitted on training
cells only, validation-only selection, and one final test evaluation per seed.

Real-data estimand, target label, modality pairing, and success margins are
**unknown** until approval and preflight.

## Fixed order of operations (verified in code)

1. Generate or load data in an allowed mode (`synthetic` while blocked)
2. Split donors into train / validation / test; validate zero donor overlap
3. Fit transforms on training cell IDs only; reject held-out IDs in the fit set
4. Train each baseline; select with validation only
5. Evaluate test once per model per seed
6. Summarise five seeds with mean, sd, and interval; do not tune on test
7. On held-out cells, run the seven interventions for gated (and applicable) models
8. Write run records and reports under `reports/generated/`

## Baselines

See `MODEL_CARD.md`. Configured in `configs/toy_pilot.json`.

## Reporting rules

- Separate predictive performance, routing signals, and intervention evidence
- Empty limitations lists are refused
- Run records require commit, config hash, data fingerprint, data mode, approval
  state, seeds, donor/cell counts, transform `fit_scope`, metrics, and evidence labels
- Do not call routing weights explanations without intervention support
- Do not convert Tasic proxy-view results into condition-specific multiomics claims

## Tasic boundary (verified)

Recorded in `legacy/tasic_proxy_view/`. Architecture proof of concept only. Both
views from one RNA matrix. Not independent-modality validation. Not
condition-specific evidence. Not leakage-controlled. Not donor-aware.

## Stop rules for this pre-approval sequence

Stop and ask the owner if:

- approval state is unclear
- a real dataset matrix appears in the working tree
- a commit would require a forbidden path or condition-specific term in code
- test metrics are used for tuning
- donors overlap across splits

## Post-approval sequence (proposed)

Documented in `docs/CURSOR_IMPLEMENTATION_HANDOFF.md` section 8 and
`docs/decision_log.md`. Do not start it without a dated approval record.

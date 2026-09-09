# Paired-model development: runnable synthetic verification

Updated: 2026-09-08. Neural training and final artifact/scoring code verified locally.
This is **software verification**, not a real-data experiment or scientific result.

## Run locally

```bash
.venv-p22/bin/python scripts/train_multiome.py \
  --config configs/paired_multiome.json \
  --output-dir reports/generated/multiome/training_next
```

Use a new output directory. The command generates neutral synthetic arrays itself;
it has no real-data input option, performs no downloads, and refuses `data_mode: real`.
It writes resolved settings before fitting, then `run.json` and `SUMMARY.md`. Invalid
inputs return exit code 2; failures after directory creation leave `failure.json`.
No GPU, cloud service, new dependency, or change to professor approval was needed.

It also writes `final/refit_contract.json` before final fitting, then `models.pt`
and `manifest.json`. The saved tensors contain six state dictionaries plus numeric
scaler parameters, loaded with `weights_only=True`, not pickled executable models.
`synthetic_external/` contains donor predictions, `validation.csv` and a JSON report.
These files are all labeled synthetic; the real-data entry path remains refused.

## What was implemented

- `train_model` accepts paired train/validation donor IDs for binary classification.
  Each donor receives equal total loss weight. Validation averages positive-class
  probabilities by donor and thresholds at 0.5. Donors cannot cross splits; mixed
  labels fail. Callers without donor IDs retain their previous cell-level behavior.
- The paired-array adapter uses training-only variance selection and frozen scaling.
  It preserves sparse arrays until selected features are bounded, rejects inputs
  above the declared donor cell cap, and shares partitions across all six networks.
- Cross-attention uses four learned latent tokens per modality, dimension 16, two
  heads, and RNA/view-A queries over ATAC/view-B keys and values within each cell.
  Tokens are projections of the feature vector, not named genes or regulatory sites.
- The matched token-concat model has the same encoders, pooling dimensions, and head.
  Attention adds parameters; it is not advertised as parameter-count matched.
  Standard concatenation and gated fusion remain separately named controls.
- Paired comparison rejects different/duplicate donor sets, inconsistent labels,
  and invalid probabilities. Both predictions share donor resamples: 1,000 draws,
  seed 22, invalid single-class draws counted rather than redrawn. Positive advantage
  requires delta at least the count-derived margin and interval lower bound above zero.

The executable uses five repeated five-fold outer donor splits. Within each outer
training set, the first of three fixed-seed donor folds supplies validation donors.
It does not choose splits using scores. Each model gets the same maximum epoch,
learning-rate, batch-size, patience, and initialization-seed settings. Per-repeat
comparisons use one out-of-fold prediction per donor, never pooled repeat rows as
independent observations. The majority control learns from training donors only.
Chromosome-21 dosage, biological QC, and pseudobulk RNA controls are explicitly not
applicable to this neutral fixture; they remain required for the real experiment.

Final refit uses all development donors, with each model's epoch count fixed to
`ceil(median(internal best epochs))`. It refits preprocessing on development cells
only and uses the same donor-balanced optimizer update as internal training. A
separate synthetic draw, seed 23 for the default fixture, exercises artifact reload
and held-out scoring. Neither its inputs nor outcomes select the saved parameters.

Scoring checks an expected manifest hash, the contained weight/scaler hash, exact
feature order, and disjoint donor/cell IDs. An exclusive lock is created before any
prediction and retained even after a scoring failure. Do not remove/copy locks to
turn evaluation into model selection. This is accidental-repeat protection, not a
security barrier against someone modifying files. Different donor IDs alone still
do not establish independent biological specimens.

## Measured execution

[Saved summary](../reports/generated/multiome/training_20260908_final/SUMMARY.md) and
[full record](../reports/generated/multiome/training_20260908_final/run.json):

- 30 synthetic donors, 256 cells each, 32 view-A and 24 view-B features.
- 25 outer folds; 150 internal fits plus six final refits and reload/scoring.
- Final epochs: ATAC-only 2; all other neural families 1, from internal validation only.
- CPU, one PyTorch thread: **27.286 seconds**, **0.4466 GB process peak RSS**.
- Trainable parameters: single-view A 1,618; single-view B 1,362; standard concat
  2,978; gated fusion 4,068; token concat 6,146; cross-attention 7,234.

The report includes split identities, preprocessing and checkpoint hashes, exact
source hashes captured before training, environment, donor predictions, and resources.
Fold weights are hashed in memory; final weights and scalers are saved. This small-feature fixture
does **not** establish full-atlas ingestion, fragment-recount, or real-training costs.

## Remaining real-data requirements

The saved configuration freezes this software benchmark only. It is **not M5's
accepted scientific protocol**. Real normalization, shared ATAC measurements,
release/QC reconciliation, specimen independence, sensitivities/covariate policies,
and the dated professor-specific approval remain unresolved. User authorization to
continue development was received; it was not relabeled as Professor Fang's approval.

Final all-development refit/serialized artifacts and locked scoring now exist, but
the accepted real-data orchestrator remains blocked by those contracts. Do not feed
raw atlas counts directly to the array adapter and interpret its standard scaling as
an accepted RNA/ATAC normalization. Matrix-row/barcode identity must be established
upstream; matching row counts alone cannot prove it. See [the checklist](../tasks/todo.md).

## Verification

```bash
.venv-p22/bin/python -m pytest -q tests/test_training.py tests/test_cross_attention.py \
  tests/test_multiome_protocol.py tests/test_multiome_runner.py tests/test_multiome_final.py
make lint
make test-all
```

Tests cover different donor/cell checkpoint choices, donor loss weights, split and
label rejection, Q/K/V direction and token axes, finite gradients, modality ablations,
held-out preprocessing invariance, strict paired bootstrap, synthetic execution, and
refusal of real-data configurations or output overwrites. Independent review found
no required defects in the completed training slices.

Verification including the author-table audit increment: **576 full-suite tests passed**, with 19
pre-existing scikit-learn warnings. Lint and formatting passed. No tests were disabled.

Implementation follows the installed PyTorch 2.8 APIs:
[MultiheadAttention](https://docs.pytorch.org/docs/2.8/generated/torch.nn.MultiheadAttention.html)
and [unreduced cross entropy](https://docs.pytorch.org/docs/2.8/generated/torch.nn.CrossEntropyLoss.html).
Final artifacts follow [state-dictionary saving/loading](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html)
with an explicit [weights-only load](https://docs.pytorch.org/docs/2.8/generated/torch.load.html).

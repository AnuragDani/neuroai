# NN v2 Ladder Audit

## Root cause
In `prepare_nn_fold` (`src/p22/data/nn_fold.py`), the `inputs.rna` and `inputs.atac` matrices were not being subset by `rows` (the concatenation of `train_rows` and `holdout_rows`) before being passed into the preprocessing pipeline (`_rna_lognorm`, etc). However, the metadata arrays (`label`, `donor`, `qc`, `nuisance_codes`) were properly subset by `rows` (via `inputs.metadata.iloc[rows]`). This caused a massive row misalignment: the features at index `i` in the resulting `FoldArrays` corresponded to the `i`-th cell in the original unsampled matrix, while the label at index `i` corresponded to the `rows[i]`-th cell. This destroyed the association between features and labels, resulting in random chance performance (AUROC ~0.345 instead of 1.0) for models like `chr21_dosage`.

## Fixes
TBD

## Tests
TBD

## What changed in the protocol
TBD

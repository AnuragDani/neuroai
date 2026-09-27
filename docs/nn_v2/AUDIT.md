# NN v2 Ladder Audit

## Root cause
In `prepare_nn_fold` (`src/p22/data/nn_fold.py`), the `inputs.rna` and `inputs.atac` matrices were not being subset by `rows` (the concatenation of `train_rows` and `holdout_rows`) before being passed into the preprocessing pipeline (`_rna_lognorm`, etc). However, the metadata arrays (`label`, `donor`, `qc`, `nuisance_codes`) were properly subset by `rows` (via `inputs.metadata.iloc[rows]`). This caused a massive row misalignment: the features at index `i` in the resulting `FoldArrays` corresponded to the `i`-th cell in the original unsampled matrix, while the label at index `i` corresponded to the `rows[i]`-th cell. This destroyed the association between features and labels, resulting in random chance performance (AUROC ~0.345 instead of 1.0) for models like `chr21_dosage`.

## Fixes
- `prepare_nn_fold` was corrected to properly subset the sparse matrices `inputs.rna[rows, :]` and `inputs.atac[rows, :]` before downstream processing.
- `scripts/summarize_nn_v2.py` was updated to properly use `repeated_primary_contrast` semantics, pooling donors per repeat and calculating the independent donor bootstrap CI correctly.
- Frozen model widths were restored.

## Tests
- `tests/test_nn_audit_alignment.py`: verifies feature-label alignment is properly maintained during fold preparation.
- `tests/test_nn_conformance.py`: ensures that the restored model widths strictly match the protocol definitions.
- `tests/test_nn_summary.py`: synthetically evaluates the summarizer CI logic, asserting it matches an independent recomputation.

## What changed in the protocol
- Restored original frozen model widths, reverting undocumented capacity changes.
- Summarizer uncertainty CI logic was updated to use a mathematically sound donor-level bootstrap over repeats.

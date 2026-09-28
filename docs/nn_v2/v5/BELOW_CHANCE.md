# Below-chance pooled AUROC — V3 diagnosis

**Verdict:** `PIPELINE_BUG_FIXED`

V2 required a shared-path fix (positive-control donor_auroc=0.924); canonical ladder must be rerun under the corrected fit path.

## Evidence (from docs/nn_v2/v5/)

| Arm | Per-fold AUROC mean | Per-fold SD | Pooled AUROC |
|---|---:|---:|---:|
| R3_ca | 0.687 | 0.272 | 0.363 |
| R3_tc | 0.641 | 0.289 | 0.342 |
| logreg_rna | 0.573 | 0.233 | 0.399 |
| majority | 0.500 | 0.000 | 0.353 |
| chr21_dosage | 1.000 | 0.000 | 0.998 |

## Positive control (V2)

- Forced-chr21 logreg pooled donor AUROC: **0.924** (threshold ≥ 0.9).
- Default HVG keeps ~31 chr21 genes (most dosage signal dropped before training).
- Orientation Spearman (pred DS prob vs chr21 share): 0.6480533926585095.

## Shared-path fix

sklearn controls now fit on the full outer-train split; previously worker_task passed only the inner-train third and _control_trainer discarded val, wasting one third of training donors

## Reading

Pooled AUROC mixes fold-specific score scales across stratified folds and can look below chance even when each fold ranks donors above chance. That pooling gap remains visible (learned per-fold means > 0.5; pooled < 0.45). Separately, V2 found that sklearn control arms were fit on only the inner-train third of outer-train donors; fixing that path raised the forced-chr21 positive control above 0.9. Because the shared runner changed, the V3 tree selects `PIPELINE_BUG_FIXED` and V4 must rebuild the canonical ladder under the corrected fit.

**Next:** V4: rerun full ladder into ladder_v3

# Legacy Tasic proxy-view experiment: evidence record

**Step:** C02
**Data mode:** legacy read-only
**Manifest:** `legacy/tasic_proxy_view/manifest.json` (8 tracked files, byte size and SHA-256 recorded)
**Regenerate or check:** `python scripts/build_legacy_manifest.py build|verify`

This directory records what the earlier Tasic work does and does not show. It does not
copy, move, or edit anything under `experiments/`. Every claim below carries an evidence
label: verified, experimental result, proposed, inference, or unknown.

## 1. What was run (verified)

- Source: Tasic et al. 2018 mouse cortex SMART-seq data, accession GSE115746. The matrix
  itself is not tracked in this repository.
- 22,113 cells passed the script's quality filter, 40,333 genes retained, 2,000 highly
  variable genes selected, 60 principal components computed.
- View one is highly variable gene expression. View two is a 60-component principal
  component projection of the same expression matrix (`X_morph = pca.fit_transform(X_full)`
  in `experiments/run_tasic2018_pipeline.py`).
- Five models per task: logistic regression on view one, MLP on view one, MLP on view two,
  concatenation fusion, attention fusion.
- Two tasks: a four-class broad label task and a 130-class fine-grained label task
  (21,858 cells split 13,988 / 3,498 / 4,372).

## 2. Numbers as recorded (experimental result)

Four-class task: accuracy is 1.0 for logistic regression, MLP on view one, concatenation
fusion, and attention fusion, and 0.9998 for the MLP on view two. The task is saturated, so
it cannot separate model families.

130-class task test accuracy:

| Model | Accuracy | Weighted F1 |
|---|---|---|
| Logistic regression, view one | 0.9101 | 0.9090 |
| MLP, view one | 0.9030 | 0.9043 |
| MLP, view two | 0.9135 | 0.9146 |
| Concatenation fusion | 0.9213 | 0.9221 |
| Attention fusion | 0.9149 | 0.9165 |

Paired comparison of attention fusion against concatenation fusion on the same test cells:
128 cases where attention fusion is correct and concatenation is wrong, 156 the other way,
continuity-corrected chi-square 2.5669, p = 0.109. Not significant at 0.05.

Routing signals: on the four-class task the mean weight on view one ranges from 0.61 to
0.89 across classes. On the 130-class task the mean weight is near 0.999 on view two for
the highest-ranked classes.

Mutual information with the label, averaged over features: 0.1132 for view one features,
0.6033 for view two components. Mean pairwise mutual information between paired features of
the two views is 0.0027, computed on 5,000 sampled cells.

## 3. What this supports (inference)

- The fusion architecture runs end to end at this scale and produces per-class routing
  weights: supported.
- Concatenation fusion is at least as accurate as attention fusion on the 130-class task in
  this single run: supported by the paired test, which shows no significant difference.
- Strongly asymmetric routing weights coincide with the view whose components carry higher
  mutual information with the label in this setup: supported as an association only.

## 4. What this does not support (verified from the code and outputs)

- Not independent two-modality validation. Both views come from one RNA matrix, so
  agreement between them is not independent evidence.
- Not condition-specific evidence. There is no clinical cohort, no case and control
  contrast, and no condition label anywhere in these outputs.
- Not an explanation of mechanism. Attention weights are routing signals. No clamp,
  permutation, or ablation test was run, so nothing here shows the prediction depends on
  the routed view.
- Not leakage-controlled. The principal component projection for view two was fitted on all
  cells before the split.
- Not donor-aware. The split is stratified over cells with one seed, and the reported
  intervals resample test cells rather than donors, so both underestimate uncertainty from
  donor structure.
- Not a variability estimate. One seed per model, so differences of one or two accuracy
  points cannot be separated from run-to-run noise.

## 5. Unknown

- Whether donor identifiers exist in the source metadata for these cells; the tracked
  outputs do not carry them.
- Whether the ranking of model families survives donor-held-out splitting, train-only
  transforms, and five seeds. The synthetic sequence C03 to C11 builds the machinery to
  answer that; this record does not answer it.
- Whether any of this transfers to a second measurement modality.

## 6. Rules for reuse (proposed)

- Cite these files as an architecture proof of concept with the boundary above attached.
- Do not describe the two views as separate measurement modalities.
- Do not quote routing weights without stating that no intervention test supports them.
- Do not regenerate these outputs. If they change, `scripts/build_legacy_manifest.py verify`
  fails, and the change must be explained before any downstream claim is reused.

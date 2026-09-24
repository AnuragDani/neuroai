# Planted-signal benchmark (N4)

Planted synthetic signal only; no biological or clinical claim.

## S0

| delta | model | donor BA (mean +/- SD) | AUROC | log-loss |
| --- | --- | --- | --- | --- |
| 0.0 | logreg_concat | 0.542 +/- 0.125 | 0.636 | 0.708 |
| 0.0 | rna_atac_concat | 0.533 +/- 0.075 | 0.569 | 0.708 |
| 0.0 | gated_fusion | 0.500 +/- 0.118 | 0.617 | 0.709 |
| 0.0 | token_concat | 0.500 +/- 0.118 | 0.569 | 0.712 |
| 0.0 | cross_attention | 0.500 +/- 0.000 | 0.569 | 0.706 |

## S1

| delta | model | donor BA (mean +/- SD) | AUROC | log-loss |
| --- | --- | --- | --- | --- |
| 0.25 | logreg_concat | 1.000 +/- 0.000 | 1.000 | 0.150 |
| 0.25 | rna_atac_concat | 0.967 +/- 0.075 | 1.000 | 0.314 |
| 0.25 | gated_fusion | 0.967 +/- 0.075 | 1.000 | 0.290 |
| 0.25 | token_concat | 0.967 +/- 0.075 | 1.000 | 0.318 |
| 0.25 | cross_attention | 0.967 +/- 0.075 | 1.000 | 0.318 |
| 0.5 | logreg_concat | 1.000 +/- 0.000 | 1.000 | 0.103 |
| 0.5 | rna_atac_concat | 1.000 +/- 0.000 | 1.000 | 0.125 |
| 0.5 | gated_fusion | 1.000 +/- 0.000 | 1.000 | 0.110 |
| 0.5 | token_concat | 1.000 +/- 0.000 | 1.000 | 0.127 |
| 0.5 | cross_attention | 1.000 +/- 0.000 | 1.000 | 0.126 |
| 1.0 | logreg_concat | 1.000 +/- 0.000 | 1.000 | 0.033 |
| 1.0 | rna_atac_concat | 1.000 +/- 0.000 | 1.000 | 0.042 |
| 1.0 | gated_fusion | 1.000 +/- 0.000 | 1.000 | 0.043 |
| 1.0 | token_concat | 1.000 +/- 0.000 | 1.000 | 0.047 |
| 1.0 | cross_attention | 1.000 +/- 0.000 | 1.000 | 0.042 |

## S2

| delta | model | donor BA (mean +/- SD) | AUROC | log-loss |
| --- | --- | --- | --- | --- |
| 0.25 | logreg_concat | 1.000 +/- 0.000 | 1.000 | 0.049 |
| 0.25 | rna_atac_concat | 1.000 +/- 0.000 | 1.000 | 0.203 |
| 0.25 | gated_fusion | 1.000 +/- 0.000 | 1.000 | 0.195 |
| 0.25 | token_concat | 1.000 +/- 0.000 | 1.000 | 0.203 |
| 0.25 | cross_attention | 1.000 +/- 0.000 | 1.000 | 0.160 |
| 0.5 | logreg_concat | 1.000 +/- 0.000 | 1.000 | 0.026 |
| 0.5 | rna_atac_concat | 1.000 +/- 0.000 | 1.000 | 0.066 |
| 0.5 | gated_fusion | 1.000 +/- 0.000 | 1.000 | 0.056 |
| 0.5 | token_concat | 1.000 +/- 0.000 | 1.000 | 0.066 |
| 0.5 | cross_attention | 1.000 +/- 0.000 | 1.000 | 0.049 |
| 1.0 | logreg_concat | 1.000 +/- 0.000 | 1.000 | 0.018 |
| 1.0 | rna_atac_concat | 1.000 +/- 0.000 | 1.000 | 0.020 |
| 1.0 | gated_fusion | 1.000 +/- 0.000 | 1.000 | 0.014 |
| 1.0 | token_concat | 1.000 +/- 0.000 | 1.000 | 0.019 |
| 1.0 | cross_attention | 1.000 +/- 0.000 | 1.000 | 0.016 |

## S3

| delta | model | donor BA (mean +/- SD) | AUROC | log-loss |
| --- | --- | --- | --- | --- |
| 0.25 | logreg_concat | 1.000 +/- 0.000 | 1.000 | 0.087 |
| 0.25 | rna_atac_concat | 0.900 +/- 0.149 | 1.000 | 0.381 |
| 0.25 | gated_fusion | 0.967 +/- 0.075 | 1.000 | 0.364 |
| 0.25 | token_concat | 0.900 +/- 0.149 | 1.000 | 0.388 |
| 0.25 | cross_attention | 0.900 +/- 0.149 | 1.000 | 0.368 |
| 0.5 | logreg_concat | 1.000 +/- 0.000 | 1.000 | 0.050 |
| 0.5 | rna_atac_concat | 1.000 +/- 0.000 | 1.000 | 0.166 |
| 0.5 | gated_fusion | 1.000 +/- 0.000 | 1.000 | 0.142 |
| 0.5 | token_concat | 1.000 +/- 0.000 | 1.000 | 0.167 |
| 0.5 | cross_attention | 1.000 +/- 0.000 | 1.000 | 0.137 |
| 1.0 | logreg_concat | 1.000 +/- 0.000 | 1.000 | 0.038 |
| 1.0 | rna_atac_concat | 1.000 +/- 0.000 | 1.000 | 0.042 |
| 1.0 | gated_fusion | 1.000 +/- 0.000 | 1.000 | 0.038 |
| 1.0 | token_concat | 1.000 +/- 0.000 | 1.000 | 0.042 |
| 1.0 | cross_attention | 1.000 +/- 0.000 | 1.000 | 0.036 |

## S4

| delta | model | donor BA (mean +/- SD) | AUROC | log-loss |
| --- | --- | --- | --- | --- |
| 0.25 | logreg_concat | 0.867 +/- 0.139 | 0.978 | 0.494 |
| 0.25 | rna_atac_concat | 0.767 +/- 0.224 | 0.911 | 0.556 |
| 0.25 | gated_fusion | 0.833 +/- 0.167 | 0.956 | 0.541 |
| 0.25 | token_concat | 0.833 +/- 0.167 | 0.889 | 0.560 |
| 0.25 | cross_attention | 0.833 +/- 0.167 | 0.867 | 0.543 |
| 0.5 | logreg_concat | 0.867 +/- 0.139 | 1.000 | 0.435 |
| 0.5 | rna_atac_concat | 0.833 +/- 0.167 | 0.956 | 0.503 |
| 0.5 | gated_fusion | 0.833 +/- 0.167 | 1.000 | 0.502 |
| 0.5 | token_concat | 0.800 +/- 0.139 | 0.978 | 0.490 |
| 0.5 | cross_attention | 0.867 +/- 0.139 | 0.956 | 0.490 |
| 1.0 | logreg_concat | 0.900 +/- 0.149 | 1.000 | 0.395 |
| 1.0 | rna_atac_concat | 0.867 +/- 0.139 | 1.000 | 0.452 |
| 1.0 | gated_fusion | 0.900 +/- 0.149 | 1.000 | 0.435 |
| 1.0 | token_concat | 0.867 +/- 0.139 | 1.000 | 0.448 |
| 1.0 | cross_attention | 0.867 +/- 0.139 | 1.000 | 0.436 |

## S5

| delta | model | donor BA (mean +/- SD) | AUROC | log-loss |
| --- | --- | --- | --- | --- |
| 0.25 | logreg_concat | 0.542 +/- 0.125 | 0.636 | 0.708 |
| 0.25 | rna_atac_concat | 0.667 +/- 0.204 | 0.683 | 0.654 |
| 0.25 | gated_fusion | 0.642 +/- 0.227 | 0.711 | 0.651 |
| 0.25 | token_concat | 0.500 +/- 0.118 | 0.617 | 0.690 |
| 0.25 | cross_attention | 0.567 +/- 0.091 | 0.594 | 0.676 |
| 0.5 | logreg_concat | 0.542 +/- 0.125 | 0.636 | 0.708 |
| 0.5 | rna_atac_concat | 0.900 +/- 0.149 | 1.000 | 0.380 |
| 0.5 | gated_fusion | 0.967 +/- 0.075 | 1.000 | 0.321 |
| 0.5 | token_concat | 0.900 +/- 0.149 | 1.000 | 0.382 |
| 0.5 | cross_attention | 0.867 +/- 0.139 | 1.000 | 0.381 |
| 1.0 | logreg_concat | 0.542 +/- 0.125 | 0.636 | 0.708 |
| 1.0 | rna_atac_concat | 0.933 +/- 0.149 | 1.000 | 0.234 |
| 1.0 | gated_fusion | 1.000 +/- 0.000 | 1.000 | 0.162 |
| 1.0 | token_concat | 0.933 +/- 0.149 | 1.000 | 0.229 |
| 1.0 | cross_attention | 0.967 +/- 0.075 | 1.000 | 0.211 |

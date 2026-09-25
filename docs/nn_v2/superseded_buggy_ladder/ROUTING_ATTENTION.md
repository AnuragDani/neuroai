# N17 routing / attention description by cell type

Status: `NOT_SHOWN_USED` for every readout.

N13 (held-out faithfulness interventions) is `BLOCKED:N10_ladder_missing`, so no readout
is shown to be used by the model. Per `decision_tree.md` N17, every readout is therefore
tagged `NOT_SHOWN_USED`. No trained models exist (`R3_gated`, `R4_ca`), so routing weights,
attention entropy and the k_R x k_A program-module matrix could not be computed.

| readout | tag | reason |
| --- | --- | --- |
| R3_gated mean gated routing weight (RNA vs ATAC), per cell type | `NOT_SHOWN_USED` | model absent (N10 ladder missing) |
| CA attention entropy, per cell type | `NOT_SHOWN_USED` | model absent (N10 ladder missing) |
| R4_ca mean k_R x k_A program-module attention matrix + top genes/regions | `NOT_SHOWN_USED` | model absent (N10 ladder missing) |

No biological interpretation is offered for any `NOT_SHOWN_USED` readout. Attention is not
treated as explanation. Tag source: `docs/nn_v2/faithfulness.json`.

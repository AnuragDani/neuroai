# Routing and attention (N17)

Source models: `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v3` (canonical ladder_v3; not copied into finish-base).

**N13 status:** `DONE` (decision tags: CA_PAIRING_UNUSED, ATAC_USED).

Descriptive readouts only. An attention/gate readout may be described as `USED_BY_MODEL` only when its mapped N13 intervention Δ log-loss CI excludes 0; otherwise `NOT_SHOWN_USED`. Attention is not explanation.

| Readout | N13 interventions | Tag |
|---|---|---|
| R3_gated_routing_weight | I6_01, I6_10, I6_55 | `NOT_SHOWN_USED` |
| R3_ca_attention_entropy | I4 | `NOT_SHOWN_USED` |
| R4_ca_program_module_attention | I4 | `NOT_SHOWN_USED` |

| Cell type | R3_gated RNA | R3_gated ATAC | R3_gated tag | R3_ca entropy | R3_ca tag | R4_ca tag |
|---|---|---|---|---|---|---|
| AST | 0.551 | 0.449 | `NOT_SHOWN_USED` | 2.079 | `NOT_SHOWN_USED` | `NOT_SHOWN_USED` |
| IPC | 0.519 | 0.481 | `NOT_SHOWN_USED` | 2.079 | `NOT_SHOWN_USED` | `NOT_SHOWN_USED` |
| IPC_prol | 0.517 | 0.483 | `NOT_SHOWN_USED` | 2.079 | `NOT_SHOWN_USED` | `NOT_SHOWN_USED` |
| MIC | 0.668 | 0.332 | `NOT_SHOWN_USED` | 2.066 | `NOT_SHOWN_USED` | `NOT_SHOWN_USED` |
| NEU_CALB2 | 0.538 | 0.462 | `NOT_SHOWN_USED` | 2.079 | `NOT_SHOWN_USED` | `NOT_SHOWN_USED` |
| NEU_CUX2 | 0.522 | 0.478 | `NOT_SHOWN_USED` | 2.079 | `NOT_SHOWN_USED` | `NOT_SHOWN_USED` |
| NEU_RELN | 0.561 | 0.439 | `NOT_SHOWN_USED` | 2.079 | `NOT_SHOWN_USED` | `NOT_SHOWN_USED` |
| NEU_RORB | 0.556 | 0.444 | `NOT_SHOWN_USED` | 2.079 | `NOT_SHOWN_USED` | `NOT_SHOWN_USED` |
| NEU_SST | 0.538 | 0.462 | `NOT_SHOWN_USED` | 2.079 | `NOT_SHOWN_USED` | `NOT_SHOWN_USED` |
| NEU_TLE4 | 0.552 | 0.448 | `NOT_SHOWN_USED` | 2.079 | `NOT_SHOWN_USED` | `NOT_SHOWN_USED` |
| NEU_low | 0.544 | 0.456 | `NOT_SHOWN_USED` | 2.079 | `NOT_SHOWN_USED` | `NOT_SHOWN_USED` |
| OPC | 0.552 | 0.448 | `NOT_SHOWN_USED` | 2.079 | `NOT_SHOWN_USED` | `NOT_SHOWN_USED` |
| RG | 0.528 | 0.472 | `NOT_SHOWN_USED` | 2.079 | `NOT_SHOWN_USED` | `NOT_SHOWN_USED` |
| RG_prol | 0.519 | 0.481 | `NOT_SHOWN_USED` | 2.079 | `NOT_SHOWN_USED` | `NOT_SHOWN_USED` |
| VASC | 0.567 | 0.433 | `NOT_SHOWN_USED` | 2.078 | `NOT_SHOWN_USED` | `NOT_SHOWN_USED` |

## R4_ca program-module attention

Per-cell-type mean k_R×k_A matrices are in `routing_attention.json` (`R4_ca_tag` = `NOT_SHOWN_USED`). Top genes/regions per token (first fold annotation) are under `R4_ca_annotations`. No biological interpretation is offered for `NOT_SHOWN_USED` readouts.

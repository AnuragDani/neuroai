# Evidence boundary — next action 2026-10-03

Date: 2026-10-03. Scope: pin accepted scientific evidence before paper edits or the offline desk decision.
No fits, downloads, research network requests, external scores, submissions, messages or push occurred while producing this record.
Original MOM records and raw gate artifacts were read only; none were rewritten.

## Professor vs worker distinction

| Kind | What it is | Sources used here | Role in this boundary |
|---|---|---|---|
| Professor meeting records | Original guidance on direction, benchmarks and fairness | `MOM/README.md`; `MOM/2026-07-02/README.md`; `MOM/2026-07-21/README.md` (indexes to vault originals) | Direction only. Not a numerical acceptance gate. |
| Worker scientific gates | Measured outcomes, labels and stop decisions | Live verifier/summary JSON; M10/E5/S7/S8/S9/S10/Q2 artifacts below | Binding for paper numbers and scientific labels. |

This record does **not** assert new professor endorsement. Worker labels below remain worker evidence.
When a dated narrative conflicts with a live gate leaf, the gate leaf wins.

## Runnable verification (saved-fold replay)

Command (no `--write`; no learning):

```sh
.venv-p22/bin/python gnhf/verify_ladder.py --run reports/generated/nn_20260923/ladder_v3
```

Live result (2026-10-03):

- `verdict`: **PASS**
- `primary_recomputed.estimate`: `0.026666666666666672`
- `primary_recomputed.ci`: `[-0.024999999999999967, 0.07678571428571429]`
- `primary_recomputed.valid_draws`: `1000`
- `primary_recomputed.margin`: `0.07`
- `primary_recomputed.advantage`: `false`
- `problems`: `[]`
- Note retained: majority pooled BA 0.300; fold-wise thresholds depress pooled majority BA; report AUROC alongside BA.

Primary arm pair is hard-coded in `gnhf/verify_ladder.py` as `R3_ca` − `R3_tc` (lines setting `ca, tc = "R3_ca", "R3_tc"`).

## Primary contrast and outcome

| Item | Accepted value | Exact source leaf |
|---|---|---|
| Primary model | `R3_ca` | `docs/nn_v2/ladder_summary.json` → `primary.model` |
| Primary reference | `R3_tc` | `docs/nn_v2/ladder_summary.json` → `primary.reference`; also `gnhf/verify_ladder.py` arm pair |
| BA contrast (R3_ca − R3_tc) | `+0.02667` (exact `0.026666666666666672`) | `docs/nn_v2/ladder_verification.json` → `primary_recomputed.estimate` |
| Replay 95% CI | `[-0.0250, +0.07679]` (exact `[-0.025000000000000022, 0.07678571428571423]` on disk; live replay above agrees within float noise) | `docs/nn_v2/ladder_verification.json` → `primary_recomputed.ci` — **use this**, not the summary’s older CI |
| Margin | `0.07` | `primary_recomputed.margin` |
| Advantage | `false` | `primary_recomputed.advantage` |
| Primary scientific label | **`B_NULL`** | `docs/nn_v2/ladder_summary.json` → `outcome`; preserved in M10 `preserved_labels.primary` and E5 `scientific_status_unchanged.primary` |

Summary older CI (`primary.ci` ≈ `[-0.02672, 0.07704]`) is retained as historical summary text only. Paper and this boundary cite the replay CI.

## Absolute saved-result arm metrics

Source: `docs/nn_v2/ladder_verification.json`, `record_type=ladder_verification`, leaves `per_arm.<arm>.{balanced_accuracy,auroc,parameter_count}`.
These are descriptive saved-result metrics, not new model selection. R4 capacity differs from R3.
`parameter_count` zeros are the verifier’s recorded entries; they do not establish that fitted logistic models have zero coefficients.

| Accepted saved-result arm | BA | AUROC | Recorded parameters |
|---|---:|---:|---:|
| R3_ca | 0.4000 | 0.3582 | 384,250 |
| R3_tc | 0.3733 | 0.3316 | 380,026 |
| R4_ca | 0.5267 | 0.5147 | 29,970 |
| R4_tc | 0.5000 | 0.4427 | 25,746 |
| logreg_concat | 0.4133 | 0.3822 | 0* |
| Pseudobulk RNA logistic | 0.5133 | 0.5573 | 0* |
| chr21_dosage | 1.0000 | 1.0000 | 0 |

Exact live leaves (rounded above to four decimals as in the plan table):

| Arm | `balanced_accuracy` | `auroc` | `parameter_count[0]` |
|---|---:|---:|---:|
| R3_ca | 0.4 | 0.3582222222222222 | 384250 |
| R3_tc | 0.37333333333333335 | 0.33155555555555555 | 380026 |
| R4_ca | 0.5266666666666666 | 0.5146666666666666 | 29970 |
| R4_tc | 0.5 | 0.44266666666666665 | 25746 |
| logreg_concat | 0.4133333333333334 | 0.38222222222222224 | 0 |
| pseudobulk_rna_logistic | 0.5133333333333333 | 0.5573333333333333 | 0 |
| chr21_dosage | 1.0 | 1.0 | 0 |
| majority (caveat arm) | 0.30000000000000004 | 0.3 | 0 |

### Caveats pinned with the absolute metrics

- Fold-wise thresholds depress pooled majority BA to 0.300; majority pooled AUROC is also 0.300 (`ladder_verification.json` → `notes[0]`).
- Report AUROC alongside BA. Do not explain every below-chance neural result solely as a threshold artifact.
- The zero-parameter dosage control is not neural multimodal improvement or a cell-state endpoint.
- Chance-level metrics do not prove that no signal exists. They provide no current evidence for useful transportable neural performance.

## Scientific labels preserved

| Label | Value | Exact source leaf |
|---|---|---|
| M9 scientific acceptance | **`NOT_AUTHORIZED`** | M10 `VERIFICATION.json` → `scientific_acceptance_of_M9` |
| M10 replay use | **`REPLAY_PASS_DIAGNOSTIC_ONLY`** (diagnostic-only) | M10 `VERIFICATION.json` → `diagnostic_replay_disposition` |
| S7 (v1) | **`INVALID`** | `docs/nn_v2/s7/S7_RESULT.json` → `scientific_label`; also M10 `preserved_labels.S7` |
| S7-v2 | **`INVALID`** | `docs/nn_v2/s7_v2/S7_V2_RESULT.json` → `scientific_label` |
| S9 | **`INVALID`** | `failure_audit_20261001/s9_audit.json` → `scientific_label_retained`; M10 `preserved_labels.S9` |
| S10 | **`INVALID`** | `failure_audit_20261001/VERIFICATION.json` → `scientific_result` / `scientific_invariants.s10_selected_experiment` |
| S8 | **`NO FIT`** | `continuation/DECISION.md` disposition; M10 `preserved_labels.S8`; E5 `prior_S8` |
| E5 | **`NO_GO`** | `tasks/decision_e5.json` → `disposition` / `verdict` |
| Q2 endpoint | **`ENDPOINT_UNRESOLVED`** | `next_stage_20260930/ENDPOINTS.md` disposition; M10 `preserved_labels.Q2` |
| Power | **`POWER_UNESTABLISHED`** | S7/S7-v2 `biological_power`; S10 `scientific_invariants.power` |
| Primary | **`B_NULL`** | `ladder_summary.json` → `outcome` |

No disagreement was found between these live leaves and the Task 1 acceptance table in `PLAN.md`. Checkpoint A may proceed.

## Source path and SHA-256 register

Hashes computed 2026-10-03 from the primary checkout (read-only).

| Path | SHA-256 |
|---|---|
| `docs/nn_v2/ladder_verification.json` | `aec19fda88d60a30fda4ebdb9af53c790c62d5210206a5627c54521bfd947256` |
| `docs/nn_v2/ladder_summary.json` | `9add634e69dfbd7de1f764d6d7d3e3a217101efec2445c426b1b7be3f4ebc4c7` |
| `gnhf/verify_ladder.py` | `e63224dc33577f1618c615d3546d0d26204b09c01951d74e29e77f33b0cf0c6b` |
| `tasks/decision_e5.json` | `9ca776ae11b742ffc8a0901eff33b5cce31164a37a207190f916f425542f0fd7` |
| `tasks/DECISION_E5.md` | `edff6817e595b8b16253e4b876ea7b5e19993c91162b0cd1c8ebb4a60ae6ecea` |
| `tasks/nn/professor_direction_investigation_20260929/masked_atac_pilot_20261001/VERIFICATION.json` | `193b29239adbcb4d47848aa17d5850359d9c3203bf3189946b1e4a44585da179` |
| `tasks/nn/professor_direction_investigation_20260929/masked_atac_pilot_20261001/HANDOFF.md` | `8b737cfe40b6e006f414505d6afe3e4b791cbac39a79aa2480445282ee2ea499` |
| `docs/nn_v2/s7/S7_RESULT.json` | `8456440992a21355849b9a8738c558200c3d583cbe0bffb0f9199e595dc244d9` |
| `docs/nn_v2/s7_v2/S7_V2_RESULT.json` | `cc5758f722d21c0c4870305e4a15fb4a4e70e809ec3183d52df5ec90e9c741bf` |
| `tasks/nn/professor_direction_investigation_20260929/continuation/DECISION.md` | `fb4c57f70f6e27543597995aa2b8a848980f776feefd517d62d4d6e56c16744f` |
| `tasks/nn/professor_direction_investigation_20260929/continuation/HANDOFF.md` | `c550bd1752d9492222beb6866fc93aa773a5541c93e68728dbfd1f7aca7853c0` |
| `tasks/nn/professor_direction_investigation_20260929/next_stage_20260930/ENDPOINTS.md` | `4c93e45b4b7cb98a986fb4e65aacb10648eb0966d04f3299854a89011b9fa636` |
| `tasks/nn/professor_direction_investigation_20260929/failure_audit_20261001/s9_audit.json` | `a642f898a698d711cd86fd01a5e1ae73a6309712006c10590248f64cf9c4205d` |
| `tasks/nn/professor_direction_investigation_20260929/failure_audit_20261001/VERIFICATION.json` | `d4dcda8c0e4dbd3631b7494af1f59ecce120562d6541f3e4e823fde13ddf1564` |
| `MOM/README.md` | `18e8c8ade62a075097a09e1da7565c5a6c33566d5298f0f319e5d9fb2ed6a4c9` |
| `MOM/2026-07-02/README.md` | `d411701b09dc34cfaf0674ea82733341ff8cd3355d9dd1823666242845212fa0` |
| `MOM/2026-07-21/README.md` | `cf732e339e5348d260c121b10f5b0f4dcb15d276cdf3bdaf5aadb3c7ee25e0e6` |

## Checkpoint A disposition

**PASS.** Live replay PASS; primary R3 pair, replay CI, absolute metrics and every listed scientific label agree with their exact source leaves. No blocker. Tasks 2 and 3 may start from this pinned boundary.

## Scope note

This boundary freezes what the bounded paper and desk decision may cite as accepted. It does not authorize fits, acquisition, external scoring, packet send or submission.

# Independent review of S7-v2 handoff — 2026-09-29

**Decision: accept the stop and `INVALID` scientific label; do not merge or rerun this frozen batch.** The 12-iteration GNHF summary contains one Cursor-output parse failure. That iteration still wrote the 14 smoke fits. The next iteration verified them; the final durable ledger contains 119 unique `ok` IDs (14 smoke + 105 screen), no confirmation fits. The failed iteration is an orchestration error, not a failed scientific fit.

## Gate recomputation from raw donor sidecars

I loaded each of the five `screen` fold sidecars per arm from `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929/donor_predictions/`. Each arm/rho has 30 distinct held-out donors. `sklearn.metrics.balanced_accuracy_score` on the pooled 30 donor labels/predictions gives:

| Model | rho=0 pooled donor BA | rho=1 pooled donor BA |
|---|---:|---:|
| cross_attention | 0.357143 | 0.321429 |
| token_concat | **0.330357** | 0.357143 |
| rna_atac_concat | 0.357143 | 0.392857 |
| gated_fusion | **0.325893** | 0.357143 |
| logreg_concat | 0.388393 | 0.357143 |
| logreg_rna | 0.357143 | 0.357143 |
| logreg_atac | 0.441964 | 0.441964 |

Frozen [v2 spec](../../../tasks/nn/s7_v2/BENCHMARK_SPEC.json) says rho-0 **pooled donor BA** must be in `[0.35,0.65]` for every complete arm. Both token-concat and gated-fusion fail. The implemented `null_check` in `src/p22/eval/s7_screen.py` instead uses **mean-fold BA**, and the GNHF [T7 handoff](T7_SCREEN.md) cites token-concat 0.341667. This is a protocol/implementation mismatch, but it does **not** change the `INVALID` label: the prespecified pooled check also fails. Do not revise the threshold or use the alternative statistic to promote this run.

At rho=1, pooled CA BA is 0.321429 versus best N4 non-attention fusion arm (`rna_atac_concat`) 0.392857, a CA gap of −0.071429. Thus fixed-cell `CA_FAVOURED` fails even apart from the rho-0 control. Saved pairing diagnostic reports CA donor log-loss drop −0.000143, 95% CI [−0.003847, 0.004451], with 1000/1000 valid draws and `PC_FAIL`; I checked the recorded gate and checkpoint coverage, but did not independently rerun 32 interventions. Confirmation was correctly skipped.

## Handoff caveats

- `docs/nn_v2/s7_v2/S7_RESULT.md` and `.json` were emitted by the reused writer with the **v1** top-level protocol ID. The separate [versioned result](S7_V2_RESULT.md) and [T10 handoff](T10_HANDOFF.md) identify v2 correctly and should be the reader entrypoints. Do not treat the unversioned files as independent v1 evidence.
- T4 recorded 110 focused/planted and 1378 full-suite tests passed before fits. This review recomputed saved outcomes; it did not rerun the full suite or modify fitting code.
- Old S7-v1 remains `INVALID`; biological primary remains `B_NULL`; power remains `POWER_UNESTABLISHED`. No new biological positive claim follows from an invalid synthetic control.

## Next decision

Keep this v2 run frozen. If pursuing another control, first decide whether the fixed rho-0 null range is a suitable design check at 30 donors and specify the evaluation statistic unambiguously **before** any new fits. A new design must have a new protocol/version and independently justified objective; no seed or threshold search on these outcomes. The bounded internal null paper remains ready as the alternative.

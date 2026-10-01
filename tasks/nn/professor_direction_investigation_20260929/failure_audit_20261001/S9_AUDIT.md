# S9_AUDIT — R1 replay of immutable S9 evidence

**Disposition:** `REPLAY_PASS` (scientific label retained `INVALID`)
**Date:** 2026-10-01
**Protocol:** `S9_analytic_pairing_use_synthetic_20260930`
**Shared S9 raw (read-only):** `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-engineering-20260928-gnhf-worktrees/read-tasks-nn-finish-ee2202-gnhf-worktrees/read-users-anuragdan-b61180-gnhf-worktrees/execute-the-p22-data-146414/reports/generated/nn_s9_analytic_pairing_20260930`
**Shared raw unchanged:** `True` (tree SHA-256 `0309b6c9d5d4715dbb624bffc757d69b1a7fe630203153d3f0719e53848fe549`)
**Research fits this replay:** 0

## Coverage

- Planned/attempted/ok/failed: 49/49/49/0
- Ledger rows / unique fit_ids: 49 / 49
- Complete: `True`
- Sidecar+checkpoint SHA-256 vs ledger: `True` (49 preds; 12 ckpts)

## Per-arm pooled donor BA (ρ=1 screen)

| Arm | Pooled BA | Independent match |
|---|---:|:---:|
| `cross_attention` | 0.625 | `True` |
| `token_concat` | 0.625 | `True` |
| `gated_fusion` | 0.6666666666666667 | `True` |
| `rna_atac_concat` | 0.6666666666666667 | `True` |
| `logreg_concat` | 0.625 | `True` |
| `logreg_rna` | 0.75 | `True` |
| `logreg_atac` | 0.7083333333333334 | `True` |

## Marginal / pairing / advantage

- Marginal pass (≤0.6): `False` (RNA 0.75; ATAC 0.7083333333333334)
- CA ρ=1 pairing: `PAIRING_NEGATIVE` (ll-drop CI lower -6.494849443633859e-06)
- CA ρ=0 pairing: `PAIRING_POSITIVE` (ll-drop CI lower 1.3105791989196136e-05)
- Advantage SEPARATE_NON_PRIMARY CA−TC: 0.0 (CA 0.625; TC 0.625)
- Interpretation: `INVALID` — rho=1 unimodal marginal BA exceeds 0.60 (logreg_rna/logreg_atac shortcut)

## Matches prior execute.json

- `disposition`: `True`
- `marginal_rna`: `True`
- `marginal_atac`: `True`
- `pairing_rho1_label`: `True`
- `pairing_rho0_label`: `True`
- `rho1_ll_drop_lower`: `True`
- `rho0_ll_drop_lower`: `True`
- `advantage_ca_ba`: `True`

## Pipeline trace

1. **generator** — `s9_analytic.generate_analytic_arrays / assign_donor_labels` (seed=9001; 24 donors; rho in {0,1})
1. **split** — `s9_analytic.allocate_s9_folds` (F=3 class-quota SHA256; both classes every fold)
1. **fit** — `s9_execute.run_one_s9_fit → s7_runner.fit_s7_arm` (model_seed=9001; max_epochs=20; workers=2 torch_threads=2)
1. **checkpoint** — `s9_execute.save_s9_checkpoint` (retain screen CA/TC only (12 files); state_dict+protocol)
1. **reload** — `s7_runner.reload_checkpoint_predictions` (identity atol 1e-6 before shuffle scoring)
1. **shuffle** — `s9_analytic.permute_atac_within_donor` (PAIRING_SHUFFLE_SEEDS (16); within-donor marginal preserved)
1. **aggregate** — `group_splits.aggregate_donor_probabilities` (held-out donors pooled once across folds)
1. **bootstrap** — `s7_pairing.evaluate_pairing_pc` (1000 draws; seed from S7_BOOTSTRAP_SEED; min_valid=1000)
1. **gate** — `s9_execute.interpret_batch` (unimodal marginal BA≤0.6; primary CA pairing ll-drop CI; INVALID on marginal FAIL)

## Review chronology

- Q7 PROTOCOL_FROZEN (generator/split/null/fit arithmetic)
- Q8 IMPLEMENT_PASS (s9_analytic + dry-run; 0 research fits)
- Q9 independent review PASS (agent 393c27bd…; no self-cert)
- Checkpoint C authorize research fits under reviewed hashes
- Q10 execute 49/49 → INVALID (unimodal marginal FAIL)
- Q12 handoff preserves INVALID; biological pilot BLOCKED

- Q9 verdict `PASS`; reviewer `393c27bd-2487-49eb-8225-ddd76b74ec4a`; correction_cycle `0`
- Note: Q9 reviewed protocol/code/test hashes and checklist 1–10; Q10 executor s9_execute.py was authored after Q9 and was not re-hashed under the Q9 REVIEWED_HASHES lock (post-review execution path). R1 records this chronology; cause claims deferred.

## Optimization provenance

- Retained CA/TC screen checkpoints: 12/12
- Any epoch/learning history in checkpoints: `False`
- Sum ledger seconds: 5.234899454993865
- Five-second cumulative fit wall alone neither proves nor refutes adequate learning; epoch/selection history is absent from saved checkpoints (state_dict + protocol dims only).

## Failure-category distinctions

| Category | Applies | Evidence |
|---|---|---|
| protocol_failure | `True` | Frozen unimodal marginal gate FAIL: logreg_rna BA 0.75 and logreg_atac BA 0.7083333333333334 both > 0.6. Primary INVALID retained; not a method claim. |
| implementation_deviation | `False` | Replay recomputes identical disposition/labels/CI lowers versus prior execute.json; donor prediction and checkpoint SHA-256 match ledger; live splits match SPLIT_MANIFEST; oracle gate PASS. |
| uncertain_optimization | `True` | Retained checkpoints store state_dict + protocol dims only; no epoch/learning_history/selection metrics. Cumulative ledger seconds=5.2349 cannot alone establish under-training or adequacy. Leave optimization uncertain. |
| statistical_fluctuation | `False` | Primary INVALID is a hard marginal threshold exceedance on all 24 donors (pooled), not a borderline CI that could flip under resampling of the same saved predictions. |
| missing_provenance | `True` | Epoch/selection history absent from checkpoints; Q10 executor module was not under the Q9 REVIEWED_HASHES lock (chronology note). Does not overturn saved INVALID label. |

## Invariants preserved

- S9 scientific label remains **`INVALID`** (immutable; replay does not rewrite old summaries).
- Primary `B_NULL`; S7 `INVALID`; prior S8 `NO FIT`.

## Next

R2 null-exchangeability / marginal diagnosis (≤256 generator-only draws; 0 fits). Checkpoint A after R1+R2.

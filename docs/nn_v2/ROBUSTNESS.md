# NN-v2 robustness (D13, D9) — tasks N11, N12

## Source binding

- Accepted with-chr21 ladder: `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v2` (`folds_done=450`, `failures=[]`; verifier PASS).
- N11 no-chr21 folds: `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/chr21_excluded` (`folds_done=100`, `failures=[]`; arms R3_ca, R3_tc, logreg_rna, logreg_concat × 5 repeats × 5 folds). Same donor splits as ladder_v2; frozen architecture widths (~384k R3_ca params), not the superseded buggy `ladder/` (~99k).
- N12 seed folds under `…/seeds/m_*_s_*` use the **buggy** ~99k-param protocol and are **not** accepted against ladder_v2. Do not reuse; rerun required.

## chr21-excluded sensitivity (N11)

Rebuilt `docs/nn_v2/chr21_excluded.json` by comparing chr21-excluded fold predictions to ladder_v2 (not the old `ladder/`). Decision-tree N11: all no-chr21 BA ≤ 0.55 → **DOSAGE_DOMINATED**. Per-arm no-chr21 BA: R3_ca 0.373, R3_tc 0.380, logreg_rna 0.480, logreg_concat 0.460. Paired with−without differences are near zero for R3 arms and small for logreg (CIs include or touch 0 except logreg_concat lower bound 0). Interpretation is limited to this internal 30-donor cohort; model-free chr21 dosage remains near-perfect on the same ladder.

## Init-seed and sampling-seed sensitivity (N12)

**Not accepted.** Robust-lane `seed_sensitivity.json` summarized runs whose fold `parameter_count` (~98874 for R3_ca) matches the superseded buggy ladder, not ladder_v2 (~384250). Status remains TODO pending a fixed-protocol seed rerun (model seeds 0–4 at sampling 22; sampling seeds 23–24 at model 0; arms R3_ca/R3_tc only).

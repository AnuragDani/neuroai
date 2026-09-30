# DRAFT / NO FITS — S8 pairing-use prospective control

**Protocol ID (draft):** `S8_pairing_use_DRAFT_20260929`  
**Kind:** prospective semisynthetic pairing-use diagnostic only  
**Status:** DRAFT / NO FITS — not frozen for execution; no model fits authorized by this file  
**Parent:** `LANE_B.md` (same folder)  
**Does not modify:** S7-v1, S7-v2, ladder_v3, scientific JSON, thresholds of past batches

## Hypothesis (non-advantage)

Under the known S7 covariance plant at ρ=1, does the existing cross-attention implementation show donor-level sensitivity to within-donor ATAC pairing shuffles that preserve ATAC marginals?

## Generative equation (reuse; not novel)

For each donor and paired channel, draw independent Gaussians `z,w` from SHA256(seed, donor_id, channel); centre/scale `z` to variance 1; orthogonalize/centre/scale `w` against `z`; set:

```
RNA = z
ATAC = (2*y_d - 1) * rho * z + sqrt(1 - rho^2) * w
```

Other transformed columns unchanged. Fake labels via `fake_donor_labels` with tag `prospective-s8:<generator_seed>`; never train on real disease labels. Row identity: stable `cell_id` order. Source of equation: frozen S7-v2 spec / `plant_covariance` (read-only reference).

## Primary estimand and statistic

- **Estimand:** mean held-out-donor log-loss increase under within-donor ATAC shuffle vs identity, CA ρ=1 screen checkpoints.  
- **Statistic (exactly one primary):** mean donor ll-drop; 1000 donor-bootstrap draws; seed 22; paired shared draws; PASS iff estimate > 0 and 95% CI lower > 0.  
- **Not primary:** CA−baseline balanced-accuracy margin; mean-fold BA.

## Arms and budget equality

Arms: `cross_attention`, `token_concat`, `rna_atac_concat`, `gated_fusion`, `logreg_concat`, `logreg_rna`, `logreg_atac`.  
Training: N4/S7 neural defaults (max_epochs 20 screen path, patience 5, lr 1e-3, batch 64, n_tokens 8, embed 32, hidden 128, n_heads 4, dropout 0.2); identical available budget; CA/TC parameters within 10% or refuse; no hyperparameter sweep.

## Splits

Reuse S7-v2 deterministic class-quota donor allocation (16/14 fake; test quotas class-0 [4,3,3,3,3], class-1 [2,3,3,3,3]; inner 4+4 val). Split seed 0; generator seed screen 1001. Validate all outer+inner class presence before any fit.

## Evaluation statistic resolution

| Use | Statistic |
|---|---|
| All PASS/FAIL gates | **Pooled** donor BA (30 held-out donors) |
| Descriptive only | Mean-fold BA / AUROC |
| Pairing primary | Donor log-loss drop (above) |

## Null / marginal gates (prospective)

- **ρ=0 null:** every complete arm’s **pooled** BA inside the central 95% band of a **pre-fit chance calibration** (≥10k draws; constant-0.5 and Bernoulli-0.5 predictors on frozen fake labels/splits). Do **not** hardcode `[0.35, 0.65]` without that artifact. Missing calibration → no fits / `INVALID`.  
- **ρ=1 marginal:** `logreg_rna` and `logreg_atac` pooled donor BA ≤ 0.60.  
- **ρ=0.5:** descriptive only.

## Gate order and labels

1. Preflight/split → 2. Smoke → 3. Screen coverage → 4. ρ=0 null → 5. ρ=1 marginal → 6. Pairing PC.  

Labels: `INVALID` | `PAIRING_NEGATIVE` | `PAIRING_POSITIVE`.  
Precedence: `INVALID` wins over pairing labels. No advantage confirmation stage. Never relabel S7.

## Pairing intervention

32 seeds 3001–3032; permute ATAC rows within each held-out donor; preserve marginal multiset; identity reload abs diff ≤ 1e-6; insufficient valid bootstrap draws (<950) → incomplete/`INVALID`.

## Fit budget

| Stage | Attempted fits |
|---|---:|
| Smoke | 14 |
| Screen | 105 |
| Advantage confirmation | 0 |
| Pairing (new fits) | 0 |
| Planned total | 119 |
| Hard cap | 150 |

Count attempted jobs, not only `ok`. Cap breach → stop `INVALID`.

## Falsifier

Valid screen + CA pairing ll-drop 95% CI lower ≤ 0 ⇒ `PAIRING_NEGATIVE`.

## Output root (when later authorized)

`reports/generated/nn_s8_pairing_use_<date>/` — new tree only. Not authorized by this draft.

## Literature anchors (technical adaptations only)

Ilse et al. 2018 MIL [B1]; Ganin domain-adversarial [B2]; CPC/CLIP pairing losses [B3]/B4]; Transformer / multimodal attention [B5]–[B7]; attention-is-not-explanation caveat [B11]. No novelty claim.

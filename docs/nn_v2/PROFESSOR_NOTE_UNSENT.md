# Unsent note to professor (draft only — do NOT send)

Status: real-data NN-v2 ladder accepted as a **null** on canonical **`ladder_v3`**
(rebuild after a shared-path control-fit fix; `ladder_v2` retained). Primary contrast
R3_ca − R3_tc donor balanced accuracy ≈ **0.0267**, 95% CI includes 0 (summary ≈
[−0.027, 0.077]; verifier recomputed ≈ [−0.025, 0.077]), margin 0.07 not met →
**`B_NULL`**. Gate `docs/nn_v2/ladder_verification.json` = **PASS** on all 450 folds.
No complex-model superiority claim. RNA logistic remains competitive
(`LINEAR_SUFFICIENT`); model-free chr21 dosage AUROC **1.0**.

**Validity (v5).** Pooled AUROC for learned arms can look below chance while
**per-fold AUROC** means stay above chance (e.g. R3_ca per-fold mean ≈ 0.656 vs
pooled ≈ 0.366) — a pooling artefact across stratified folds; report both
(`docs/nn_v2/v5/per_fold_metrics.json`). Forced-chr21 positive control through the
full pipeline: logreg donor AUROC **0.924**; default HVG keeps ~31/538 chr21 genes.
Sklearn controls were under-trained on the inner-train third; fitting on full outer
train fixed that path (`PIPELINE_BUG_FIXED` → rebuild as `ladder_v3`). Predictions
were not flipped.

Chr21-excluded arms stay ≤ 0.55 BA → **`DOSAGE_DOMINATED`** (this cohort only). Seed
spreads are modest (`SPREAD_ONLY`; model 0.073, sampling 0.033). Cell-state spectrum
on held-out R3_ca scores: **`SPECTRUM_NULL`** (9 eligible; no Holm-significant
DS−CON difference), including on chr21-excluded scores (P3). Faithfulness: identity
NC exact zero; **`CA_PAIRING_UNUSED`**; **`ATAC_USED`** on R3_tc I1; attention/routing
readouts all **`NOT_SHOWN_USED`**. Adversary rung **`R2_REJECTED`** (probe drop
insufficient). Optional gene-activity secondary ladder: **`GA_B_NULL`** (500-gene
amendment) — not external validation.

Planted benchmark (synthetic labels): **no** scenario favoured cross-attention,
including gene-matched RNA×ATAC interaction S6 (P2; both δ cells
`LINEAR_SUFFICIENT`; `any_ca_favoured=false`). Additive regimes are linear-sufficient;
pairing-only favoured gated fusion / MLP.

Limits to keep visible: 30 donors; internal cohort; same-cohort annotations; region
panel not regulatory; attention ≠ explanation; pairing PC not refit; prefer per-fold
AUROC alongside pooled metrics. Paper draft still `DRAFT_V1_COMPLETE` pending P6.
Full D1–D13 coverage table: `docs/nn_v2/v5/PROFESSOR_UPDATE_v5.md` (unsent). This note
is **unsent**.

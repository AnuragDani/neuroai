# Unsent note to professor (draft only — do NOT send)

Status: real-data NN-v2 ladder accepted as a **null**. Primary contrast R3_ca − R3_tc
donor balanced accuracy ≈ **−0.0067**, 95% CI includes 0 (summary ≈ [−0.053, 0.035];
verifier recomputed ≈ [−0.053, 0.035]), margin 0.07 not met → **`B_NULL`**. Gate
`docs/nn_v2/ladder_verification.json` = **PASS** on all 450 folds. No complex-model
superiority claim. RNA logistic remains competitive (`LINEAR_SUFFICIENT`); model-free
chr21 dosage AUROC ≈ **0.998**.

Chr21-excluded arms stay ≤ 0.55 BA → **`DOSAGE_DOMINATED`** (this cohort only). Seed
spreads are small (`SPREAD_ONLY`). Cell-state spectrum on held-out R3_ca scores:
**`SPECTRUM_NULL`** (9 eligible types; no Holm-significant DS−CON difference).
Faithfulness: identity NC exact zero; **`CA_PAIRING_UNUSED`**; **`ATAC_USED`** on some
non-CA arms; attention/routing readouts all **`NOT_SHOWN_USED`**. Adversary rung
**`R2_REJECTED`** (probe drop insufficient). Optional gene-activity secondary ladder:
**`GA_B_NULL`** (500-gene amendment) — not external validation.

Planted benchmark (synthetic labels): **no** scenario favoured cross-attention over the
best simpler model; additive regimes are linear-sufficient; pairing-only favoured gated
fusion / MLP.

Limits to keep visible: 30 donors; internal cohort; same-cohort annotations; region panel
not regulatory; attention ≠ explanation; pairing PC not refit; chr21 cell-score export
deferred. Paper rewrite and vault copy still pending on this branch. This note is
**unsent**.

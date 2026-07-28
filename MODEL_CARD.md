# Model Card

**Purpose:** synthetic-only comparison of single-view and fusion baselines with
routing faithfulness checks
**Approval state:** blocked — no condition-specific training
**Device:** CPU default

## Families (verified)

Neutral view names `view_a` and `view_b`:

1. Logistic regression on view A
2. Logistic regression on view B
3. MLP on view A
4. MLP on view B
5. Concatenation fusion
6. Gated fusion (`RoutingGate` + `GatedFusionModel`)

Gated fusion is a routing MLP over concatenated branch embeddings followed by a
weighted sum. It is not query/key/value cross-attention. Legacy Tasic outputs
may still say "attention fusion"; that name belongs to the frozen legacy
experiment, not to `GatedFusionModel`.

`FusionOutput` fields: `logits`, `routing_weights`, `branch_embeddings`,
`fused_embedding`. Routing weights are non-negative and sum to one. Validated
overrides `[1, 0]`, `[0, 1]`, and `[0.5, 0.5]` are supported for interventions.
Concatenation reports uniform 0.5 weights and `has_gate = False`.

## Training contract (verified)

Order fixed by `p22.training`: donor split → train-only transforms → train →
validation selection → one test read (`SingleUseHoldout`). Seeds control
Python, NumPy, and PyTorch. Non-synthetic data modes are refused while approval
is blocked.

## Metrics (verified)

Accuracy, balanced accuracy, macro/weighted F1, macro-OvR AUROC when defined,
multiclass ECE, donor-cluster bootstrap, McNemar, Cohen's h, five-seed
summaries. Undefined metrics return an explicit `not_applicable` reason, never
a silent NaN. Bootstrap resamples whole donors.

## Routing language (verified)

Routing weights are signals about contribution to the fused representation.
They are not causal explanations. Dependence claims require held-out
intervention evidence from `p22.eval.faithfulness`.

## Interventions (verified)

Clamp view A/B, permute view A/B within donor, ablate view A/B embedding, fixed
uniform route. Report flip rate, confidence drop, metric drop, routing shift,
per-donor and per-label summaries. Permutations never cross donors. Outputs are
labelled intervention evidence, not causal biology.

## Limitations

- Synthetic numbers carry no biological meaning
- Small donor counts make intervals wide
- Five seeds show spread; overlapping intervals mean no separation claim
- Tasic legacy results are not independent-modality or condition-specific evidence
- No approved real dataset is present

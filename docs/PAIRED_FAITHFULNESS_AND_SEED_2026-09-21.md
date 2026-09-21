# Real paired pilot: faithfulness and initialization sensitivity

Date: 2026-09-21 · Run: `p22-results-executio-debda8` · Status: **pilot executed**

This closes the two evidence gaps left by the real paired pilot
(`docs/DEVELOPMENT_PAIRED_INPUT_AND_PILOT_2026-09-21.md`): held-out faithfulness
interventions scored at the donor level, and initialization-seed sensitivity of the
primary cross-attention vs matched token-concat contrast. It is still a **pilot**:
one outer fold (repeat 0, fold 0) and one donor split. It is not a final estimate,
not external validation, and its predictions must not be used to select
outcome-favourable donors.

## 1. Inputs and fold (unchanged from the pilot)

- RNA: local CELLxGENE H5AD `X`, SHA-256 `08d6eff2…fcdbb`, 35,477 genes.
- ATAC: the frozen 256-region real count matrix, SHA-256 `b1b7e9e3…c307`
  (`reports/generated/development_region_set_20260921/counts/counts.npz`).
- 7,680 cells (256/donor, 30 donors); held-out test donors 6 (4 control / 2 DS);
  train 4,096 / val 2,048 / test 1,536 cells.
- Protocol SHA-256 `e66ff82f…1d5e`.

## 2. Faithfulness interventions (`experimental result`)

All seven held-out interventions were run per two-view family on the held-out test
cells only. The clamp value comes from the training views; permutations stay inside
each donor. The donor metric is the same mean-probability donor aggregation and 0.5
threshold as the primary estimand.

| family | clamp A donorΔ | ablate A donorΔ | clamp B donorΔ | ablate B donorΔ | uniform route |
|---|---:|---:|---:|---:|---|
| rna_atac_concat | 0.625 → 0.5 | 0.625 → 0.0 | 0.625 → 0.625 | 0.625 → 0.625 | NOT_APPLICABLE (no gate) |
| gated_fusion | 0.625 → 0.5 | 0.625 → 0.5 | 0.625 → 0.625 | 0.625 → 0.625 | 0.625 → 0.625, routing shift 0.42 |
| token_concat | 0.625 → 0.5 | 0.625 → 0.0 | 0.625 → 0.625 | 0.625 → 0.625 | NOT_APPLICABLE (no gate) |
| cross_attention | 0.625 → 0.5 | 0.625 → 0.0 | 0.625 → 0.625 | 0.625 → 0.625 | NOT_APPLICABLE (no gate) |

Cell-level flip rates: clamp/ablate of the RNA view flips 30–50 % of held-out
cells; the same interventions on the ATAC view flip 3–6 %. `verified` (within this
pilot): every two-view model's held-out prediction depends far more on the RNA view
than on the 256-region ATAC view. This is **intervention evidence under a stated
manipulation**, not a causal biological claim, and a routing weight is not an
explanation.

The gated model is the only family with a learned gate; the fixed-uniform-route
intervention is reported as `NOT_APPLICABLE` for the non-gated families rather than
silently skipped. The pilot's 256-region feature set is the likely reason ATAC
carries little signal; this is an input limitation, not an architecture finding.

## 3. Initialization-seed sensitivity (`experimental result`)

The donor split was held fixed and only the model initialization/optimization seed
changed (seeds 0, 1, 2):

- cross-attention donor balanced accuracy: 0.625, 0.625, 0.625 (spread 0.0);
- token-concat donor balanced accuracy: 0.625, 0.625, 0.625 (spread 0.0);
- primary delta (cross-attention − token-concat): 0.0, 0.0, 0.0 (spread 0.0).

`verified` (within this pilot): the null primary contrast is not an artifact of one
initialization seed. A zero spread over three seeds is **not** a stability
guarantee beyond the seeds actually run, and initialization-seed variability is
distinct from the still-unrun repeated donor-split variability.

## 4. What is verified vs proposed

- `verified` — real inputs and donor-isolated fold reused exactly from the pilot.
- `experimental result` — the intervention table and the seed-spread table above.
- `proposed` — the final protocol: stronger frozen region set, repeated donor
  splits (all 30 donors tested across folds), accepted normalization, and the
  primary contrast with donor-level uncertainty. The current pilot tests only 6
  test donors, so the bootstrap interval is degenerate.
- `unknown` — external cohort route (tar-packaged, per-file embargo).

## 5. Commands

```
.venv-p22/bin/python scripts/run_real_paired_faithfulness.py \
  --output-dir reports/generated/real_paired_faithfulness_20260921/run
.venv-p22/bin/python -m pytest -q -m "not slow"   # 899 passed, 32 deselected
.venv-p22/bin/ruff check scripts tests src && .venv-p22/bin/ruff format --check scripts tests src
```

Evidence: `docs/real_paired_faithfulness_2026-09-21.json` (tracked summary),
`reports/generated/real_paired_faithfulness_20260921/run/run.json` (full tables;
SHA-256 `576882b6d4ab96822a33e7612185e17153adc5fd1bbd2f3837de1079f65820f8`).
Code: `src/p22/eval/paired_faithfulness.py`, `scripts/run_real_paired_faithfulness.py`,
`tests/test_paired_faithfulness.py` (9 offline tests).

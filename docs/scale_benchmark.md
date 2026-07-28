# Larger Synthetic Scale Benchmark

**Date:** 2026-07-28
**Evidence labels:** `experimental result`, `verified`
**Data mode:** `synthetic`
**Approval state:** blocked pending Professor Fang
**Configuration:** `configs/scale_pilot.json`
**Notebook:** `notebooks/scale/11_scale_benchmark.ipynb`

## Human Gate

Can the local CPU pipeline process a meaningfully larger controlled workload
while preserving donor-held-out evaluation and train-only transforms?

## Observed Result

The scale notebook passed all checks.

| Tier | Workload | Result |
|---|---|---|
| Medium full pipeline | 64 donors, 6,400 cells, 256 features per view, six models, five seeds | PASS; 17.731 seconds; approximately 553 MB process peak RSS before stress tier |
| Stress data path | 128 donors, 32,000 cells, 1,000 features per view | PASS; 0.862 seconds for generation, split, and transforms; approximately 1,615 MB process high-water RSS |

Checks passed:

- approval remained blocked;
- all five medium seeds completed;
- all six model families produced outcomes for every seed;
- no donor crossed train, validation, or test splits;
- stress data contained only finite values;
- stress train-only transforms preserved both 1,000-feature shapes.

## Interpretation

This is local engineering evidence that the synthetic pipeline handles the
tested scale on CPU. It is not evidence that a real cohort is statistically
adequate, biologically informative, or externally valid.

The process RSS values are high-water measurements from one notebook kernel,
not a hardware-independent memory requirement. Re-run on the target machine
before making a resource commitment.

## Still Required For Real Data

- total donors and donors per class;
- cells per donor after QC;
- RNA/ATAC pairing rate;
- feature counts after train-only feature selection;
- donor-level precision or power criterion;
- real-data pilot runtime and memory;
- Professor Fang approval and a frozen target, split, metric, and success rule.

No real dataset was added or analyzed by this benchmark.

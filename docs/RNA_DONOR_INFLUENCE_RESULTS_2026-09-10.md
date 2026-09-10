# RNA donor influence: results, 2026-09-10

POST_HOC_EXPLORATORY. This completes the bounded F4–F5 RNA diagnostic, not the
full P22 plan. Original RNA results remain inconclusive; G8 is unchanged.
No paired predictive evaluation or real neural training ran.

## Result

All four saved baselines reproduced exactly, including donor order and saved
gene/donor/cell counts. Every donor was omitted once per comparison: 68/68
omissions available, each with design rank 4 and 12 residual degrees of freedom.

`PCW18_DS_16545` had the largest absolute same-support influence in each comparison.
The same donors contribute to every comparison; RG comparisons also share cells.
These are not four independent observations about that donor.

| Comparison | Baseline rho | Same-support delta omitting this donor | Omission rho | Share of absolute influence |
|---|---:|---:|---:|---:|
| RG → oRG | -0.007896 | +0.191714 | 0.183818 | 20.0% |
| RG → vRG | -0.030550 | +0.165192 | 0.134642 | 19.5% |
| cycling progenitors → CP | 0.096712 | +0.169408 | 0.266120 | 20.4% |
| IPC → IP | 0.009666 | +0.118950 | 0.128616 | 16.0% |

These shares describe concentration; they are not significance thresholds.
For this donor, the support delta was zero in all four comparisons. Across all
68 omissions, the largest absolute support delta was 0.000756456. At most five
baseline genes were lost and at most one new gene became eligible per omission.
New genes were counted but excluded from the diagnostic endpoint.

Decision: keep all donors and preserve the original conclusion. Do not select
donor exclusions to improve agreement. External-donor uncertainty remains
unresolved. Advance the separately planned paired-input feasibility tasks before
proposing real training; this diagnostic supplies neither common measured ATAC
counts nor accepted external QC.

## Execution and verification

- Implementation commit: `a0049f2960f796871ed9ed7b4971077200d48ae7`.
- Frozen config commit: `5be576c`; canonical config SHA256:
  `d51a69cc997fe3a80615ea76bdf9d9504a5334c05fe09eb8fe77a623d266cf58`.
- One real CPU run: 45.942 seconds; peak sampled RSS 4.141571 GiB.
  Limit: 1,800 seconds, stop at 5 GiB under a 6 GiB budget. Sampled monitoring
  is not a kernel hard ceiling. Both run and resource reports say `COMPLETED`.
- Final focused checks: 20 passed. Final full suite: 628 passed in 64.63 seconds;
  19 existing synthetic classification warnings. Lint/format: 108 files pass.
  Final fast suite: 596 passed, 32 deselected in 59.58 seconds.
- Fixtures check planted influence, stable data, absent class, rank failure,
  insufficient/constant/nonfinite effects, normalization, expression-floor support
  changes, decomposition, repeated-output determinism, refusal before omissions,
  all-unavailable reporting, no overwrite, and owned-child timeout/memory races.
- Original H5AD, workbook, reference CSV and four reused source helpers have
  identical before/after hashes. All 12 original dirty-file/notebook fingerprints
  matched after execution; original checkout status remains unchanged.
- Main verified resource completion, 68 unique rows, fit rank/df, delta arithmetic,
  implementation/artifact hashes and plot readability. Independent artifact
  review passed: exact baseline/Gi correlations, donor/class accounting, gene-set
  fingerprints and ranks; delta arithmetic error at most 1.39e-17. Full review
  is recorded in the delivered package. No second real refit was run; omission
  refit correctness rests on reviewed code and synthetic checks, not independent
  raw-count re-estimation during artifact review.

The local model supplied only a small test draft, which needed supervisor
correction. Core implementation and scientific decisions were supervisor-led
after explicit user approval; independent reviewers checked code and results.
The rejected local-only pilot report remains historical, not an accepted protocol.

## Artifacts and reproduction

See [the one-command guide](RNA_DONOR_INFLUENCE.md). Results are in
`reports/generated/rna_donor_influence_20260910_supervised/`: full donor table,
baseline genes, plot, summary, run/resource records and empty successful-run logs.
The original checkout receives an identical durable artifact copy plus a reviewed
Git bundle. No original evidence is overwritten; no push or merge is performed.
The bundle retains the isolated commits, not ignored source data or the shared
environment. Preserve the exact reference CSV and config paths when reproducing.

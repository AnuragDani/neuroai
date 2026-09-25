# Unsent note to professor (draft only — do NOT send)

Status: partial. The NN-v2 foundation is frozen and checked; the real-data ladder did not
run (upstream N10 stalled), so there is no DS result yet.

What is ready:
- Donor-aware sampler: 30 donors, cap 1000 cells/donor, 30,000 cells, seed 22, stratified
  donor×cell-type×library; historical 256-cap sample reproduced as reference.
- Leak-checked fold prep: 24 fit / 6 holdout donors, 2,000 RNA HVGs, 256 ATAC regions
  per fold (465 union), chr21 retained.
- An 18-arm, parameter-counted ladder with the primary contrast fixed at
  R3_ca − R3_tc (margin 0.07); matched token-concat twin is within 1.10% of CA params.
- ATAC gene-activity panel: 548 label-free chr21 regions, 548/548 complete joins,
  acceptance checker PASSED (11/11).

Your question "which scenario favours cross-attention vs a simple MLP?" now has a
benchmark answer: in none of the 16 planted scenario×δ cells did cross-attention beat the
best simpler model. Additive signals were solved by linear concat (BA 1.0); the
pairing-only regime S5 favoured gated fusion (1.0) and the concat MLP/token-concat
(0.9333) over cross-attention (0.9667). The fusion family does detect pairing-only signal
(it does not collapse to chance), it is simply not the best detector. These are synthetic
labels and carry no biological claim.

What is missing: the real primary contrast, chr21-exclusion arm, seed stability,
faithfulness interventions, cell-state spectrum, and routing/attention readouts. All are
blocked behind the ladder, not failed. Attention readouts are reported as
`NOT_SHOWN_USED`, never as evidence.

Requested next step: unblock and run the ladder at cap 1000, seed 22, so the fixed
primary contrast and the chr21-excluded sensitivity can be measured and reported. Until
then, no scientific claim about cross-attention on DS is warranted.

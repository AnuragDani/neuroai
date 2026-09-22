Subject: P22 update: ATAC representation sensitivity, simple controls, and the missing cell-state question

Hi Professor Fang,

This is an unsent draft for your review. It reports only internal work; nothing
here has been sent, published, or shared.

Since the last update I ran the prespecified ATAC representation sensitivity, added
the simple linear controls that were missing, and completed a model-free cell-state
feasibility assessment.

- Representation sensitivity: the retained 256-region ATAC rule broke
  training-library prevalence ties lexicographically, which placed 163-219 of 256
  regions on chromosome 1 per fold. I changed only that tie-break to a fixed
  sha256 ordering (salt fixed before selection), measured the resulting 465-region
  union once, and reran the frozen comparison. The corrected null persists:
  cross-attention minus token-concat is -0.0200 with a 95% donor-bootstrap interval
  of [-0.0533, +0.0113], versus the historical-corrected +0.0067 [-0.025, +0.0350].
  Both cross zero. Five initialization seeds on the new representation show no seed
  with an advantage.
- Simple controls: RNA-only, ATAC-only and concatenated cell-level logistic
  regressions now exist on both representations. RNA-only and concatenated logistic
  regression (about 0.62) outperform the neural token-concat reference (about 0.53),
  while ATAC-only underperforms (about 0.41). This is a linear-versus-neural
  estimator observation, not a cross-attention result.
- Cell-state feasibility: I built donor-by-cell-type support tables, measured ATAC
  panel coverage, and a deterministic donor-aware stratified sampling proposal. The
  important finding is a coverage gap: all 13 prespecified excitatory maturation
  program genes are on the RNA axis, but only 1 of 13 (TLE4) has any overlapping
  measured ATAC region. The prevalence-selected panels are not a targeted
  regulatory panel, so the within-lineage program question cannot be answered from
  the current measurements.

The biological objective still missing from the classifier work is that within-
excitatory-lineage maturation/program question. The classifier comparison answers a
donor disease-classification question; it does not test a regulatory program. I have
recorded a prespecified future estimand and falsification criterion, but testing it
needs a locus-targeted region set or the author peak-by-cell matrix, which is outside
this assignment.

Two limits remain unchanged: external paired evaluation is still blocked (access,
transport and no established common measurement space), and the Lattke paper is this
same cohort, so it is annotation support rather than independent validation. The
separate completed RNA replication remains inconclusive. I am not asking to relax any
access control.

Please start with `one_pager.md`. The canonical notebook now exposes the tie-break
sensitivity, the linear controls and the cell-state feasibility, and a safe-mode
executed copy is included.

Best,
Anurag

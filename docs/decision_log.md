# Decision log

## 2026-07-27 — Synthetic-only implementation freeze

- **Decision:** Complete C01–C13 under blocked approval; stop for Professor Fang.
- **Owner:** researcher recorded; approver is Professor Fang.
- **Allowed now:** synthetic arrays, reusable package code, tests, schemas,
  configs, reports, methods documentation, read-only legacy inspection.
- **Forbidden now:** real-matrix download or inspection, condition-specific
  training or target selection, biological mechanism claims from routing
  weights alone, cell-level splits when donor IDs exist, fitting transforms on
  held-out data, tuning on test, changing legacy experiment outputs.
- **Evidence:** plan steps C01–C13 complete; `make plan-status` next action
  `awaiting_professor_approval`.
- **Label:** verified for the blocked state; proposed for any post-approval work.

## Pending — Professor Fang approval

- **Decision needed:** approve or reject condition-specific dataset work
  described in the post-approval plan.
- **Required before training on real data:**
  1. Dated approval record (direction, dataset, target, estimand, split, metric,
     margin, benchmarks, stop rules)
  2. File-level metadata preflight (`p22` preflight reporter)
  3. Frozen primary target and evaluation protocol
- **Status:** open
- **Label:** unknown until recorded

## Historical — Tasic proxy-view architecture proof

- **Decision:** Preserve outputs as legacy evidence; do not treat as
  independent-modality or condition-specific validation.
- **Record:** `legacy/tasic_proxy_view/`
- **Label:** verified boundary; experimental result for the recorded numbers

## 2026-09-05 — Continue reusable neural-network development locally

- **Authorization:** user explicitly approved continuing development in the current
  task. This is not recorded as a dated approval from Professor Fang; the existing
  professor-specific record and condition-specific restrictions remain unchanged.
- **Decision:** implement donor-balanced binary training and donor-level checkpoint
  selection as optional arguments on the existing training loop. Preserve legacy
  behavior when donor IDs are absent; do not build a second optimizer loop.
- **Architecture:** RNA-query/ATAC-key-value cross-attention over four learned
  within-cell latent tokens per view, using installed PyTorch. Retain gating as a
  separate baseline. Use identical token encoders/head dimensions for token concat;
  report the extra attention parameters rather than claiming parameter equality.
- **Scope:** an explicitly synthetic command proves software integration and local
  resource use. It does not accept a real-data mode. Full scientific protocol,
  accepted counts/normalization, final refits, and external evaluation remain open.
- **Evidence:** [training guide](PAIRED_MULTIOME_TRAINING.md), 150 synthetic model
  fits, 25 donor-held-out folds, 25.883 seconds and 0.4351 GB process peak RSS on CPU.
- **Consequence:** no GPU/cloud provisioning justified by this workload. These
  small-feature measurements do not estimate full-matrix loading or exact recounting.

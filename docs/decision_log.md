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

## 2026-09-08 — User-reported real-data approval attestation

- **Record:** [scoped attestation](../plan/real_data_attestation_2026-09-08.json).
  User answered yes to the question about Professor Fang approval and asked to
  complete the existing plan. This records the user's report, not independent
  verification or an invented professor approval date.
- **Execution:** use the existing per-run approval-attestation mechanism for the
  public-data study. Preserve historical `plan/approvals.json`. Controlled access,
  paid infrastructure, unbounded fragment recounts and scientific-gate bypasses
  remain outside this authorization.
- **Statistics:** retain the frozen RNA comparison and headline rules, but remove
  the review's unsupported 2.5% arbitrary-dependence family-wise guarantee. Four
  nominal 0.025 events can have a three-or-more union probability of 0.0333;
  the descriptive rule is not a calibrated strong family-wise test.

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

## 2026-09-08 — Retained release, final artifacts and stopping boundaries

- **Authorization:** user requested finishing the plan with regular commits. Continue
  code and public-file diagnostics; do not invent a dated Professor Fang approval.
- **Retained source:** pinned author downstream filtered table exactly matches all
  37 final H5AD libraries and 30 donors/conditions. GEO flags alone are not the
  retained-cohort contract. Apply the exact retained-barcode mask before sampling.
- **Final fitting:** reuse the existing optimizer update, freeze each family's
  epochs to ceiling of median internal best epochs, then refit on all development
  donors. Store state dictionaries and numeric scaler parameters with hashes.
- **Evaluation:** exact feature order and disjoint cell/donor IDs required. An
  exclusive durable one-shot lock is acquired before predictions and retained on
  failure. Synthetic scoring does not prove specimen independence or real benefit.
- **Evidence:** [audit](PAIRED_MULTIOME_AUDIT.md), [training](PAIRED_MULTIOME_TRAINING.md),
  150 synthetic internal fits plus six final refits, reload and scoring; 27.286 seconds
  and 0.4466 GB process peak RSS. Different-model review found no required defects
  after the audit command's documented byte budget was corrected.
- **Verification:** 576 full-suite tests passed, 19 pre-existing warnings; lint and
  formatting passed. All 26 local links in the changed plan/evidence documents resolve.
- **Unfinished research:** accepted common-region ATAC counts, external release/QC
  and specimen evidence, real protocol/normalization and biological controls, real
  execution and the separate original RNA replication. These stay unchecked in
  [the plan](../tasks/todo.md); no fabricated successful outcome or completed-plan claim.

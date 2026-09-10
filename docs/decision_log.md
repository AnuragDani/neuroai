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

## 2026-09-08 — Real external RNA replication completed locally

- **Result:** all four prespecified summary-effect comparisons and the headline
  are inconclusive. Each comparison has nine DS and eight control discovery
  donors, 1,000 successful donor bootstraps and 1,000 whole-vector permutations.
  No cutoffs, gene filters or endpoints changed after seeing these results.
- **Verification:** three zero-error real notebook executions gave exactly equal
  RNA result rows. Final full suite: 608 passed, 19 existing warnings; lint/format
  passed. The final report distinguishes verified processed summaries from
  untested external raw matrices; G8 remains inconclusive.
- **Evidence:** [results, commands and completion ledger](EXTERNAL_RNA_REPLICATION_RESULTS_2026-09-08.md).
  User-reported approval is the scoped per-run attestation, not independent proof
  or a new dated professor approval record.
- **Remaining:** fresh Colab execution needs sign-in and upload approval. The
  paired extension still requires accepted ATAC counts, NeMO access/QC, a frozen
  real protocol, and actual internal/external neural comparisons. These gates
  remain open; the full plan is not declared complete.

## 2026-09-09 — Approval confirmed; Colab runs finished, archival check open

- **Authorization:** user answered “Yes dont ask asgain” to the explicit question
  whether Professor Fang approved this real-data analysis. Save that confirmation
  in the scoped attestation and do not re-request it for the same study. Notebook
  upload and free CPU execution were separately authorized. No dated independent
  approval evidence, paid compute, broader data access or outreach was inferred.
- **Execution:** native Colab Python 3.13 completed with its truthful G0
  inconclusive. Isolated Python 3.11 on the same VM then completed the unchanged
  23-cell canonical notebook with runtime-side zero-error/source checks. Retain
  startup failures and the isolated-kernel remedy; do not relabel the subprocess
  as the native Colab kernel.
- **Evidence:** native notebook downloaded and saved locally; final 40-file archive
  generated on the VM. Chrome retrieval failed repeatedly before that final
  archive could be copied and independently compared locally. Exact archive hash,
  command, recovery steps and limits are in the [results checkpoint](EXTERNAL_RNA_REPLICATION_RESULTS_2026-09-08.md).
- **Status:** original RNA task 5 stays partial. Earlier sign-in/upload statements
  are historical, not current blockers. No scientific code or paired M1–M8 gate
  changed, and no completed-plan or positive replication claim is made.

## 2026-09-09 — Original RNA plan completed with archived Colab evidence

- **Recovery:** downloaded the saved notebook through Google Drive's normal UI;
  its embedded archive exactly matches the previously recorded ZIP size/SHA.
  No rerun, permission expansion or additional local upload was needed.
- **Verification:** all 39 listed file hashes pass; safe extraction retained 40
  files including the inventory. The Python 3.11 notebook has the exact original
  23 cell sources, all code executed and zero errors. Both Colab runs match all
  checked RNA/cohort fields against local results exactly (maximum difference 0).
- **Differences retained:** native Python 3.13 G0 remains inconclusive; isolated
  Python 3.11 G0 passes. Startup failures, actual environment/commands, resource
  differences and the truthful subprocess flag are archived, not rewritten.
- **Completion:** original RNA Tasks 1–5 complete; four comparisons, headline and
  G8 stay inconclusive. [Final evidence](EXTERNAL_RNA_REPLICATION_RESULTS_2026-09-08.md).
  The preceding pending checkpoint is superseded. Paired M1–M8 requirements remain
  open; RNA reproducibility is not accepted paired input or neural validation.

# Paired DS multiome development plan

Updated: 2026-09-10 (PDT). Review corrections; planning revision only.
No new experiment authorized
or executed by this revision. Status: retained-cell ingestion, donor-aware networks, final
saved models/scalers and one-shot scoring implemented. 150 synthetic internal fits
plus six final refits verified. Real-data scientific gates remain pending.

## Next implementation: usable experiment paths

The immediate deliverable is a small command-line workflow with readable result
files, not another architecture, dashboard, or autonomous orchestrator. Extend
this same P22 plan; preserve all existing M1–M8 checkboxes below and in `todo.md`.

Two tracks can progress independently after this plan is approved:

| Track | What the user gets | What it can establish |
|---|---|---|
| Local RNA follow-up, F4–F5 | One command producing donor-influence table, plot, and summary | Which donors drive changes and whether influence is concentrated or diffuse; not a new replication verdict |
| Paired inputs, F1–F3 | Bounded archive probe plus evidence-linked readiness report | What can be inspected within budget, which gates remain unmet, and the exact next input needed |
| Real paired training, M5–M8 | Dry-run preflight; real fits deferred pending accepted development ATAC inputs, followed by separately gated external scoring | Conditional follow-on work, not a promised result of F1–F3 inspection |

**Recommended first scientific output:** the RNA donor-influence diagnostic. The
local H5AD and frozen external workbook are present under `data/real/`; verify
their hashes before use. This new, explicitly post-hoc exploratory analysis does
not wait for NeMO and does not replace the completed RNA study. Do not add another
binary DS classifier to work around the unresolved paired-data question.
The completed donor bootstrap already measures aggregate uncertainty. The new
question is donor-specific concentration of influence, separating same-support
correlation changes from changing gene support. It does not resolve statistical
power versus absent reproducible effects. See F4's frozen comparison contract.

**Recommended paired-input action:** one metadata-only probe of the NeMO Open
bag's `VuongWeber_2025_DSdevctx_atac_counts_20260128.mex.tar.gz`, then one evidence
decision. A gzip prefix can be incomplete or matrix-first. Do not assume random
tar offsets, successful metadata retrieval, or final QC from a file listing.

### Dependency order and checkpoints

```text
Plan approval + isolated workspace
├─ F4 freeze RNA diagnostic → F5 implement/run diagnostic → RNA checkpoint
└─ F1 recover reviewed fix → F2 bounded probe → F3 input decision → input checkpoint
                                                   ├─ blocked: exact missing input + stop
                                                   └─ M4 development inputs accepted* → M5 → M6a/b/c → M7 → M8
```

*Development common measured ATAC counts are a binding unresolved requirement;
F1–F3 can report this gap but do not produce those counts. The inspected raw
libraries do not establish a usable common space. This is not a cohort-wide
absence claim: two published processed objects remain uninspected, as recorded in
[the source evidence](../docs/PAIRED_MULTIOME_REMAINING_EVIDENCE_2026-09-08.md).
Possible next actions are separately bounded inspection of a documented published
common-count object, acquisition of a supplied compatible object, or an approved,
measured recount. None is automatically authorized by this planning revision.

Detailed acceptance criteria, verification, dependencies and file scope are in
[todo.md](todo.md), tasks F1–F5 and M6a–M6c. The diagram does not authorize fitting
while a required gate is unresolved. An internal-only pilot may proceed only
under a separately reviewed development-only protocol with all development QC,
pairing, feature, normalization and donor-split requirements satisfied. It cannot
close the original combined-cohort Checkpoint B or M8 while NeMO remains pending.
Peak-to-gene aggregation is not implemented and remains deferred, not an implicit
M6 input producer. If proposed later, it needs its own task and reviewed annotation,
coverage/missingness, count-unit and approximation contract. Shared gene names
alone do not make different ATAC measurements comparable; `EXPLORATORY_ONLY` never
closes confirmatory M4 or M8. Until a representation is accepted, the pilot is deferred.

### Intended commands and outputs

The following interfaces are **proposals to implement**, not commands available
today. Existing `scripts/audit_multiome.py` stays an offline verifier, and
`scripts/train_multiome.py` stays synthetic-only.

- `scripts/probe_multiome_release.py --manifest <pinned-release> --output-dir <new-dir>`:
  writes `probe.json` with inspected members, source identity, byte use and a stop
  reason. No matrix loading or training.
- `scripts/diagnose_rna_replication.py --config <frozen-diagnostic> --output-dir <new-dir>`:
  writes `donor_influence.csv`, `donor_influence.png`, `SUMMARY.md`, and run hashes.
- `scripts/run_real_multiome.py --config <frozen-real-protocol> --stage internal-pilot --dry-run`:
  writes or displays the readiness decision, planned resources, and exact missing
  inputs. Dry-run is the default and performs no fit or network access.
- The same real entrypoint with explicit `--execute` runs only the selected,
  accepted stage. External scoring remains a separate locked stage using the
  existing final-artifact/scoring machinery; no automatic stage escalation.

Every result should answer: what ran, what changed, what remains blocked, and
which single action can change the decision. No repeated unchanged API/tree
refreshes, automatic new datasets, or silently enlarged budgets.

### Boundaries and resources

- Preserve completed RNA results, thresholds, G8, approvals, notebooks and source
  hashes. Diagnostic output must use a new directory and the label
  `POST_HOC_EXPLORATORY`; it cannot turn the primary inconclusive result positive.
- Existing paired integrity fix is in isolated commit `3b677d5`, not this checkout.
  F1 names the recovery patch, bundle and application checks. The isolated checkout
  still existed on 2026-09-10; do not depend on temporary storage alone. Keep the
  ignored recovery package out of cleanup until F1's code/test slice is committed
  durably. Do not merge its entire branch or overwrite this plan with its old docs.
- The previous GNHF run exceeded its cap: 872,648 reported worker tokens. Do not
  resume it. GNHF repair is a separate tooling task, not a prerequisite for P22:
  use directly supervised, small implementation slices. Do not promise a strict
  token ceiling from the current end-of-turn accounting or substitute a wall
  clock limit for a token limit.
- Probe ceiling: 1 MiB total response-body bytes, 5 MiB total decoded content,
  at most one HEAD and one range GET, 30-second network timeout. Stop on a missing
  or mismatched range response, matrix payload, invalid/truncated metadata or cap.
  No larger retry without a separately reviewed budget. Compression and any
  archive-extension headers count toward decoded limits.
- RNA diagnostic: no new downloads; aggregate existing raw RNA once per unique
  population and reuse compact donor aggregates. Initially at most four comparison
  sets times their existing eligible donors; no nested 1,000-resample analysis
  per omission. CPU only, proposed 30-minute job ceiling and 6 GiB memory budget;
  preflight and record resources, refuse or stop rather than silently scale up.
- No full fragments, recount, paid compute, author outreach, controlled access,
  push or merge. No new GPU purchase. Real-training budgets must be measured on
  accepted inputs before expansion; synthetic timings are not real-data estimates.
- One verified implementation slice per local commit. Preserve unrelated dirty
  files; keep raw data/generated outputs ignored and commit concise evidence.

### Decision rules and fallback

Archive metadata can resolve availability or barcode/feature facts, but not
author QC meaning. F3 must identify the evidence separately for each gate. If
the probe cannot reach metadata within budget, report `INCONCLUSIVE` rather than
claiming no suitable data exist. If measured spaces demonstrably mismatch, retain
`NEEDS_RECOUNT`; never manufacture measurements through zero-filling or overlap.

When paired inputs remain blocked, finish the RNA diagnostic and present one
specific follow-up request: the exact QC/count artifact or a measured, bounded
processed-object inspection/recount proposal. Do not start that larger work.
If the RNA diagnostic also remains inconclusive, that is a valid output: report
which influence/support question remains unanswered, without tuning exclusions.

The 2026-09-10 user request authorizes these plan corrections, not experiment
execution. F4's frozen configuration requires review before F5 runs. Any later
development-only pilot needs its own accepted scope and inputs; it is not scheduled
as an immediately executable fallback. The completed RNA study's recorded
professor approval is unchanged. This revision executes none of the pending
implementation/experiment tasks.

### Review disposition

Accepted: explicit development-input dependency, recovery instructions, a focused
donor-concentration question, fixed numeric tolerance, same-support comparisons,
shared-donor disclosure, and fresh resource estimates before larger work.

Not adopted: compulsory bootstrap-SD scaling (only intervals, not SDs, were saved),
or an extra top-100 diagnostic. Top-set changes alone do not show that reselection
dominates agreement. A chromosome-21-only arm is optional future dosage sanity
checking, not a power test or replacement for F4–F5: matching positive signs do
not imply matching ranks or adequate sensitivity to weaker non-chromosome-21
effects. Existing external chromosome-21 sets have 91–101 genes, below the frozen
500-shared-gene floor; such an arm requires a separate contract, not weakened
primary gates. No new control arm is added here.

## Scope

Extend P22 toward real RNA+ATAC comparisons using GSE305146 for development and Vuong/NeMO as the reserved external candidate. The scientific contract and source evidence live in [the dataset proposal](../docs/PAIRED_DS_MULTIOME_DATASET_OPTIONS.md). This plan does not replace [external RNA replication](../docs/EXTERNAL_RNA_REPLICATION_PLAN.md) or change historical results or legacy plan-guard state.

The ingestion/compatibility report is available through [the audit guide](../docs/PAIRED_MULTIOME_AUDIT.md).
The [training guide](../docs/PAIRED_MULTIOME_TRAINING.md) records donor-aware selection,
genuine cross-attention, matched token concatenation, paired uncertainty, and a completed
synthetic benchmark, final refit and reload/scoring. The author's filtered library
table now exactly matches final-release membership. Real-data training still depends on an accepted cohort, valid ATAC
representation and frozen scientific protocol. The user has now reported professor
approval through the [scoped per-run attestation](../plan/real_data_attestation_2026-09-08.json);
the actual professor approval date remains unknown and historical policy is unchanged.

## Decisions

- NeMO's 3,731 RNA `Unk` rows explain the count difference exactly. Record this candidate reconciliation separately from unresolved upstream QC; do not apply it as an accepted exclusion without source evidence.
- Map all GSE305146 libraries to biological donors and retained cells. Check specimen provenance across studies; different donor names do not establish independence.
- Normalize documented obstetric GW to approximate PCW with an explicit minus-two conversion. Preserve original values and unresolved units.
- Require common measured ATAC regions/count semantics for confirmatory evaluation. Peak-derived gene scores can support an exploratory pilot; exact recounting and its resource budget remain possible.
- Primary proposed question: external donor balanced-accuracy improvement of cross-attention over concatenation. Keep chromosome-21 dosage and simpler controls; record negative/inconclusive outcomes without changing the endpoint.
- Reuse donor splits, aggregation, resource reporting, preprocessing fingerprints, baseline/gated models, and training code. Add donor-level checkpoint scoring and a real-data adapter without removing synthetic-only safeguards from the existing synthetic runner.
- Implement genuine cross-attention separately from gating, with multiple key/value tokens, explicit token construction, and matched concatenation controls.

## Ordered tasks

All task state, acceptance criteria, likely files, and verification are in [todo.md](todo.md).

1. M1 — Source release, QC, and specimen contract.
2. M2 — Developmental-age normalization.
3. M3 — Bounded paired sparse ingestion.
4. M4 — Shared ATAC feature compatibility.
5. M5 — Freeze donor-level research protocol.
6. M6 — Donor-aware baseline training adapter.
7. M7 — Explicit cross-attention comparison.
8. M8 — Locked external evaluation and report.

Checkpoints follow M1–M2, M3–M4, M5–M6, and M7–M8. M3 diagnostics can proceed with unresolved release questions, but confirmatory training/evaluation cannot bypass their relevant gates. No external predictive result may choose preprocessing, thresholds, or architecture.

## Remaining evidence requirements

The dataset proposal addresses all six review findings, but the empirical questions remain open: release/QC reconciliation, specimen provenance, age conventions, compatible ATAC counts, resource measurements, and whether an attention model adds value with 30 development donors and at most 26 external donors. Architectural hyperparameters and approximation acceptance limits must be written into the protocol before fitting/evaluation; they are not implicit defaults.

The [2026-09-08 source check](../docs/PAIRED_MULTIOME_REMAINING_EVIDENCE_2026-09-08.md)
now documents UCLA/NIH procurement versus HDBR and the exact annotation count match.
The executable audit reports these findings without certifying specimen identity,
reproduced QC, or compatible ATAC counts. Original RNA replication is implemented
and [executed locally](../docs/EXTERNAL_RNA_REPLICATION_RESULTS_2026-09-08.md): all
four comparisons are inconclusive, with exactly matching results in three runs.
Original RNA Tasks 1–5 are complete: fresh free-CPU Colab archive retrieved, hashes
verified and results exactly matched locally (2026-09-09). Approval remains recorded.
RNA results cannot satisfy paired-data gates.

## Completion evidence

A completed extension has versioned input/QC/feature/protocol manifests, passing focused integrity tests, donor-disjoint internal results, clearly labeled model families, and an external report with uncertainty and limitations. A failed compatibility or independent-evaluation check is reported explicitly; it is not converted into a successful multimodal claim.

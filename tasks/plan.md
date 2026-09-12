# Paired DS multiome development plan

Updated: 2026-09-11 (PDT). Bounded next-cycle contract; planning revision only.
This revision authorizes no implementation, download, or experiment. Status:
retained-cell ingestion, donor-aware networks, final
saved models/scalers and one-shot scoring implemented. 150 synthetic internal fits
plus six final refits verified. Real-data scientific gates remain pending.

## Next implementation: usable experiment paths

The immediate deliverable is a small command-line workflow with readable result
files, not another architecture, dashboard, or autonomous orchestrator. Extend
this same P22 plan; preserve all existing M1–M8 checkboxes below and in `todo.md`.

Current track status:

| Track | What the user gets | What it can establish |
|---|---|---|
| Local RNA follow-up, F4–F5: complete in isolated branch | Reviewed donor-influence table, plot, and summary | 68 valid omissions; original inconclusive conclusion unchanged; no repeat scheduled |
| Paired inputs, F1–F3 | Bounded archive probe plus evidence-linked readiness report | What can be inspected within budget, which gates remain unmet, and the exact next input needed |
| Real paired training, M5–M8 | Dry-run preflight; real fits deferred pending accepted development ATAC inputs, followed by separately gated external scoring | Conditional follow-on work, not a promised result of F1–F3 inspection |

**Completed baseline:** F4–F5 ran once on real inputs: 68 valid omissions,
45.94 seconds, 4.14 GiB sampled peak RSS, and 628 passing tests. Code/results
are committed in isolated head `46d7523`, not merged into this checkout.
[Durable delivery and recovery instructions](../reports/generated/rna_donor_influence_20260910_supervised/REVIEW.md)
include the bundle and reviewed checklist. Preserve that work. Do not repeat the
diagnostic, remove an influential donor, or add a classifier to change the RNA verdict.

### Next-cycle objective and reasoning

**Long-term question:** does cross-attention improve donor-level prediction over
matched concatenation using valid paired RNA+ATAC measurements? This cycle does
not answer that model-performance question. It establishes which input requirements
remain unsatisfied and the single next action that can change the decision.

**Deliverable:** one reviewed coordinate-guard commit, one tested bounded probe,
and one evidence-linked input decision. `INCONCLUSIVE` with exact missing inputs
is a valid cycle outcome; a software failure is not a completed scientific decision.

| Step | Why it is necessary | Completion evidence |
|---|---|---|
| F1: recover the existing coordinate guard | Conflicting peak IDs and coordinates can invalidate measurement comparisons before a model sees them | The regression fails on the base, passes with the exact reviewed patch, and existing readers still pass |
| F2a/F2b: implement, then use one bounded probe | Archive member order and reachable barcode/feature metadata are unknown; a full count download is unnecessary for this narrow question | Adversarial fixtures pass; one `probe.json` records complete-member facts, byte ledger and stop reason, including an explicit preflight refusal if needed |
| F3: join evidence into one decision | Archive access, matching cell totals, compatible measurements and accepted QC are different claims | `input_decision.json` and `INPUT_DECISION.md` state each gate separately and name one next action |

F1–F3 **do not create common measured ATAC counts**. Development data are the
binding concern for an internal pilot. NeMO metadata cannot solve that concern.
The inspected B17C2L/B10C1Q peak lists mismatch, but the two published processed
objects remain uninspected. Do not claim that no usable object exists.

### Frozen scope of this cycle

- Work only on F1, F2a/F2b and F3. M5, M6a–M6c, M7 and M8 remain separate later
  work. No RNA reruns, new datasets, new model families, peak-to-gene approximation,
  count projection, full fragments, recount, paid compute, outreach, push or merge.
- Start implementation in an isolated checkout containing the accepted RNA code
  from `46d7523`, plus these two current plan files. Record both revisions and
  dirty/source/result fingerprints before editing. Do not import old GNHF plan
  documents or automatically commit unrelated files. Never rerun GNHF.
- Proposed edits: F1 two existing files; F2a three files; F2b one evidence note
  plus generated artifacts; F3 at most five files. Use the existing Python environment and installed
  libraries. No dependency, framework, dashboard or general download manager.
- One candidate source only: NeMO's
  `VuongWeber_2025_DSdevctx_atac_counts_20260128.mex.tar.gz`, declared size
  1,540,753,269 bytes and declared MD5 `796c8b3aa587b257af0a46615a437dba`.
  These are publisher declarations, not a locally verified full-file checksum.
- Proposed `configs/nemo_atac_probe.json` pins the exact HTTPS payload URL,
  source-evidence path/hash, filename, declared size/checksum and numeric limits.
  Recover the exact URL from local first-party response evidence before launch;
  never infer it from a filename or directory. If unavailable, record
  `SOURCE_IDENTITY_UNRESOLVED` without a live request. The existing source review
  saved summaries/hashes rather than all raw responses; no fresh bag/API fetch is
  silently added to this cycle. A required small source-resolution request becomes
  the single next proposal instead.
- F2b uses at most one HEAD and one prefix range GET, with no retries or redirects.
  Aggregate application-read response bodies must not exceed 1,048,576 bytes.
  Aggregate decoded content, including archive headers and nested layers, must
  not exceed 5,242,880 bytes. A single 30-second monotonic deadline covers network
  work, including DNS/connect/TLS, HEAD and GET; it is not a new timeout per read.
  Tests must cover stalled/slow-drip responses and deadline enforcement. These
  body limits do not claim to meter TLS/TCP overhead or bytes already buffered by
  the OS. Stop body reads immediately when a response fails validation.
- Require HTTP 206 and the exact requested Content-Range/declared total before
  reading the prefix. Disable HTTP content decoding. Stop at matrix content,
  unknown/nonregular/unsafe members, incomplete metadata, cap or timeout. Do not
  extract to disk, follow archive instructions, skip through matrix payloads, or
  use a full-download fallback. Prefix chunks can already contain matrix bytes;
  do not parse or continue past the first matrix member.
- F3 runs the existing local audit once, with its existing explicit caps:
  1,700,000,000 input bytes, 268,435,456 expanded bytes, 10,000,000 nonzeros and
  256 retained cells per donor in the existing single-library pilot. This is
  neither a new cohort-wide ingestion nor a donor-validation experiment. No
  network is permitted in F3. Byte limits are not process-RAM guarantees.

### Outputs, decision rules and terminal condition

All proposed interfaces below must refuse existing output directories. Keep
generated data ignored; commit concise code, tests and evidence descriptions.

`probe.json` must contain schema version, exact command/config/code hashes, UTC
time, source declaration versus observed headers, requests, cumulative body and
decoded bytes, elapsed time, inspected member names/completeness, prefix SHA256,
and a specific stop reason. `request_attempted=false` distinguishes preflight
refusal from a live probe: unresolved URL, prefix hash and observed headers are
null; requests and inspected members are empty; body and decoded byte counters
are zero. F3 must reject a no-request record with contradictory observations.
Complete members may support local facts; partial
coverage never proves full archive membership, final QC or dataset absence.

`input_decision.json` must keep separate `development`, `external`, and
`cross_cohort` evidence. Each gate records `PASS`, `UNRESOLVED`, or `FAIL`, its
source path/hash, inspected scope, reason and missing artifact. Required fields
cover release/retained barcodes, donor pairing, QC/count-stage meaning, age/class
support, specimen provenance, genome/coordinate convention, count units, exact
measured regions and feature-selection provenance. Missing evidence is not PASS.
Retain M4's existing `PASS`/`INCONCLUSIVE`/`NEEDS_RECOUNT` vocabulary separately.

Both `training_allowed` and `model_training_performed` remain false in F3: this
cycle has no accepted real M5 protocol. `INPUT_DECISION.md` gives inspected scope,
what changed, unresolved requirements, and exactly one prioritized next action.
If development counts remain missing, prefer a separately budgeted inspection
proposal for `GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz`, listed as
7.6G in the existing evidence. That name does not establish assay contents,
compatible counts, training-only feature provenance, or cross-cohort readiness.
Record current free disk in GiB and identify unknown compressed/decoded/working
sizes before requesting a larger inspection. Do not download it in this cycle.
If an earlier missing source identity prevents the probe, prioritize that smaller
source-resolution proposal and retain the development-count blocker explicitly.

**Stop after F3's reviewed decision.** No second live probe, source substitution,
expanded budget, processed-object download or real fit follows automatically.
Complete means all implementation criteria/tests pass, evidence is preserved,
and a reviewer accepts the decision and next action. A transport or partial-prefix
stop can complete the evidence question; broken code must be fixed offline first.

**Recommended paired-input action:** one metadata-only probe of the NeMO Open
bag's `VuongWeber_2025_DSdevctx_atac_counts_20260128.mex.tar.gz`, then one evidence
decision. A gzip prefix can be incomplete or matrix-first. Do not assume random
tar offsets, successful metadata retrieval, or final QC from a file listing.

### Dependency order and checkpoints

```text
Completed: F4/F5 RNA diagnostic (isolated 46d7523); preserve, do not repeat
Next-cycle approval + isolated workspace
└─ F1 recover fix → F2a offline probe/tests → F2b at most one probe → F3 decision → STOP
Later, separately reviewed: accepted development inputs* → M5 → M6a/b/c → M7
External evaluation additionally requires accepted external inputs + frozen models → M8
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

The paired interfaces below are **proposals**, not commands available today.
The RNA diagnostic already exists in isolated `a0049f2` and is not part of this
cycle. Existing `scripts/audit_multiome.py` stays an offline verifier, and
`scripts/train_multiome.py` stays synthetic-only.

- `scripts/probe_multiome_release.py --manifest configs/nemo_atac_probe.json --output-dir <new-dir>`:
  writes `probe.json` with inspected members, source identity, byte use and a stop
  reason. No matrix loading or training.
- `scripts/audit_multiome.py --manifest configs/paired_multiome_audit.json --probe-report <probe.json> --probe-manifest configs/nemo_atac_probe.json --output-dir <new-dir> --max-input-bytes 1700000000 --max-expanded-bytes 268435456 --max-nnz 10000000 --cell-cap 256`:
  retains current audit artifacts and adds `input_decision.json` and
  `INPUT_DECISION.md` within the explicit existing local caps.
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
- Probe ceiling: 1 MiB total application-read response-body bytes, 5 MiB total decoded
  content, at most one HEAD and one range GET, and one 30-second total network
  deadline as defined above. Stop on a missing
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

The RNA diagnostic is complete. When paired inputs remain blocked, present one
specific follow-up request: the exact QC/count artifact or a measured, bounded
processed-object inspection/recount proposal. Do not start that larger work.
If the RNA diagnostic also remains inconclusive, that is a valid output: report
which influence/support question remains unanswered, without tuning exclusions.

The 2026-09-11 user request authorizes these plan corrections, not experiment
execution. F4–F5 already passed review and execution in their isolated branch. Any later
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

# Paired DS multiome development plan

Updated: 2026-09-12 (PDT). F1–F3 implemented and the bounded audit completed;
final decision review is recorded in the audit guide. No further execution is
authorized by this completion record. Status: retained-cell ingestion, donor-aware networks, final
saved models/scalers and one-shot scoring implemented. 150 synthetic internal fits
plus six final refits verified. Real-data scientific gates remain pending.

## Bounded implementation: usable experiment paths

The immediate deliverable is a small command-line workflow with readable result
files, not another architecture, dashboard, or autonomous orchestrator. Extend
this same P22 plan; preserve all existing M1–M8 checkboxes below and in `todo.md`.

Current track status:

| Track | What the user gets | What it can establish |
|---|---|---|
| Local RNA follow-up, F4–F5: complete in isolated branch | Reviewed donor-influence table, plot, and summary | 68 valid omissions; original inconclusive conclusion unchanged; no repeat scheduled |
| Paired inputs, F1–F3: bounded cycle complete | Coordinate guard, resolved NeMO declaration, development-reader inventory and evidence-linked decision | Source identity resolved; development reader absent in checked environment; compatible counts/QC still unresolved |
| Real paired training, M5–M8 | Dry-run preflight; real fits deferred pending accepted development ATAC inputs, followed by separately gated external scoring | Conditional follow-on work, not a promised result of F1–F3 inspection |

**Completed baseline:** F4–F5 ran once on real inputs: 68 valid omissions,
45.94 seconds, 4.14 GiB sampled peak RSS, and 628 passing tests. Code/results
are committed in accepted head `46d7523`, the baseline of this isolated branch;
neither branch is merged into the original user checkout.
[Durable delivery and recovery instructions](../reports/generated/rna_donor_influence_20260910_supervised/REVIEW.md)
include the bundle and reviewed checklist. Preserve that work. Do not repeat the
diagnostic, remove an influential donor, or add a classifier to change the RNA verdict.

**Current cycle result:** implementation `3b007d7` completed the one offline audit:
1,582,118,205 input bytes, 57,855,276 expanded bytes, 256 selected retained cells,
and zero exact shared regions between the two inspected raw peak lists.
NeMO's 1,867-byte declaration resolved in one request. Both processed development
objects remain uninspected. `INCONCLUSIVE` is the input decision, not a new
biological finding. The next action is bounded reader enablement plus a tiny
sparse fixture, outside this cycle's no-install scope. See the
[decision and verification record](../docs/PAIRED_MULTIOME_AUDIT.md#f3-decision-and-closure)
and [durable delivery](../reports/generated/input_feasibility_20260912/REVIEW.md).

### Next-cycle objective and reasoning

**Long-term question:** does cross-attention improve donor-level prediction over
matched concatenation using valid paired RNA+ATAC measurements? This cycle does
not answer that model-performance question. It establishes which input requirements
remain unsatisfied and the single next action that can change the decision.

**Deliverable:** one reviewed coordinate-guard commit, one tested source resolver,
one development-object feasibility record, and one evidence-linked input decision.
`INCONCLUSIVE` with exact missing inputs
is a valid cycle outcome; a software failure is not a completed scientific decision.

| Step | Why it is necessary | Completion evidence |
|---|---|---|
| F1: recover the existing coordinate guard | Conflicting peak IDs and coordinates can invalidate measurement comparisons before a model sees them | The regression fails on the base, passes with the exact reviewed patch, and existing readers still pass |
| F2d: freeze development-object inspection feasibility | Development common measured counts are the binding input, while both published `.rda.gz` objects and required reader/runtime remain unverified | One offline capability/resource record names the selected object, missing reader/runtime facts, exact inspection questions and a bounded follow-up |
| F2s: resolve NeMO source identity | Exact payload URL is absent from preserved local evidence; building a payload probe before resolving it would likely create unused code | One capped read of the pinned 1,867-byte official bag produces a reviewed `source_identity.json`, or an explicit source-resolution failure; this external check cannot block F2d |
| F3: join evidence into one decision | Source access, reader feasibility, compatible measurements and accepted QC are different claims | `input_decision.json` and `INPUT_DECISION.md` state each gate separately and name one development-focused next action |

F1–F3 **do not create common measured ATAC counts**. Development data are the
binding concern for an internal pilot. NeMO metadata cannot solve that concern.
The inspected B17C2L/B10C1Q peak lists mismatch, but the two published processed
objects remain uninspected. Do not claim that no usable object exists.
An accepted development object can support a donor-held-out internal milestone;
the current M5 plan still requires freezing external donor balanced-accuracy
improvement as the primary contrast. Its real protocol remains pending. Internal
results are a separate milestone; they cannot satisfy or replace that endpoint.

### Frozen scope of this cycle

- Work only on F1, F2d, F2s and F3, in that order. F2d does not depend on NeMO
  access or F2s success. M5, M6a–M6c, M7 and M8 remain separate later
  work. No RNA reruns, new datasets, new model families, peak-to-gene approximation,
  count projection, payload-prefix probe, processed-object download, full fragments,
  recount, dependency installation, paid compute, outreach, push or merge.
- Start implementation in an isolated checkout containing the accepted RNA code
  from `46d7523`, plus these two current plan files. Record both revisions and
  dirty/source/result fingerprints before editing. Do not import old GNHF plan
  documents or automatically commit unrelated files. Never rerun GNHF.
- Proposed edits: F1 two existing files; F2d one evidence note; F2s one small
  stdlib script, one test and that shared evidence note; F3 at most five files.
  Use the existing Python environment and installed libraries. No dependency,
  framework, dashboard or general download manager.
- One external payload candidate only: NeMO's
  `VuongWeber_2025_DSdevctx_atac_counts_20260128.mex.tar.gz`, declared size
  1,540,753,269 bytes and declared MD5 `796c8b3aa587b257af0a46615a437dba`.
  These are publisher declarations, not a locally verified full-file checksum.
- F2s reads only the pinned official ATAC Open bag URL already recorded in local
  [recheck evidence](../reports/generated/paired_public_recheck_2026-09-09/verification.md):
  `https://data.nemoarchive.org/publication_release/Vuong_delaTorre_Human_snMultiome-2026-05-04/Analysis_bag_3_Vuong_delaTorre_Human_snMultiome_Analysis_ATAC_Open.tgz`.
  It permits one GET, no HEAD, retry or redirect, at most 65,536 body bytes,
  262,144 aggregate decoded bytes (including archive headers), and one 15-second
  monotonic network deadline covering DNS/connect/TLS and all reads. Require HTTP
  200, disable HTTP decoding, and compare the complete body with preserved evidence:
  1,867 bytes and SHA256
  `4698c4b80d1e1bde7588b9b0979beb113df2ca24aebf54afbbac606eaf064d45`.
  Any mismatch yields `SOURCE_EVIDENCE_CHANGED`; do not parse or make another
  request. On exact match, read `fetch.txt` and `manifest-md5.txt` locally without
  extracting files. Require one target row in each, joined on the same bag-relative
  payload path: URL/size from `fetch.txt`, MD5 from `manifest-md5.txt`. Match the
  target filename, 1,540,753,269 bytes and declared MD5 above. Reject ambiguous
  rows, unsafe paths and links; allow directory entries and regular bag metadata.
  Preserve the complete hash-matching bag in the new ignored output directory so
  the URL/declaration join can be verified offline. Never construct or follow the
  payload URL. Record bag-response `ETag` and `Last-Modified` when supplied; these
  do not bind the payload version. Test caps and the absolute deadline offline
  before the single live request; no retry for verification.
- F2d performs no network access. Record whether `R`, `Rscript`, `pyreadr`, or
  `rpy2` are available, current free disk in GiB, and unknown compressed,
  decompressed, in-memory and working-space requirements. Presence of a generic R
  reader is insufficient: later inspection must support the serialized object
  classes and sparse assays, including required Seurat/Signac dependencies if
  applicable. Reading only assay names can still deserialize the whole object.
  Select only
  `GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz` (publisher listing
  7.6G) for a later proposal. File name and size do not prove assay contents.
  Freeze later inspection questions: object/classes; assay names; raw-count
  layer/slot; sparse dimensions; feature identifiers/coordinates and genome build;
  count units; donor/cell metadata and retained-cell semantics; and whether
  `peaks_by_cluster` or another common measured ATAC matrix exists. Also ask which
  donors/labels contributed to peak discovery; shared columns alone do not prove
  training-only feature provenance. No dense materialization is acceptable.
- F3 runs the existing local audit once, with its existing explicit caps:
  1,700,000,000 input bytes, 268,435,456 expanded bytes, 10,000,000 nonzeros and
  256 retained cells per donor in the existing single-library pilot. This is
  neither a new cohort-wide ingestion nor a donor-validation experiment. No
  network is permitted in F3. Byte limits are not process-RAM guarantees.

Read-only planning inventory on 2026-09-12: neither `R` nor `Rscript` was found on
PATH; neither `pyreadr` nor `rpy2` was found in `.venv-p22`. Repository-volume free
space was 29,096,732 KiB (27.75 GiB), not the review's earlier 55 GiB. Host memory
was not established by this check. These observations do not prove that every
possible runtime is absent. F2d must refresh them before proposing a resource
budget; the publisher's rounded `7.6G` listing is not an exact byte count.

### Outputs, decision rules and terminal condition

All proposed interfaces below must refuse existing output directories. Keep
generated data ignored; commit concise code, tests and evidence descriptions.

`source_identity.json` must contain schema version, exact command/code and local
source-evidence hashes, UTC time, pinned bag URL, request ledger, supplied
`Content-Length`/`Content-Encoding`/`ETag`/`Last-Modified`, cumulative body and decoded
bytes, elapsed time, raw-bag path/hash, declared target and separately resolved
URL/size/MD5, matched member paths and one stop reason. Keep expected declarations
separate from observations: resolved fields remain null unless both manifest rows
validate. Preflight refusal records `request_attempted=false`, empty requests,
zero byte counters and null response fields; a failed request preserves measured
bytes and elapsed time. F3 rejects contradictions and verifies the saved bag/join
for a successful resolution. This record establishes
source identity only, not payload immutability, archive contents, QC or usability.

`development_object_feasibility.json` is a small manually assembled record of the
offline checks, not a new collector service. Include schema version, UTC time,
commands/results, source paths/hashes, runtime paths/versions, selected object,
free disk, host/available memory where measurable, and known/unknown compressed,
decoded, peak-RSS and working-disk quantities with units. Unknowns are null with
reasons, never zero. State whether reader support is proven, untested or absent,
the exact inspection questions, and the smallest next action. It cannot mark
counts, QC, coordinates or donor pairing as accepted. A later full-object proposal
requires numeric network/decoded/RSS/disk/time ceilings, a means to enforce them,
headroom and a stop rule; unknown full-object fit must remain unresolved.

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
If development counts remain missing, select the first unmet prerequisite for
inspecting the named development object. With absent or untested reader support,
propose a bounded reader-enablement and tiny sparse-object fixture check in an
isolated local/free-CPU environment. With a proven reader but unknown full-object
resource fit, propose only the smallest sizing check with explicit limits. Only
when both are supported may the next action be a resource-bounded object
inspection. A tiny fixture does not prove that the real object fits in memory.
Check existing approvals against the exact proposed action; identify only any
uncovered authorization. NeMO source resolution cannot displace this development
priority, even if its request fails.

**Stop after F3's reviewed decision.** No payload probe, second source request,
source substitution, dependency installation, expanded budget, processed-object
download or real fit follows automatically.
Complete means all implementation criteria/tests pass, evidence is preserved,
and a reviewer accepts the decision and next action. A bounded source-resolution
failure can complete that evidence question; broken code must be fixed offline first.

**Recommended paired-input action:** establish reader/resource feasibility for
the selected development object, then resolve external payload identity cheaply.
Do not reuse a gzip/tar prefix probe for `.rda.gz`:
its format and resource needs differ. NeMO payload inspection remains a later
external-input task, worth building only if source resolution succeeds and a
predeclared question can change an external-input decision. HTTP size or
Accept-Ranges headers cannot establish assay contents or actual Range behavior.

### Dependency order and checkpoints

```text
Completed: F4/F5 RNA diagnostic (isolated 46d7523); preserve, do not repeat
Completed under user approval in isolated workspace:
└─ F1 recovered fix → F2d offline feasibility → F2s one tiny source read → F3 decision → STOPPED
Later, separately reviewed: accepted development inputs* → M5 → M6a/b/c → M7
External evaluation additionally requires accepted external inputs + frozen models → M8
```

F2s failure is recorded in F3 and does not undo or stall the development proposal.

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

### Available bounded commands and deferred interfaces

The source resolver and decision-mode audit are implemented in this isolated
branch. Their one real execution is complete; these commands document the
interface, not permission to repeat it. The real-data runner remains a
**proposal**, not an available command. The RNA diagnostic already exists in
accepted `a0049f2` and is not part of this cycle.
Existing `scripts/audit_multiome.py` stays an offline verifier, and
`scripts/train_multiome.py` stays synthetic-only.

- `scripts/resolve_nemo_source.py --output-dir <new-dir>`: reads only the pinned
  1,867-byte official bag under the frozen limits and writes `source_identity.json`.
- `scripts/audit_multiome.py --manifest configs/paired_multiome_audit.json --source-identity <source_identity.json> --source-identity-sha256 <reviewed-source-hash> --development-feasibility <development_object_feasibility.json> --development-feasibility-sha256 <reviewed-development-hash> --output-dir <new-dir> --max-input-bytes 1700000000 --max-expanded-bytes 268435456 --max-nnz 10000000 --cell-cap 256`:
  retains current audit artifacts and adds `input_decision.json` and
  `INPUT_DECISION.md`. Both reviewed record hashes and all four exact caps are
  required in decision mode. Legacy audit callers retain their existing interface.
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
- The paired integrity fix from `3b677d5` was recovered exactly in isolated
  `cf8ed33`. F1 records the recovery patch, bundle and application checks.
  Do not depend on temporary storage alone. Keep the
  ignored recovery package out of cleanup until F1's code/test slice is committed
  durably. Do not merge its entire branch or overwrite this plan with its old docs.
- The previous GNHF run exceeded its cap: 872,648 reported worker tokens. Do not
  resume it. GNHF repair is a separate tooling task, not a prerequisite for P22:
  use directly supervised, small implementation slices. Do not promise a strict
  token ceiling from the current end-of-turn accounting or substitute a wall
  clock limit for a token limit.
- Current network ceiling: F2s's one bag GET, 65,536 application-read body bytes,
  262,144 decoded bytes and 15-second total network deadline. These body counters
  exclude TLS/TCP overhead and bytes buffered by the OS. The previous 1 MiB/5 MiB
  payload-prefix probe is deferred; its earlier budget grants no current request.
  A later payload probe needs its own fixed target and question, and must compare
  payload response validators across requests where available. Bag ETags cannot
  stand in for payload validators; even payload validators do not establish QC.
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

The source resolver establishes only a declared URL/size/checksum, and F2d
establishes inspection prerequisites. Neither inspects count-archive contents or
certifies author QC. F3 must identify the evidence separately for each gate. A
source failure or unresolved resource estimate yields a bounded `INCONCLUSIVE`
decision, never a dataset-absence claim. If measured spaces demonstrably mismatch, retain
`NEEDS_RECOUNT`; never manufacture measurements through zero-filling or overlap.

The RNA diagnostic is complete. When paired inputs remain blocked, present one
specific follow-up request: the exact QC/count artifact or a measured, bounded
processed-object inspection/recount proposal. Do not start that larger work.
If the RNA diagnostic also remains inconclusive, that is a valid output: report
which influence/support question remains unanswered, without tuning exclusions.

The initial 2026-09-12 request authorized plan corrections only; the subsequent
“Develop the plan” request authorized this bounded F1–F3 implementation.
It is now complete and stopped at its decision. F4–F5 already passed review and
execution in their isolated branch. Any later
development-only pilot needs its own accepted scope and inputs; it is not scheduled
as an immediately executable fallback. The completed RNA study's recorded
professor approval is unchanged. No pending M5–M8 real experiment was executed.

### Review disposition

September 12 second opinion: accepted source resolution before any payload-probe
build, development-reader/resource checks first, separate internal/external
milestones, and response-validator recording. Deferred F2a/F2b payload-probe
implementation entirely for this cycle. Rejected broad HEAD surveys as proof of
counts, switching to whichever target is reachable, and treating R serialization
as MEX/tar. Corrected the draft's `fetch.txt`/checksum-manifest join. M1–M8 and the
external primary contrast remain unchanged.

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

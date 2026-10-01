# Paired DS multiome implementation checklist

## Data-driven investigation continuation — Q0–Q12

Detailed acceptance criteria, verification commands, dependencies and likely files are defined per task in [the dated plan](nn/professor_direction_investigation_20260929/next_stage_20260930/PLAN.md#execution-amendment-detailed-tasks-and-verification). This is the canonical checklist for the new continuation. Existing checkboxes below retain their original scope. Earlier D0 metadata/count checks completed; Q1 adds a fresh reproducible replay and failure checks.

- [x] Q0: Pin source/runtime/input provenance; preserve dirty main; copy only owned plan/evidence into isolated worktree. — `DONE`. Evidence: [PREFLIGHT.md](nn/professor_direction_investigation_20260929/next_stage_20260930/PREFLIGHT.md); owned plan/prompt/three diagnostic JSONs copied with matching SHA-256; root plan/checklist appended without overwriting older sections.
- [x] Q1: Reproduce saved diagnostics and canonical verifier; verify tamper/order/overwrite refusals. — `DONE`. Evidence: [REPLAY.md](nn/professor_direction_investigation_20260929/next_stage_20260930/REPLAY.md); fresh root `reports/generated/nn_next_stage_q1_replay_20260930/` byte-identical to three golden JSONs; `verify_ladder.py` PASS/`B_NULL` without `--write`; 17 pytest PASS including new refusal tests.
- [x] Q2: Audit independent cell-state endpoint or record ENDPOINT_UNRESOLVED. — `DONE` (`ENDPOINT_UNRESOLVED`). Evidence: [ENDPOINTS.md](nn/professor_direction_investigation_20260929/next_stage_20260930/ENDPOINTS.md); [endpoint_inventory.json](nn/professor_direction_investigation_20260929/next_stage_20260930/endpoint_inventory.json); no independently measured maturation/state endpoint orthogonal to RNA inputs; age and RNA cluster labels rejected as cell-state truth.
- [x] Q3: Quantify all fold-specific ATAC panels; distinguish measured coverage from regulatory adequacy. — `DONE` (`REGULATORY_ADEQUACY_UNRESOLVED`; structural `STRUCTURAL_COVERAGE_PASS`). Evidence: [REGULATORY_COVERAGE.md](nn/professor_direction_investigation_20260929/next_stage_20260930/REGULATORY_COVERAGE.md); [regulatory_coverage.json](nn/professor_direction_investigation_20260929/next_stage_20260930/regulatory_coverage.json); all 25 training-only 256-region panels reported; gene overlap descriptive only; at most one alternate (existing gene-activity exact counts).
- [x] Checkpoint A: Source/replay/measurement contracts checked; unresolved endpoint cannot unlock a biological fit. — `DONE`. Evidence: Q1 replay PASS; Q2 `ENDPOINT_UNRESOLVED`; Q3 structural PASS / `REGULATORY_ADEQUACY_UNRESOLVED`; unresolved flags retained and cannot authorize biological cell-state fits.
- [x] Q4: Verify targeted sampling, donor/age/class support and declared adequacy; freeze eligibility before effect analysis. — `DONE` (`SUPPORT_REPAIR_PASS`; `ELIGIBILITY_FROZEN`). Evidence: [SAMPLING_FEASIBILITY.md](nn/professor_direction_investigation_20260929/next_stage_20260930/SAMPLING_FEASIBILITY.md); [sampling_feasibility.json](nn/professor_direction_investigation_20260929/next_stage_20260930/sampling_feasibility.json); targeted cap64/seed22 restores MIC/OPC/VASC support; golden IDs exact; biological pilot still blocked by Q2; power `POWER_UNESTABLISHED`.
- [x] Q5: Complete bounded external source/QC/specimen/feature feasibility or precise blocker. — `DONE` (`EXTERNAL_FEASIBILITY_BOUNDED`; overall confirmatory `UNRESOLVED`). Evidence: [EXTERNAL_FEASIBILITY.md](nn/professor_direction_investigation_20260929/next_stage_20260930/EXTERNAL_FEASIBILITY.md); [external_feasibility.json](nn/professor_direction_investigation_20260929/next_stage_20260930/external_feasibility.json); NeMO role PRESERVED; QC/specimen/feature UNRESOLVED; age + source declaration ACCEPTED; 0 new network bytes; GSE280175/GSE204684 EXPLORATORY_ONLY.
- [x] Checkpoint B: Support and candidate-source reports reviewed; no dataset-defect inference solely from null. — `DONE`. Evidence: Q4 `SUPPORT_REPAIR_PASS` / `ELIGIBILITY_FROZEN`; Q5 `EXTERNAL_FEASIBILITY_BOUNDED` with confirmatory `UNRESOLVED`; null/primary `B_NULL` does not imply dataset defect; unresolved external contracts retained for Q6.
- [x] Q6: Rank evidence-backed bottlenecks; choose one experiment; verify fit/resource arithmetic. — `DONE` (`EXPERIMENT_SELECTED`; fit feasibility `PASS`). Evidence: [RESEARCH_DECISION.md](nn/professor_direction_investigation_20260929/next_stage_20260930/RESEARCH_DECISION.md); [research_decision.json](nn/professor_direction_investigation_20260929/next_stage_20260930/research_decision.json); [FIT_LEDGER.json](nn/professor_direction_investigation_20260929/next_stage_20260930/FIT_LEDGER.json); chose `S9_analytic_pairing_use_synthetic_20260930` (49≤60 fits); S8 rounded-band boundary corrected with exact Bernoulli quantiles; mechanism mismatch retained; prior S8 `NO FIT` unchanged.
- [ ] Q7: Commit new analytic synthetic protocol with fitted-mechanism null and disjoint calibration/decision allocation.
- [ ] Q8: Reuse existing runner/models; verify oracle, leakage, pairing, gradients, reload and refusal risks.
- [ ] Q9: Obtain independent scientific/code review on exact hashes; maximum two correction cycles.
- [ ] Checkpoint C: Exact protocol/code/test/review/resource gates pass before fits.
- [ ] Q10: Run one bounded synthetic batch if authorized by gates; replay predictions; preserve every attempt.
- [ ] Q11a: If justified, freeze/review one separate real-data exploratory pilot protocol.
- [ ] Q11b: Verify minimal existing-runner adaptation and matched controls if needed.
- [ ] Q11c: Execute bounded pilot, replay results and faithfulness; otherwise document SKIPPED/BLOCKED.
- [ ] Q12: Commit verified handoff, disposition/evidence for every task, cumulative budgets and one next action.
- [ ] Checkpoint D: Stop on completed handoff or precise blocker after independent safe tasks finish. Positive result not required.

For skipped/blocked tasks, retain unchecked box and record disposition plus evidence beside it; do not mark an unexecuted experiment DONE. Q12 may close the run while broader study remains partial. Launch details: [GNHF_PROMPT.md](nn/professor_direction_investigation_20260929/next_stage_20260930/GNHF_PROMPT.md).

Updated: 2026-09-14 (planning only). Bounded F1–F3 implementation and input decision complete.
E0 and E1 tiny-reader proof complete; nine live fixture/control cases pass.
E2 offline pass recorded SOURCE_UNRESOLVED; exact object contract and E3 pending.
This clears only generic fixture/runtime controls; target workspace/class support
is unproven. E2-M HEAD proposal supersedes the old listing GET; nothing executed.
Retained-cell ingestion, neural training, final artifacts and
one-shot scoring verified. 150 synthetic internal fits plus six final refits.
Scientific acceptance gates remain open; the full research plan is not complete.

Contract: [dataset proposal](../docs/PAIRED_DS_MULTIOME_DATASET_OPTIONS.md). Overview: [plan.md](plan.md).

## Conditional follow-up queue — E0–E4

### Authorized local setup continuation

User approved local resources after E-A's stop. Follow the
[local amendment](plan.md#local-resource-amendment--2026-09-12), retaining old
attempts and the 360-second ledger. No scientific acceptance changes.

- [x] L0: start installed Docker once within 45 seconds, verify local endpoint,
  headroom and cached image inventory; do not pull/update/build or delete work.
- [x] L1: select one immutable compatible cached image, if present; prove isolated
  sparse fixture and negative/descendant-stop checks. R absence is NOT_RUN.
- [x] L2: save reviewed outcome/resources and commit tested slices. If no suitable
  cached reader exists, name one exact acquisition proposal rather than install
  without declared assets/sizes. Do not enter E2/E3 or restart B automatically.

L0 result: Docker started; local cgroup-v2 runtime available. No dedicated cached
R image identified; selected exact config ID is absent. L1 remains NOT_RUN.
See [setup evidence](../reports/generated/local_reader_setup_20260912/SETUP.md)
and [pinned acquisition proposal](../configs/local_r_reader_acquisition.json).
L2 closes only the reviewed proposal outcome. L1/E1 remain NOT_RUN; bounded
transfer/decode/import implementation is still required before any image install.

**Superseding result:** subsequent execution implemented and ran bounded image
acquisition/import, followed by the isolated sparse fixture. L1/E1 now pass for
the tested classes only. R 4.6.1 / Matrix 1.7.6; nine live cases; no dataset bytes.
Prior NOT_RUN/failed records are retained, not overwritten. See
[verified completion and ledger](../reports/generated/r_reader_completion_20260912/REVIEW.md).

Verification: inspect runtime/image evidence and actual test outputs; retain
original dirty/RNA fingerprints. Files: existing plan/checklist, shared audit
guide; fixture slice remains at most one script and one test plus guide.

User approved execution after reviewing this addition. Use
[the route/limit contract](plan.md#conditional-follow-up-paths--planning-only).
Preserve the completed F1–F5 evidence and all M1–M8 criteria. Only one route is
active at a time, with explicit checkpoints before installation or acquisition.

### E0: Select the first route and record fallback triggers

**Description:** Review existing evidence offline and select A by default, B only
for a documented environment reason, or C only when an exact documented export
exists. Record when D/E would become relevant; do not run a discovery campaign.

**Acceptance criteria:**

- [x] One `route_decision.md` names target/source hashes, route, specific question,
  known/unknown facts, failure category, fallback trigger and uncovered authority.
- [x] Resource/enforcement availability and shared E1 counters are specified;
  original dirty/RNA/evidence fingerprints and existing approvals are preserved.
- [x] Stop within 30 minutes, no network/install/data read beyond existing evidence.
  Missing target identity or controls yields an explicit refusal, not a guessed URL.

**Verification:** inspect saved evidence against F2d/F3 and the source note;
table-top trace local installation failure, missing assay, missing provenance,
unknown memory and no exact export. Each yields one justified next action.
**Dependencies:** reviewed plan; accepted F1–F3 baseline `48b90c9`.
**Result:** [E0 record](../reports/generated/reader_enablement_20260912/route_decision.md).
A lacks R and an active Docker daemon. B capability preflight next, not a data read.
**Files likely touched:** one concise evidence note in `docs/PAIRED_MULTIOME_AUDIT.md`;
new ignored record. **Estimated scope:** Small.

### E1: Prove a bounded reader path with a tiny sparse fixture

**Description:** Implement the narrow fixture checker, then run A or conditional
B only after the installation scope is approved. Do not inspect a real object.

**Acceptance criteria:**

- [x] Pin runtime/package assets; fixture preserves sparse integer counts, row/column
  identifiers, interval fields and donor metadata across save/load. Record actual
  classes tested, unsupported classes and no dense conversion.
- [x] Malformed fixture, missing dependency, output reuse and budget failure refuse
  safely. All descendants stop on timeout/resource failure; tests cover that
  behavior. Missing R produces explicit NOT_RUN, never a passing scientific gate.
- [x] Original attempts plus the explicitly authorized local continuation share
  the amended E1 limits in plan.md; no object
  bytes fetched. Record cumulative bytes/time/disk and process-tree memory evidence.
  One successful fixture closes E1; both failures or cap exhaustion stop.

**Verification:** smallest offline regression first, then the R fixture under
approved controls; run relevant repository lint/tests if code changes. Independently
check sparse values/order and fixture hashes. A fixture is not real-object proof.
**Dependencies:** E0 plus approval for bounded dependency action; existing free-CPU
approval is not re-requested. C can instead verify its existing export reader.
**Files likely touched:** proposed `scripts/inspect_development_object.R`,
`tests/test_development_object_reader.py`, shared audit guide. If necessary
process-tree controls cannot fit a separately reviewed small slice, stop and
scope that prerequisite; do not repurpose the accepted RNA supervisor.
**Estimated scope:** Medium, at most three files for the fixture slice.

**Result:** E1 passes for `list`/`data.frame`/`dgCMatrix` only. The 392-byte fixture
preserves four nonzero counts, empty cell column, IDs, intervals and donors exactly.
Live malformed-count/ID/field/interval and output-reuse refusals pass. Timeout
kills child/grandchild container; 128 MiB OOM kills R and its child. All test
containers end with Running=false/Pid=0 and are removed. No Seurat/ChromatinAssay
support, real-assay availability, QC acceptance or training readiness is implied.

### Checkpoint E-A: Reader evidence, not permission to download

- [x] Review E0/E1 artifacts and counters. Exactly one applicable reader route is
  demonstrated, or a specific environment/control blocker is documented.
- [x] No real-object contents, counts/QC acceptance or training readiness inferred.
  Stop unless E2's next contract is separately reviewed and approved.

**Historical result:** [CONTROL_UNRESOLVED](../reports/generated/reader_enablement_20260912/DECISION.md).
A lacks a reader/active local Docker daemon. B has R but a read-only cgroup mount;
the actual membership cannot be safely resolved. One read-only B probe, no R or
installer launch. E1 fixture/descendant-stop criteria remain unchecked, not waived.
The approved local continuation above subsequently proved those fixture controls.

### E2: Freeze one target and an enforceable inspection budget

**Description:** Produce the offline per-object contract. Default to the selected
7.6G-listed object; prefer C only with a real documented export. D requires an
evidence-backed missing-assay/coverage reason, never just a memory failure.

**Acceptance criteria:**

- [ ] Pin one source/target, format and available checksum/version evidence, intended
  donor/population scope, exact inspection questions and acceptance requirements.
  Rounded listing size, unknown contents and expected memory are labeled honestly.
- [ ] Specify numeric network/decoded/disk/process-tree-RSS/wall ceilings, headroom,
  enforcement, preservation/cleanup rules and uncovered authority before any
  acquisition. Unknown expected requirements do not mean unlimited permission.
- [x] Finish one offline proposal within 30 minutes, 0 network/installs/downloads.
  If identity or defensible controls/limits cannot be fixed, stop RESOURCE_UNRESOLVED
  or SOURCE_UNRESOLVED. Do not start an exploratory whole-object load to estimate RAM.
  Source follow-up is only the separately bounded E2-M HEAD proposal below;
  no request occurs during this offline task.

**Verification:** review the budget against a timestamped host snapshot, retained
attempt files, expanded/input/output working sets and the reader's tested limits.
Check that B does not assert free capacity and D has its own contract.
**Dependencies:** E0 and applicable E1/export-reader proof; separate review/approval
is needed to execute the resulting contract.
**Files likely touched:** one proposed source/budget JSON in `configs/` and shared
audit guide, plus ignored snapshots. **Estimated scope:** Small, at most two files.

**Result:** [offline source contract](../configs/development_object_source_contract.json)
records SOURCE_UNRESOLVED. A candidate URL is derived from pinned directory/name
evidence; payload bytes/checksum, classes and full-object resource needs remain
unknown. E2-M replaces the earlier listing-GET proposal; no request, payload or
class-package installation has run. Other E2 acceptance boxes remain open;
E3 cannot start under a zero-byte object budget.

#### E2-M launcher breakdown — planning update 2026-09-14

These subtasks refine, not replace, the existing E2-M contract below. All pending
items remain proposals. Preserve source-contract and source-note hashes, original
ledgers, RNA findings and all existing checkboxes. Future live scope remains:
one HEAD, 15 seconds total, <=65,536 header bytes, zero application body/decoded
reads, <=256 MiB process-tree memory, zero swap, <=1 MiB retained output and
>=10 GiB free host disk. No retry, redirect, GET/Range, install or budget reset.

#### E2-M0: Accepted capture-core evidence

- [x] `11a4b7b` adds `scripts/capture_development_head.py` and
  `tests/test_development_head_capture.py`; existing parser unchanged.
- [x] Supervisor record: 45 focused tests, 836 full-suite tests, Ruff passing;
  no default live transport, CLI or dataset request.
  [Evidence](/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/lmstudio_head_capture_split_20260914.mOJ8o9/REVIEW.md).

This closes the core coding slice only, not runtime proof or parent E2-M.

#### E2-M1: Establish runtime/control feasibility

**Description:** One proposed <=30-minute read-only/offline pass over the existing
host, cached runtime and control evidence. No runtime launch, setting changes,
network, installs or destructive cleanup.

**Acceptance criteria:**

- [ ] Pin available compatible Python/TLS runtime and code identities; record
  actual isolation, hard aggregate memory/no-swap, watchdog, output/disk controls
  and their uncovered proof. A flag or per-process limit alone is not proof.
- [ ] Define bounded, safe offline test allocations against preserved ledgers,
  non-root/no-host-data-mount configuration and one end-to-end wall budget;
  identify missing permission separately from missing technical evidence.
- [ ] If any prerequisite is unknown/unavailable, document the exact blocker
  and smallest scoped next action; no installation or weaker fallback.

**Dependencies:** E2 offline source record and E2-M0.
**Verification:** timestamped inventory/configuration evidence mapped to each
frozen limit; independent review before runtime probes. No claimed host inspection
or hard-control proof from this planning edit.
**Files likely touched:** existing `docs/PAIRED_MULTIOME_AUDIT.md`; ignored evidence
under a new `reports/generated/` directory. **Scope:** Small, 1 tracked file.
**Stop outcome:** named resource/authority blocker; source status stays unresolved.

#### E2-M2: Build a refusal-first launcher binding

**Description:** Implement one narrow wrapper around the accepted core, using only
the reviewed cached runtime/control design. Develop against offline fakes first;
no real default connection or startup side effect during tests.

**Acceptance criteria:**

- [ ] Before transport, validate the unchanged source contract AND source-note
  hashes, code/runtime identity, owner's exact HEAD approval, bounded labels and
  output destination; refuse stale/missing evidence or unsupported controls.
- [ ] Configure verified TLS with no proxy/retry/redirect and inspected non-root
  isolation. Enforce hard aggregate memory/no-swap before child execution, with
  an external process-tree watchdog for the single wall budget covering startup,
  connection/TLS, request/read and cleanup; no polling-only or phase-reset shortcut.
- [ ] Bound aggregate output including errors/logs, check disk headroom, preserve
  evidence in a new directory, and refuse late/failed cleanup. Never promote
  capture success into payload/scientific acceptance.

**Dependencies:** accepted E2-M1 design and applicable local implementation scope.
**Verification:** proposed focused tests for preflight refusals, input/output
bounds, transport binding and cleanup; existing parser/core regressions also pass.
No live network. Command for new tests once present:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv-p22/bin/python -m pytest -q tests/test_launcher_head_capture.py`.
**Files likely touched:** proposed `scripts/launcher_head_capture.py`,
proposed `tests/test_launcher_head_capture.py`, existing audit guide.
**Scope:** Medium, <=3 tracked files.
**Stop outcome:** unproven control or missing asset/permission blocks live use.

#### E2-M3: Prove bounded launcher failure controls

**Description:** Within accepted offline test allocations only, exercise the real
selected containment mechanism with tiny hostile fixtures; no host exhaustion,
new dependency acquisition or real dataset endpoint.

**Acceptance criteria:**

- [ ] Independently verify child/process-tree termination for hangs (including
  non-cooperative work) within the total deadline, with bounded cleanup evidence;
  a fake-clock unit test alone does not establish this.
- [ ] Demonstrate hard aggregate memory/no-swap and output containment in safe
  capped tests. Missing enforcement or nonzero swap refuses before the workload;
  monitoring a breach then killing is not hard-limit proof.
- [ ] Verify changed hashes, absent scope approval, unsafe input/transport,
  insufficient disk, excessive output and late/failed cleanup all refuse.
  Preserve proof of no live request and no leftover child processes.

**Dependencies:** E2-M2 and reviewed explicit probe allocations from E2-M1;
missing allocation is a blocker, not permission to improvise.
**Verification:** proposed launcher focused tests, existing parser/core focused
tests, `make lint`, and `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src make test-all`;
inspect real containment/termination records separately from mocked tests.
**Files likely touched:** proposed launcher test file and existing audit guide;
ignored probe evidence. **Scope:** Small, <=2 tracked files.
**Stop outcome:** any failed/unproven control blocks HEAD; record smallest fix.

#### Checkpoint E2-M-Review: Controls accepted; live authority separate

- [ ] Independent review accepts code and real control evidence; tests match the
  frozen limits and no existing scientific gate or source contract changed.
- [ ] Owner's explicit approval covers this exact one-HEAD scope. Reviewer/model
  agreement cannot grant permission; missing approval means no request.
- [ ] Resource and source checks will be repeated immediately before the attempt.
  Changed facts or stronger body-byte semantics require review, not silent relaxation.

#### E2-M4: Execute the existing one-HEAD scope conditionally

**Description:** After the checkpoint only, execute parent E2-M once. This task
adds no live command or permission to the current plan edit.

**Acceptance criteria:**

- [ ] Revalidate approval, hashes and controls; make at most one HEAD under every
  parent limit. No GET/Range, redirect, retry, alternate source or budget reset.
- [ ] Record URL/time/status, exact captured headers/prefix and its local hash,
  bounds/stop evidence and valid positive server-declared Content-Length.
  Missing optional validators remain unknown; no payload checksum is invented.
- [ ] Non-200, redirect, invalid/missing length, changed evidence or any control
  failure stops SOURCE_UNRESOLVED with its reason. Success permits only E2-R
  offline planning; it does not establish measured ATAC counts or authorize E3.

**Dependencies:** accepted E2-M-Review and existing parent E2-M authorization.
**Verification:** independent raw-header/hash and ledger review; no second request
to verify the first. Existing E2-M, E2-R and E2-C requirements remain authoritative.
**Files likely touched:** existing audit guide; result in a new ignored
`reports/generated/` directory, not a tracked payload. **Scope:** Small, 1 tracked file.
**Stop outcome:** one reviewed metadata result or concrete blocker; no automatic
object acquisition, reader installation, fixture run or training.

#### E2-M: Resolve available source metadata once

**Description:** Conditional metadata-only request, not execution authorized by
this plan edit. Use only the contract's candidate URL; no directory reread.

**Acceptance criteria:**

- [ ] After separate scope approval, one HEAD; 15 seconds, no redirect/retry,
  <=65,536 total header bytes, zero body/decoded-body reads, 256 MiB process-tree
  memory/no swap, <=1 MiB output, >=10 GiB free disk. Test these bounds offline
  before requesting; refuse if the selected client/runtime cannot enforce them.
- [ ] Record URL, timestamp, status, headers, locally computed header-record hash,
  and positive Content-Length when valid. Distinguish server-declared transfer size
  from measured payload bytes. Missing ETag/Last-Modified/Accept-Ranges/checksum
  stays unknown, not a fabricated observation or automatic failure of identity.
- [ ] Non-200/redirect, missing/invalid length, changed source evidence or bound
  failure stops SOURCE_UNRESOLVED with the exact reason. No GET/Range/retry or
  package install follows. Success permits only E2-R planning, not object access.

**Verification:** offline mocked 200/missing-length/redirect/oversize/deadline
cases plus independent header/hash review if the request is authorized and runs.
**Dependencies:** E2 offline record and approval of this exact metadata scope.
**Files likely touched:** one narrow request/check script, one focused test,
shared audit guide; new ignored response record. **Scope:** Medium, <=3 files.

#### E2-R: Cost target-compatible reading before acquisition

**Description:** One offline proposal, <=30 minutes, zero network/install/object
bytes. No generic runtime restart or repeated image acquisition.

**Acceptance criteria:**

- [ ] Pin the selected workspace/extraction path and compatible package versions
  or equivalent reader. Cost exact missing dependency assets first; missing sizes
  or support stay unresolved. For R, require a <=1 MiB `save/load` workspace/class fixture
  with exact sparse-count/ID/metadata checks and unexpected-class refusal before E3.
  The prior `saveRDS/readRDS` fixture remains complete but does not satisfy this.
- [ ] Propose separate numeric transfer, decoded, retained/temporary disk,
  process-tree memory/swap and wall caps, >=10 GiB disk headroom, control/stop
  evidence, and required authority. Fresh host resources and justified estimates
  must support the full-load proposal; neither HEAD nor compressed size proves RAM.
  Package/class-fixture work has its own explicit allocation against preserved
  ledgers or an approved amendment; no implicit new 506-second setup attempt.
- [ ] Stop RESOURCE_UNRESOLVED (or name missing reader evidence) if no defensible
  contract exists. No install, VM adjustment, object download or full-load probe
  is authorized here. Record exactly what evidence/allocation could change that.

**Verification:** table-top missing-package, unknown expansion, insufficient
memory/disk and unsupported-class cases; each yields a distinct refusal. An
approved later R fixture must test `.rda` and applicable classes, not generic R
only. Route C instead verifies its documented format with the supported export reader.
**Dependencies:** usable E2-M metadata or a separately reviewed documented export;
existing generic E1 evidence. E3 additionally requires actual applicable proof.
**Files likely touched:** source/resource contract and shared audit guide; new
ignored proposal evidence. **Scope:** Small, <=2 files.

#### Checkpoint E2-C: Real-object go/no-go

- [ ] E2-M metadata and E2-R resource/class contract independently accepted;
  separately authorized applicable fixture passes before any real-object load.
- [ ] Exact acquisition/inspection permission is explicit; otherwise STOP with
  the unresolved item. No checkbox closes because a model endorsed the plan.

### E3: Inspect only the approved source and report measured facts

**Description:** Conditional later implementation/acquisition; not runnable under
the current plan-only request. Extend the fixture reader narrowly for the selected
object, or use existing MEX readers for C. Do not build adapters for unverified formats.

**Acceptance criteria:**

- [ ] New output records target/code hashes and the gate fields in plan.md; missing
  assays, counts, metadata, coordinates or provenance remain explicit. Preserve
  paired sparse values/order and refuse duplicate/inconsistent IDs or dense fallback.
- [ ] Offline tests cover malformed/incomplete objects and resource-stop paths
  before the single real attempt. Exact target and approved E2 caps are enforced;
  no source substitution, budget reset, hidden retry or uncontrolled deserialization.
- [ ] Route decision distinguishes missing assay/coverage (D may be proposed),
  resource failure (stop/re-scope), and unknown scientific provenance (missing
  evidence, not runtime failure). Do not rewrite old F2d/F3 records or imply training.

**Verification:** independently inspect sampled sparse entries and complete
ID/donor/region fingerprints against the source; verify resource/stop ledger and
all acceptance claims. A read failure cannot establish dataset-wide absence.
**Dependencies:** E2-C and E2's approved exact acquisition/inspection contract;
applicable `.rda`/class proof for R, or supported export-reader proof for C.
A prefix/Range probe is not that proof.
**Files likely touched:** narrow R reader extension OR existing MEX adapter/test,
shared audit guide; new ignored inspection record. **Estimated scope:** Medium,
at most three files; no generic downloader or new training entrypoint.

### E4: Close the route with an input decision or bounded fallback proposal

**Description:** Review E3 evidence and choose exactly one next action. E may be
costed offline only if no permitted usable object/export remains; external QC work
gets a separate proposal when development progress makes it useful.

**Acceptance criteria:**

- [x] Each relevant development gate has evidence-linked PASS/FAIL/UNRESOLVED,
  inspected scope, donor/class support and missing artifact; external/cross-cohort
  gates remain separate. No checkbox closes on a file name, fixture or matching total.
- [x] Select one justified next action: M5 review only if development inputs are
  accepted, otherwise a newly bounded missing-evidence/resource proposal or STOP.
  E/external costing each allows one 30-minute offline pass, no payload/fragments.
- [x] Decision states biological question remains untested until real held-out
  comparison; internal results cannot replace the external primary contrast.
  No RNA rerun, donor deletion, new dataset, paid compute, outreach or weakened gate.

**Verification:** review failure/success traces and evidence hashes; ensure no
hidden NeMO-to-development switch, automatic M6c fit or renewed F2s request.
**Dependencies:** E3 outcome, or a documented earlier stop; route-specific review.
**Result:** [earlier control stop](../reports/generated/reader_enablement_20260912/DECISION.md).
One next action: separately reviewed local container setup proposal with explicit
attempt/counter amendment. No new runtime launch or data acquisition is authorized.
**Files likely touched:** shared audit guide and `tasks/todo.md`; new ignored
decision record. **Estimated scope:** Small.

### Checkpoint E-B: Terminal decision

- [ ] Accepted development input or specific blocker reviewed; original RNA,
  F1–F3 artifacts and M1–M8 acceptance criteria preserved.
- [ ] Exactly one next action and its uncovered authority named; no automatic
  full object, fragments, model training or external scoring starts.

## Advancement queue — bounded execution record 2026-09-12

These tasks extend the existing P22 work; they do not replace or complete M1–M8.
F4–F5 are complete in accepted head `46d7523`, the baseline of this isolated
branch; work is not merged into the original user checkout.
[Durable RNA evidence](../reports/generated/rna_donor_influence_20260910_supervised/REVIEW.md)
records 68 valid omissions and 628 passing tests. Do not schedule those tasks again.
User then authorized implementation of
[the frozen cycle contract](plan.md#frozen-scope-of-this-cycle).
Work is isolated in `codex/p22-input-feasibility`; preserve unrelated dirty files and record one
verified slice per local commit. No push, merge or GNHF resume.

**Cycle endpoint:** F1 → F2d → F2s → F3 → reviewed decision and STOP. Result is
one guard commit, resolved or explicitly unresolved source identity, executable
proposal for the first unmet development-inspection prerequisite, and a specific
input decision. Only F2s uses network: one tiny official-bag read.
No NeMO payload probe or processed-object download occurs in this cycle.
F2d comes first and remains useful even when F2s fails. Internal model comparison
is a later development milestone; M5's planned external primary contrast stays intact.

**Workspace verification completed:** RNA recovery bundle verified; accepted
code/results preserved. Isolated baseline is `46d7523` plus plan files from
`4219705` (carried by `81ffd12`). Fingerprint original dirty
files and protected evidence. If that context cannot be recovered, stop without
resetting, overwriting, or automatically committing unrelated work.

### F1: Bring the reviewed coordinate guard into the implementation branch

**Description:** Recover only the reviewed adapter/test slice from
`reports/generated/gnhf_companion_2026-09-09/0001-fix-reject-contradictory-peak-identifiers-and-coordi.patch`
after checking the target branch. Source commit: `3b677d5`; fallback bundle:
`reports/generated/gnhf_companion_2026-09-09/reviewed-candidate.bundle`, head
`7a9bedf97394afd2a3b1c6beee202f9a30619444`, prerequisite
`54e0e371d1263463aca9f8f79748ea35aaddcccc`. The isolated checkout
`/private/tmp/p22-gnhf-companion.scEOcw/workspace` still existed on 2026-09-10.
Do not import accompanying old plan documents. Preserve ignored recovery artifacts
until the verified code/test slice has a durable local commit; no cleanup before then.

**Reason:** a peak ID that contradicts its coordinate columns can invalidate the
measurement comparison. Reuse the reviewed 26-line fix; do not redesign ingestion.

**Acceptance criteria:**

- [x] Contradictory coordinate-shaped peak IDs are rejected by the shared reader;
  valid ARC/MEX, opaque peak IDs and unmapped RNA retain their existing behavior.
- [x] Source/dirty-file hashes are preserved; the change is present exactly once
  in an isolated reviewed commit, without changing RNA evidence or scientific gates.

**Verification:** verify patch SHA256
`c23e79578ae6540e147b339cbab5699337eb4249b0057ed8b3842f50f5898aec`,
then run `git apply --check` on the exact patch in the intended
clean workspace (read-only); if using the fallback, run `git bundle verify` and
inspect the isolated slice before recovery. Stop on divergence or missing evidence.
The recovered `tests/test_multiome.py` regression must fail against the base and
pass with the patch; run `tests/test_atac_features.py`, `make lint` and
`make test-fast`. Inspect the staged diff and three existing public feature lists.
**Dependencies:** plan approval and clean implementation workspace.
**Files likely touched:** `src/p22/data/multiome.py`, `tests/test_multiome.py`.
**Estimated scope:** Small, two files.

### F2d: Freeze development processed-object inspection feasibility

**Description:** Produce an offline capability/resource record for only
`GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz` (listed as 7.6G).

**Reason:** development common measured ATAC counts gate internal training. NeMO
source metadata cannot supply them. Planning checks found no R executable on PATH
or `pyreadr`/`rpy2` in `.venv-p22`; current free disk was 27.75 GiB. Refresh these
observations; missing executables in one environment do not prove global absence.

**Acceptance criteria:**

- [x] Manually assemble `development_object_feasibility.json` using the schema
  in `plan.md`: timestamp, commands/results, source hashes, runtime paths/versions,
  disk/memory evidence and resource unknowns. Check `R`, `Rscript`, `pyreadr`, and
  `rpy2`; distinguish availability from proven support for the serialized object
  classes and sparse assays. Generic-reader presence alone cannot pass this check.
- [x] Freeze later inspection questions: object/classes, assay names, raw-count
  layer/slot, sparse dimensions, feature identifiers/coordinates and genome build,
  count units, donor/cell metadata, retained-cell semantics, and presence of a
  common measured ATAC matrix such as `peaks_by_cluster`, and donors/labels used
  for peak discovery. Shared columns do not establish training-only selection.
- [x] Select one follow-up targeting the first unmet prerequisite: bounded reader
  enablement/tiny sparse fixture if support is absent or untested; bounded sizing
  if full-object fit is unknown; full inspection only when both are supported.
  Specify that action's runtime, numeric byte/disk/RSS/time limits, enforcement,
  headroom, outputs and stop rule. Keep unknown full-object quantities unresolved;
  even reading assay names can deserialize the whole object. No dense conversion,
  install, fixture execution, HEAD/GET or object download occurs in F2d.

**Verification:** compare record with local executable/module checks and current
disk report; unknown quantities must be null with reasons. A later tiny fixture
does not prove real-object resource fit. Ensure the proposal selects one object,
checks existing approvals and identifies only uncovered authority. Do not require
approval again for an already authorized action within its existing limits.
**Dependencies:** F1; run before F2s, with no dependency on external access.
**Files likely touched:** `docs/PAIRED_MULTIOME_AUDIT.md` plus ignored generated record.
**Estimated scope:** Small, one evidence note; no code or network.

### F2s: Resolve NeMO payload identity before considering a probe

**Description:** Implement one small stdlib resolver for the pinned official ATAC
Open bag. Read the complete 1,867-byte bag once under the frozen caps, validate
its preserved hash, then join its target fetch and checksum declarations locally.

**Reason:** exact payload URL is absent from preserved local evidence. Defer
payload-probe construction; this tiny source check updates the external track.

**Acceptance criteria:**

- [x] One GET only; no HEAD, retry or redirect; 65,536 application-read body bytes,
  262,144 aggregate decoded bytes including headers, and one 15-second monotonic
  deadline covering DNS/connect/TLS/read. Require HTTP 200, disable HTTP decoding,
  and stop before parsing unless body is exactly 1,867 bytes with SHA256
  `4698c4b80d1e1bde7588b9b0979beb113df2ca24aebf54afbbac606eaf064d45`.
- [x] Require one matching row in `fetch.txt` and `manifest-md5.txt`, joined by
  bag-relative payload path. URL/size come from the former, MD5 from the latter;
  match target filename, 1,540,753,269 bytes and
  `796c8b3aa587b257af0a46615a437dba`. Reject ambiguous rows, unsafe paths and links;
  allow regular metadata and directory entries. Never infer or follow payload URL.
- [x] Write `source_identity.json` per `plan.md` and preserve the hash-matching
  raw bag for offline verification. Record supplied bag `ETag`/`Last-Modified`,
  byte totals and elapsed time; these are not payload validators. Mismatch yields
  `SOURCE_EVIDENCE_CHANGED`; transport/preflight failure is explicit, with null
  resolved fields. No failure causes a retry or blocks the development proposal.

**Verification:** local fixtures cover the successful two-manifest join, changed
hash/length, absent/duplicate rows, mismatched path/size/MD5, unsafe members,
redirect, encoded response, byte/expansion caps, truncated archive, stalled and
slow-drip deadline expiry, and existing output directory. Fixture pins must not
override production target/limits through the CLI. Run
`PYTHONPATH=src .venv-p22/bin/python -m pytest -q tests/test_resolve_nemo_source.py`,
`make lint`, and `PYTHONPATH=src make test-fast` before the live request. Compare
saved bag, row join and request ledger offline afterward; no second network run.
**Dependencies:** F1 and the F2d record; no accepted counts or R reader required.
**Files likely touched:** new `scripts/resolve_nemo_source.py` and
`tests/test_resolve_nemo_source.py`; concise evidence in `docs/PAIRED_MULTIOME_AUDIT.md`.
**Estimated scope:** Medium, two code/test files, one shared evidence note and
one bounded request. Commit tested implementation before recording the live outcome.

### Checkpoint F-A: Useful preflight

- [x] F1/F2s pass focused tests; F2s has one reviewed bounded outcome; F2d has one
  reviewed offline record. Original inputs remain unchanged. No scientific gate
  passes from URL recovery, file size, reader availability or object name alone.

### F3: Produce one actionable input-feasibility decision

**Description:** Extend the offline audit report to connect inspected facts with
the existing M1–M4 acceptance requirements. Explicitly identify the development
common-count blocker; NeMO metadata cannot resolve it. Preserve the distinction
between inspected incompatible raw libraries and uninspected published processed
objects. Do not repeat unchanged source searches or imply F3 produces new counts.

**Reason:** the next action must target the binding missing artifact, not restart
general research. Development readiness and external readiness must stay separate.

**Acceptance criteria:**

- [x] Record separate development/external evidence for retained barcodes/QC,
  pairing, specimen provenance, genome/coordinate convention, count units, exact
  measured regions and feature provenance, with pinned sources/hashes. Missing
  evidence cannot be replaced by a user-supplied `PASS` boolean. Consume the pinned
  F2s source-identity and F2d development-feasibility records through
  `--source-identity` and `--development-feasibility`, each with its required
  reviewed `-sha256` option; preserve callers
  that omit them. Verify successful source resolution against the saved raw bag
  and manifest join. Reject malformed/tampered records or unexplained source/budget
  discrepancies; a well-formed unresolved-source record is valid input. Add
  `input_decision.json` and `INPUT_DECISION.md` with fields frozen in `plan.md`.
- [x] Report M4's existing `PASS`/`INCONCLUSIVE`/`NEEDS_RECOUNT` plus unresolved
  gates. A partial archive, matching row total or annotation mask cannot certify
  full membership, common counts, author QC or readiness to train.
- [x] A blocked report names the exact missing artifact, inspected source scope,
  and one smallest next action with proposed bytes/disk and required authority.
  Do not claim exhaustive absence or automatically launch that next action. Keep
  `training_allowed=false` and `model_training_performed=false`; an input decision
  cannot supply the absent M5 protocol. Source-resolution failure does not move
  NeMO ahead of the first unmet development prerequisite. Stop after review.

**Verification:** extend `tests/test_multiome.py`, `tests/test_atac_features.py` and
new `tests/test_input_decision.py`. Include equal totals with unknown QC, partial
coverage, count-unit mismatch, unmeasured regions, missing/tampered feasibility
fields, source-resolution failure, source hash/join mismatch, fabricated reader
readiness, unknown resource quantities, changed/omitted frozen caps and
existing-directory refusal.
Run these focused tests, `make lint`, `PYTHONPATH=src make test-fast`, then the
existing offline audit once with the exact caps in `plan.md`. Review all report
claims against pinned sources without any training or fresh source searches.
**Dependencies:** reviewed F2d/F2s outcomes; facts can be incomplete but must be labeled honestly.
**Files likely touched:** `scripts/audit_multiome.py`, `tests/test_multiome.py`,
`tests/test_atac_features.py`, new `tests/test_input_decision.py`,
`docs/PAIRED_MULTIOME_AUDIT.md`.
**Estimated scope:** Medium, at most five files. One reviewed local code/test commit,
followed by a concise reviewed decision record.

### Checkpoint F-B: Input decision, not perpetual inspection

- [x] F3 produces accepted evidence or a concrete blocker. Stop paired execution
  if required inputs fail; do not repeat F2s or expand F2d without changed evidence
  and separate authority.
- [ ] Any development-only pilot has its own reviewed scope and all relevant
  development gates. Original combined-cohort Checkpoint B and external gates
  remain unchecked while their requirements are unmet.
  Not applicable to this completed cycle: no internal pilot or new fit was run.
- [x] F1–F3 changed only the permitted files; tests, source/RNA/dirty-file hashes,
  source ledger, feasibility record and final decision pass independent review. Code failure is not
  an accepted blocked-input conclusion. Handoff names exactly one next action and
  its required authority; no automatic M6a, real fold or processed-object inspection.

**Completion evidence:** F1 `cf8ed33`; F2d `6c101bb`; F2s `83cf31e` and
outcome `879ff1c`; F3 `3b007d7`. One source GET and one offline audit completed.
Final verification: 636 fast tests, 668 full tests and lint; separate code and
artifact review approved the scoped decision. Nine scientific gates remain
explicit; no training ran. [Full evidence and hashes](../docs/PAIRED_MULTIOME_AUDIT.md#f3-decision-and-closure).
Next action is only the bounded reader/fixture proposal, not a full object download.

### F4: Freeze the new RNA donor-influence diagnostic

**Status:** complete in isolated `46d7523`; evidence in the durable RNA delivery.
Checkboxes below record that completed work, not integration into this checkout.

**Description:** Determine which discovery donors drive changes and whether their
influence is concentrated or diffuse. The completed bootstrap already measures
aggregate uncertainty; this new post-hoc diagnostic attributes leave-one-donor-out
changes descriptively, without identifying a causal donor or resolving power.

**Acceptance criteria:**

- [x] Pin existing H5AD/workbook and reference-result hashes, four comparison
  mappings, current cell/QC and gene rules, age/sex model and every eligible donor.
  Freeze baseline-gene derivation before results. Baseline Spearman must match saved
  values with `atol=1e-10, rtol=0`; donor identities and saved gene/donor counts must
  match exactly, with gene IDs/order checked against pinned inputs. A mismatch
  stops execution, not a tolerance retune or outcome-selected omission.
- [x] Freeze the same-support comparison contract below; report each donor's
  same-support correlation delta separately from its support-shift component,
  gene counts, class support and fit status. Rank absolute same-support deltas
  within each comparison with support counts beside them; do not pool comparisons
  as independent evidence or describe rank changes as coefficient magnitudes.
- [x] Label outputs `POST_HOC_EXPLORATORY`; no new significance cutoff, headline
  reclassification, causal claim or external-donor uncertainty claim. Freeze the
  no-download/CPU/resource limits from the plan; no bootstrap per omitted donor.

**Same-support contract:** F5's baseline-only preflight derives and fingerprints
`G0`, the baseline shared-gene set, from F4's frozen rules before any omission.
Reproduce saved summaries first; do not claim historical gene identities were
verified if the old run saved only counts. Let
`Gi = G0 ∩ omission-eligible genes` after refitting donor omission `i` and reapplying
the existing expression floor. Use identical gene order and external values for:

- `same_support_delta = rho_loo(Gi) - rho_baseline(Gi)`;
- `support_delta = rho_baseline(Gi) - rho_baseline(G0)`;
- their sum, the total change on the retained baseline-gene support.

Report `|G0|`, `|Gi|`, lost and newly eligible shared-gene counts. Newly eligible
genes stay outside this primary diagnostic; report their count without expanding
the endpoint. These are descriptive, support-conditional components, not a causal
decomposition or proof that gene selection dominates. Constant vectors, fewer than
the existing 500 shared genes, insufficient class support or rank failure produce
an unavailable result; do not relax gates, drop covariates or silently replace
genes. No top-100 agreement extension or bootstrap-SD standardization is scheduled.
All comparisons share discovery donors; RG → oRG and RG → vRG additionally share
the same discovery cells. Summary and plot must disclose this non-independence.

**Verification:** independent protocol review and canonical config fingerprint;
validate local input paths/hashes without running the analysis. F5 adds executable
schema, deterministic-fixture and preservation checks before using real data.
**Dependencies:** plan approval of this follow-up scope; independent of F1–F3.
**Files likely touched:** new `configs/rna_donor_influence.json`.
**Estimated scope:** Small, one file.

### F5: Deliver the one-command donor-influence experiment

**Status:** complete in isolated `46d7523`; 68/68 real omissions available, all
saved baselines reproduced, independent review passed. No repeat scheduled.

**Description:** Reuse `donor_pseudobulk`, `collapse_donor_metadata` and
`fit_discovery_effects`; aggregate existing counts once per unique population and
reuse compact donor aggregates across all omissions. Do not rerun the full original
pipeline just to produce a diagnostic.

**Acceptance criteria:**

- [x] New diagnostic command validates F4's contract, reproduces baseline
  Spearman summaries within F4's frozen tolerance and saves baseline `G0`/hash,
  then refits every eligible donor omission. Implement both delta components;
  alignment and each omission are auditable.
- [x] New exclusive output directory contains `donor_influence.csv`, one labeled
  plot, `SUMMARY.md`, config/source hashes and measured resources. It reports all
  comparisons and invalid fits, ranked donor influence, support changes, shared-donor
  non-independence, uncertainty limitations and one next decision. No new power claim.
- [x] Original outputs, validation rows, headline/G8, approvals, source data and
  notebook hashes stay unchanged. No resampling cells as independent donors,
  donor exclusion recommendation from favorable scores, or fake ATAC input.

**Verification:** isolated `tests/test_rna_donor_influence.py` and companion fixtures include a planted
influential donor, stable-data control, rank failure, gene-set/support changes,
hand-calculated delta decomposition, baseline-mismatch refusal, determinism,
stale-cache rejection if caching is used, and no-overwrite checks. Edge-case guards
need fixtures even if current real omissions do not trigger them; do not call
fixture behavior an observed real-data failure.
Run existing `tests/test_external_validation.py`, `make lint`, `make test-fast`,
then one bounded real diagnostic after the fixture checks pass.
**Dependencies:** F4, not NeMO or GNHF.
**Files likely touched:** new `src/p22/eval/rna_donor_influence.py`,
new `scripts/diagnose_rna_replication.py`, new `tests/test_rna_donor_influence.py`.
**Estimated scope:** Medium, three files.

### Checkpoint F-C: First new scientific artifact

- [x] F5 table/plot/report reproduce from their frozen inputs and are independently
  reviewed. Primary RNA results remain unchanged even if the diagnostic is positive.
- [x] Report donor-specific influence and its concentration separately from gene
  support changes; retain unresolved external uncertainty. A null/inconclusive
  diagnostic still completes
  this bounded question; expanding to new cohorts or methods requires a new plan.

**Next:** real M5–M8 execution remains deferred pending development common-count
acceptance (or a separately specified and accepted exploratory representation),
the real protocol, and each stage's additional gates. F1–F3 do not supply that
representation. Keep M6a's offline readiness work separate from fitting; no new
neural architecture or implicit peak-to-gene implementation.

Commands below remain per-task acceptance targets. Runnable evidence is in
[the audit guide](../docs/PAIRED_MULTIOME_AUDIT.md) and [training guide](../docs/PAIRED_MULTIOME_TRAINING.md).
Synthetic fixtures establish software behavior only; public-file audits establish file
facts, not disease-model results.

## Current checkpoint

- M1: All 46 GEO libraries mapped. The pinned author downstream filtered table exactly matches the final H5AD's 37 libraries, 30 donors and labels. Retained-cell ingestion joins all 550 B17C2L cells before capping and excludes 102 raw-only cells. New NeMO diagnostics identify exactly 3,731 RNA `Unk` rows and a 113,801-cell candidate, but do not certify its QC. Author methods and metadata document UCLA/NIH sources versus HDBR: no overlap evidence, not independently certified specimen identity. Full raw-barcode coverage and accepted per-cell QC remain pending.
- M2: Conversion and support checks implemented and tested. NeMO's canonical PCW 13–20 sensitivity has 8 control and 10 trisomy-21 donors before new QC exclusions.
- M3: Both MEX layouts tested; real pilot now selects 256 from the 550 author-retained cells. NeMO count packages remain unaudited. September 9 public manifest/API/Open-bag requests succeeded; the earlier transport blocker is cleared for those endpoints. Release metadata checksum matches locally, but QC/common-feature acceptance does not follow from access.
- M4: Exact-region compatibility gate implemented. Inspected B17C2L/B10C1Q peak lists have zero exactly shared intervals. Common-count input or budgeted recount is needed before comparable training; approximation remains deferred.
- M5: Immutable software benchmark settings and strict paired uncertainty implemented. The real scientific protocol and gate-bound acceptance remain pending.
- M6: Donor-aware training and bounded paired-array adapter implemented. Six neural families and majority control ran on 25 synthetic outer folds. Biological controls and accepted real-data orchestration remain pending.
- M7: Genuine cross-attention and matched token-concat control implemented; gradients, direction, axes, and ablations tested. Real internal comparison remains pending.
- M8: Final all-development refit, numeric scaler/state dictionaries, expected manifest/weight hashes and one-shot scoring implemented and tested on synthetic data. Epochs are ceil(median internal best epochs), frozen before final fits. Synthetic validation.csv produced; registry corrected to GSE280175 5+5 and NeMO candidate 13+13. Accepted real orchestration and real external evidence remain pending.
- User now reports professor approval; [scoped attestation](../plan/real_data_attestation_2026-09-08.json) records this without inventing the professor's approval date. Historical global policy remains unchanged. Original RNA real-analysis execution uses the existing per-run attestation; real paired external predictive evaluation has not run.

## Next decisions required for real execution

1. Use the recorded user-reported attestation only for the existing public-data plans and their gates. Independent documentation/date can be added later; do not invent it or let approval bypass scientific acceptance.
2. Accept a specific common-region ATAC count source, or approve a separately bounded fragment-recount task. The inspected B17C2L/B10C1Q raw libraries have zero exact common peaks; zero-filling cannot fix this. Published processed objects remain uninspected, not proven unusable. Public fragment packages total roughly 43 GiB compressed before working files. Before any larger proposal, record current free disk in GiB with a timestamp and estimate compressed, decoded, intermediate and output working sets plus safety headroom. Do not rely on stale GB/GiB figures, start a full recount, or require different hardware without that estimate.
3. Resolve the remaining NeMO QC/release semantics. RNA `Unk` removal matches the published count exactly, but current retained-candidate QC columns still include 1,751 ATAC counts <=100 and six mitochondrial percentages >=5; original-stage semantics are unverified. UCLA/NIH versus HDBR provenance is now documented. No author contacted or controlled access requested.
4. With those inputs, freeze real normalization/covariate/chr21 and sensitivity rules, connect biological controls and accepted real inputs to the existing fold/refit/scoring code, then execute M6–M8.

The original [external RNA effect-replication study](../docs/EXTERNAL_RNA_REPLICATION_PLAN.md)
is now implemented and executed on real data: all four comparisons and the headline
are inconclusive, with identical results across three local runs and 608 passing
tests. [Final evidence](../docs/EXTERNAL_RNA_REPLICATION_RESULTS_2026-09-08.md) is saved.
Original RNA Tasks 1–5 are complete: fresh free-CPU Colab archive retrieved, hashes
verified and results exactly matched locally (2026-09-09). Fang approval and
notebook upload/free CPU use are explicitly confirmed by the user; do not ask
again for this study. This neural
software does not substitute for the RNA study, nor does RNA evidence close M1–M8.

## M1: Freeze source release, QC, and specimen mapping

Produce an auditable manifest for the exact GSE305146 and NeMO releases, with distinct published/downloaded/retained counts.

**Acceptance criteria:**

- [ ] URLs, hashes, library-qualified barcodes, donor/condition mappings, repeat libraries, and exclusions are recorded; GSE305146's 46 libraries are reconciled with its published 30-donor cohort.
- [x] NeMO's 117,532 metadata rows versus 113,801 published nuclei have an exact annotation-based candidate reconciliation in the audit; upstream QC remains unverified and confirmatory evaluation blocked.
- [x] Specimen/provider/accession evidence is checked across studies, with overlap and unresolved provenance recorded: author methods and metadata document UCLA/NIH versus HDBR, with no overlap evidence but no certified identity crosswalk.

**Verification:** `.venv-p22/bin/python -m pytest -q tests/test_multiome.py -k manifest`; manually reconcile manifest tables with pinned sources. Test conflicting donor labels and duplicate library/barcode keys.

**Dependencies:** None. **Scope:** Small.
**Likely files:** `src/p22/data/multiome.py`, `tests/test_multiome.py`.

## M2: Normalize developmental ages

Make age filtering use documented units rather than column names or matching numbers.

**Acceptance criteria:**

- [x] Preserve raw age/unit/source and conversion rule; convert verified obstetric GW to approximate PCW by subtracting two, leaving PCW unchanged.
- [x] Ambiguous units and missing ages remain explicit; no implicit conversion from `gw` alone.
- [x] PCW 13–20 sensitivity maps to GW 15–22 only for verified obstetric ages, and reports age-eligible donors per condition and insufficient support. Final QC eligibility remains a separate gate.

**Verification:** `.venv-p22/bin/python -m pytest -q tests/test_multiome.py -k age`; check boundary, unchanged-PCW, and unknown-unit cases.

**Dependencies:** M1 metadata schema. **Scope:** Small.
**Likely files:** `src/p22/data/multiome.py`, `tests/test_multiome.py`.

## Checkpoint A: Cohort contract

- [ ] M1–M2 evidence reviewed; unresolved items have explicit status and downstream restrictions. No predictive results used to choose exclusions or age limits.

## M3: Run a bounded paired sparse ingestion pilot

Load combined 10x MEX and separate RNA/ATAC MEX through one narrow adapter. Begin with a small training-cohort slice and metadata; inspect external files only for predeclared integrity/compatibility checks.

**Acceptance criteria:**

- [ ] Hashes, count semantics, dimensions, unique ordered barcodes, and metadata joins agree; mismatches fail with a specific error. Archive paths are validated before extraction.
- [x] Preserve sparse arrays until capped cell/feature selection; reuse `sample_nested_capped_cells` for matched 64/128/256-cell comparisons where possible. Report any donor below a cap. Verified on fixtures and one retained-cell public pilot, not the full external atlas.
- [x] Emit an ingestion report with source/QC status, pairing counts, disk, memory, and runtime using `measure_stage`; no full dense atlas conversion or automatic large fragment download.

**Verification:** `.venv-p22/bin/python -m pytest -q tests/test_multiome.py`; run the pilot with explicit manifest, cell cap, output directory, and byte budget, and record the exact command. Confirm both layouts on tiny fixtures and one bounded real training sample.

**Dependencies:** M1–M2 schema; diagnostics may run while evidence remains unresolved. **Scope:** Medium.
**Likely files:** `src/p22/data/multiome.py`, `tests/test_multiome.py`, `scripts/audit_multiome.py`, `src/p22/data/resources.py` (only if reporting needs extension).

## M4: Establish comparable ATAC features

Determine whether published counts support a common measurement space before promising fragment-free modeling.

**Acceptance criteria:**

- [ ] Check peak/count compatibility across training libraries and cohorts, including insertion versus fragment counts, feature provenance, coverage masks, and unmeasured versus true-zero entries.
- [ ] Accept common measured regions or exact recounting on frozen regions for confirmatory use. Label peak-to-gene sums `peak_derived_gene_score`; verify hand-calculated examples and training-only approximation error where a reference exists.
- [ ] Freeze annotation, region/overlap rules, numerical approximation limits, and feature order before validation outcomes. Emit `PASS`, `INCONCLUSIVE`, or `NEEDS_RECOUNT` for exact-region checks; reserve `EXPLORATORY_ONLY` for a future approximation path. Missing evidence cannot silently pass. Recount requirements include a separate measured resource estimate.

**Verification:** `.venv-p22/bin/python -m pytest -q tests/test_atac_features.py`; demonstrate that an unmeasured region is not silently zero-filled and overlapping peaks do not imply exact counts on a new region. Review the compatibility artifact without external prediction metrics.

**Dependencies:** M3. **Scope:** Small for compatibility/approximation; any required fragment recount is a separate bounded task defined from this result.
**Likely files:** `src/p22/data/atac_features.py`, `tests/test_atac_features.py`.

## Checkpoint B: Input feasibility

- [ ] Cohort/QC evidence and measured resources permit the intended run. Confirmatory work requires M4 `PASS`; an approximation-only pilot remains exploratory. Record any recount work before proceeding.

## M5: Freeze the donor-level experiment

Turn the proposed research question into a versioned configuration before fitting or external predictions.

Eligibility clarification: after QC, verify both-class support in every planned
outer/inner donor partition. Two donors per class cannot satisfy the specified
five-fold protocol. The 13+13 external count below informs the practical margin;
it is not a universal development-cohort minimum or a power guarantee.

**Acceptance criteria:**

- [ ] Freeze cross-attention-minus-concat external donor balanced accuracy as the primary contrast, the complete baseline list, small-model/token budget, learning settings, seed schedule, primary 256-cell cap, threshold 0.5, and 64/128/age sensitivities.
- [ ] Reuse `group_splits.py` and split validators for five repeated five-fold internal evaluation, with inner donor validation for selection. Specify final all-development-data refitting using hyperparameters and epoch counts selected internally; record one final artifact per model before external scoring.
- [ ] Freeze paired donor uncertainty (1,000 resamples, seed 22), the count-derived practical margin (0.08 at 13+13), failed-resample handling, and no endpoint switching. Reuse `statistics.donor_bootstrap` to resample donor indices shared by both models, with a paired-delta metric; do not subtract independently bootstrapped intervals. Define all cell-type/covariate treatments and any chromosome-21 masking before results.

**Verification:** `.venv-p22/bin/python -m pytest -q tests/test_multiome_protocol.py`; validate both-class support, donor disjointness, immutable fingerprints, margin calculation, and rejection of unresolved required gates. Check paired deltas against hand-calculated cases and existing `paired_donor_delta`, including invalid-resample counts. Confirm 30/26 are donor counts, not cell-based power claims.

**Dependencies:** M1–M4 accepted for the selected analysis mode. **Scope:** Medium.
**Likely files:** new `configs/paired_multiome_real.json`, `src/p22/eval/multiome_protocol.py`, `tests/test_multiome_protocol.py`. Preserve the existing `configs/paired_multiome.json` synthetic benchmark unchanged.

## M6: Run donor-aware baseline models

Connect accepted real paired inputs to the existing models and training loop while retaining the separate synthetic runner's safeguards.

**Acceptance criteria:**

- [ ] Reuse preprocessing fingerprints, `BaselineMLP`, `ConcatFusionModel`, `GatedFusionModel`, and existing cheap controls; fit transforms only inside training partitions and give donors equal training weight.
- [x] Add optional donor-aggregated validation scoring to `train_model`, preserving existing behavior for callers without donor IDs. Checkpoint selection and fold metrics use the declared donor aggregation; verified on synthetic donor fixtures.
- [ ] A small internal run reports all eligible baseline families on identical donor splits/cell caps, with parameters, runtime, and negative/inconclusive outcomes; NeMO never selects checkpoints or hyperparameters.

**Verification:** `.venv-p22/bin/python -m pytest -q tests/test_multiome_runner.py tests/test_training.py`; verify donor-balanced selection can differ from cell-level selection, and that changing held-out data cannot refit transforms. Run one bounded real internal fold and record the command/config hash.

**Dependencies:** M5. **Scope:** Medium.
**Likely files:** `src/p22/eval/multiome_runner.py`, `tests/test_multiome_runner.py`, `src/p22/training/loop.py`, `tests/test_training.py`.

### M6a: Expose real-data readiness without fitting

**Description:** Add a separate real-data entrypoint that defaults to dry-run.
The existing synthetic-only entrypoint remains unchanged.

**Acceptance criteria:**

- [ ] Validate M5 protocol and input-evidence fingerprints for the requested stage;
  print missing gates and the exact next action before opening training matrices.
- [ ] Dry-run never fits, scores, downloads or changes approval state. An explicit
  execution request with unresolved required gates is refused, with a saved reason.

**Verification:** new `tests/test_real_multiome_cli.py` covers default no-op,
tampered hashes, unresolved QC/count contracts and synthetic-entrypoint preservation;
run existing professor/gate tests, `make lint`, `make test-fast`.
**Dependencies:** F3 evidence schema; fixture development can precede acceptance,
but real execution additionally requires M5 and applicable accepted M1–M4 inputs.
**Files likely touched:** new `scripts/run_real_multiome.py`,
new `tests/test_real_multiome_cli.py`, `docs/PAIRED_MULTIOME_TRAINING.md`.
**Estimated scope:** Medium, three files.

### M6b: Implement the frozen real transforms and biological controls

**Description:** Connect M5's chosen RNA/ATAC normalization and required controls
to the bounded array adapter. Standard scaling of raw counts is not an implicit
scientific normalization; reuse existing control implementations where applicable.

**Acceptance criteria:**

- [ ] Fit each learned transform/feature selection on training donors only;
  preserve exact measured feature order, sparse bounds and matched cell caps.
- [ ] Required RNA, ATAC, dosage, QC/covariate and matched-fusion controls use the
  same declared splits and report inapplicability rather than invented measurements.

**Verification:** hand-calculated transform fixtures, held-out perturbation tests,
donor-weight checks and real-control applicability tests; existing multiome/real-
runner tests plus `make lint` and `make test-fast`.
**Dependencies:** accepted M5, M6a.
**Files likely touched:** `src/p22/eval/multiome_runner.py`,
`src/p22/eval/real_runner.py`, `tests/test_multiome_runner.py`, `tests/test_real_runner.py`.
**Estimated scope:** Medium, at most four files.

### M6c: Run one accepted internal fold before expanding

**Description:** Wire the real entrypoint to existing donor-split and model helpers;
run a single fixed internal fold as a bounded correctness/resource pilot.

**Acceptance criteria:**

- [ ] An explicit stage/config selects one fixed donor-disjoint fold with the
  required class support, models and controls. NeMO does not fit transforms, select
  parameters or receive predictions; a one-library sample is not donor validation.
- [ ] Save per-donor predictions, split/config/input hashes and resource measures;
  label pilot scores exploratory and never use them to redesign the test endpoint.
- [ ] Expansion to M7's full frozen comparison requires pilot integrity/resource
  review. M8 external scoring is separate and requires accepted external QC,
  features, protocol and frozen final artifacts; no automatic execution chain.

**Verification:** new real-CLI fixtures plus existing split/training/final-artifact
tests; `make lint`, `make test-fast`, then one measured real fold only after gates pass.
**Dependencies:** M6b and accepted real inputs; a development-only mode requires
separate protocol review and cannot mark combined-cohort gates complete.
**Files likely touched:** `scripts/run_real_multiome.py`,
`tests/test_real_multiome_cli.py`, `src/p22/eval/multiome_runner.py`,
`tests/test_multiome_runner.py`, `docs/PAIRED_MULTIOME_TRAINING.md`.
**Estimated scope:** Medium, at most five files.

## Checkpoint C: Donor-aware baseline evidence

- [ ] Training/validation/test donor isolation and baseline outputs verified. Existing dosage ceiling retained in interpretation; training completion is not scientific success.

## M7: Implement the explicit cross-attention comparison

Add a small attention model as a distinct family and compare it with concatenation using equivalent token encoders and selection budgets.

**Acceptance criteria:**

- [ ] Implement the frozen query/key/value direction, tokenization, dimensions, heads, pooling, and output contract with installed PyTorch. More than one key/value token is required; gating remains separately named.
- [x] Outputs/gradients are finite, both modalities affect the computation on controlled examples, and modality ablations work; latent token weights are not presented as regulatory mechanisms.
- [ ] Integrate with the real runner; report parameter counts and a concatenation control with matched token encoders, feature budgets, and selection effort. Select architecture/checkpoints using development donors only.

**Verification:** `.venv-p22/bin/python -m pytest -q tests/test_cross_attention.py tests/test_multiome_runner.py`; inspect token axes and an internal comparison with matching inputs and recorded budgets.

**Dependencies:** M5–M6. **Scope:** Medium.
**Likely files:** `src/p22/models/cross_attention.py`, `tests/test_cross_attention.py`, `src/p22/eval/multiome_runner.py`, `tests/test_multiome_runner.py`.

## M8: Evaluate frozen models on the accepted external cohort

Apply the frozen model/feature contracts to NeMO and write the donor-level comparison with all limitations visible.

**Acceptance criteria:**

- [x] Software-only precursor: serialize all-development refits and frozen scaler parameters; reject tampering, changed feature order, overlapping donors/cells and repeat scoring. Verify by reloading and scoring a separate synthetic draw, never as biological validation.
- [ ] Require reconciled release/QC, documented specimen provenance, canonical age units, accepted feature semantics, and frozen model/transform hashes. Structural audit history is disclosed; external values never refit transforms or choose models.
- [ ] Evaluate the prespecified model set in one locked batch, retain one prediction per donor/model, and require identical unique donor sets and consistent labels before paired comparison. Report primary delta/interval, actual class counts, support-limited sensitivities, and all controls. The entire accepted external set remains outside fitting.
- [ ] Update the validation resource registry to name the actual candidate/status and the 5+5 RNA cohort correctly; produce `validation.csv` and a compact report. Known overlap, unresolved compatibility, or failed QC produces a bounded pending/inconclusive result instead of an independent multimodal success claim.

**Verification:** `.venv-p22/bin/python -m pytest -q tests/test_multiome_runner.py tests/test_marker_validation.py tests/test_professor_gates.py`; verify artifact hashes, mismatched donor/label rejection, and that repeat evaluation cannot become a model-selection loop. Run `make lint` and `make test-fast` after code integration, then review the real report against the frozen protocol.

**Dependencies:** M7 and all confirmatory gates. **Scope:** Medium.
**Likely files:** `src/p22/eval/multiome_runner.py`, `tests/test_multiome_runner.py`, `src/p22/eval/validation.py`, `tests/test_marker_validation.py`.

## Checkpoint D: Completed evidence package

- [ ] Inputs, exclusions, feature/protocol/model hashes, focused tests, baseline comparisons, and external uncertainty are reviewable. Claims distinguish measured availability, exploratory approximations, predictive comparisons, and biological evidence.

## Results-execution continuation — 2026-09-21

New execution authority for the existing approved study (public data only). Historical
records preserved; see `configs/results_execution_amendment_2026-09-21.json` and
`MOM/2026-09-21/GNHF_P22_RESULTS_AND_PROFESSOR_HANDOFF.md`.

- [x] R1: bounded development fragment barcode/index header validation — `PASS`.
  Open bgzf TSV, `<library>_<barcode>-1` barcodes all join the 248,998-cell H5AD
  index on the sampled block, `.tbi` is standard tabix. Evidence:
  `reports/generated/atac_fragment_join_20260921/dev_fragment_join.json`;
  `docs/ATAC_FRAGMENT_JOIN_VALIDATION_2026-09-21.md`.
- [x] R2a: remote indexed region-query mechanism on the development fragment —
  `PASS`. Whole-contig indexed query (`GL000009.2:0-300000` → 13,270 rows) matches
  an independent bounded-prefix decode; six real 100 kb regions return 0 unknown
  barcodes and a real 6 × 248,998 sparse counts matrix. No whole-asset read.
  Evidence: `docs/ATAC_REGION_QUERY_VALIDATION_2026-09-21.md`,
  `docs/atac_region_query_validation_2026-09-21.json`,
  `reports/generated/atac_region_query_20260921/`. Code:
  `scripts/query_fragment_regions.py`, `tests/test_query_fragment_regions.py`.
- [x] R2b: freeze a training-fold-only region set and assemble the development ATAC
  matrix — `PASS`. Exact-interval union of the 28 training libraries of pilot fold
  (repeat 0, fold 0; 24 train / 6 test donors) has 1,440,187 intervals; top-256 by
  training-library prevalence frozen. Real matrix 256 × 248,998, nnz 4,879,858,
  256/256 complete barcode joins, 1.779 GB fetched, no whole-asset read. Evidence:
  `docs/DEVELOPMENT_PAIRED_INPUT_AND_PILOT_2026-09-21.md`,
  `docs/atac_development_matrix_2026-09-21.json`,
  `configs/development_region_set_fold0_2026-09-21.{json,bed}`. Code:
  `scripts/freeze_development_region_set.py`, `scripts/quantify_development_atac.py`,
  matching tests.
- [x] R2c: real paired RNA+ATAC pilot — `EXECUTED (honest null)`. 7,680 cells
  (256/donor, 30 donors), real RNA (35,477 genes) + real ATAC (256 regions),
  one donor-isolated fold, six neural families. Cross-attention minus token-concat
  donor balanced accuracy 0.0 (interval [0,0]); no advantage. Pilot only, not a
  final estimate. Evidence: `docs/real_paired_pilot_2026-09-21.json`,
  `reports/generated/real_paired_pilot_20260921/`. Code:
  `scripts/run_real_paired_pilot.py`.
- [x] R4a: held-out faithfulness + initialization sensitivity on the real paired
  pilot — `EXECUTED`. All seven interventions per two-view family scored at the
  donor level: RNA-view clamp/ablate drop donor balanced accuracy 0.625 → 0.5/0.0,
  ATAC-view interventions leave it at 0.625, uniform route NOT_APPLICABLE for
  non-gated families. Init-seed sensitivity: cross-attention and token-concat both
  0.625 at seeds 0/1/2 (spread 0.0); primary delta 0.0 at every seed. Pilot only.
  Evidence: `docs/PAIRED_FAITHFULNESS_AND_SEED_2026-09-21.md`,
  `docs/real_paired_faithfulness_2026-09-21.json`,
  `reports/generated/real_paired_faithfulness_20260921/`. Code:
  `src/p22/eval/paired_faithfulness.py`, `scripts/run_real_paired_faithfulness.py`,
  `tests/test_paired_faithfulness.py`.
- [x] R4b: frozen internal comparison — `EXECUTED (honest null)`. Per-fold
  training-only top-256 region sets for all 25 outer folds (union 480 regions,
  `union_sha256 29ab6739…3f9e`), quantified once into a real 480 × 248,998 matrix
  (nnz 9,513,875, 480/480 complete joins, 3.295 GB fetched). Frozen 5 × 5 donor
  split tests all 30 donors per repeat. Primary cross-attention minus token-concat
  donor balanced accuracy **+0.0333** (95% donor-bootstrap interval
  **[-0.0133, 0.0806]**), margin 0.07, advantage false; interval no longer
  degenerate. Evidence: `docs/repeated_internal_comparison_2026-09-21.json`,
  `docs/REPEATED_INTERNAL_COMPARISON_2026-09-21.md`,
  `configs/final_internal_comparison_2026-09-21.json`,
  `configs/repeated_region_sets_2026-09-21.{json}`,
  `reports/generated/real_paired_comparison_20260921/`. Code:
  `scripts/freeze_repeated_region_sets.py`, `src/p22/eval/repeated_comparison.py`,
  `scripts/run_real_paired_comparison.py`, matching tests.
- [x] R4c: repeat the held-out faithfulness interventions and initialization
  sensitivity on the frozen final folds — `EXECUTED`. All 25 folds, all seven
  interventions per two-view family scored at the donor level: RNA-view interventions
  dominate (cross-attention ablate_view_a mean drop 0.103; concat 0.145) while
  ATAC-view interventions are near zero (cross-attention ablate_view_b -0.001);
  within-donor permutation ~0 (expected for per-cell models); uniform route
  NOT_APPLICABLE for non-gated families, measured for gated (mean drop 0.001). Init
  seeds 0/1/2 with donor splits held fixed: mean primary delta +0.0367/-0.0153/-0.0060
  (spread 0.052), so the null is not an init-seed artifact. No new network. Evidence:
  `docs/PAIRED_FAITHFULNESS_FROZEN_FOLDS_2026-09-21.md`,
  `docs/real_paired_faithfulness_frozen_2026-09-21.json`,
  `reports/generated/real_paired_faithfulness_frozen_20260921/`. Code:
  `src/p22/eval/paired_faithfulness.py` (`aggregate_interventions`),
  `scripts/run_real_paired_faithfulness_frozen.py`, `tests/test_paired_faithfulness.py`.
- [x] R5a: normalization sensitivity on the frozen folds — `EXECUTED (null)`. Raw
  standard scaler exactly reproduces the frozen primary (+0.0333, interval
  [-0.0133, +0.0806]); log1p + standard scaler also +0.0333 (interval
  [-0.0050, +0.0800]); advantage false in both. Raw-count standard scaling is
  prospectively frozen as the operative normalization; the primary estimate is
  unchanged. No new network. Evidence:
  `docs/NORMALIZATION_SENSITIVITY_2026-09-21.md`,
  `docs/real_paired_normalization_sensitivity_2026-09-21.json`,
  `reports/generated/real_paired_normalization_20260921/`. Code:
  `scripts/run_real_paired_normalization_sensitivity.py`,
  `tests/test_real_paired_normalization.py`.
- [ ] R5b: external route — `BLOCKED (evidenced)`. Direct HTTPS to
  `data.nemoarchive.org`/`assets.nemoarchive.org` fails TLS on three attempts; the
  read proxy times out; per-file `Access=embargo` conflicts with collection
  `access=open`; no cross-cohort common measured feature set; controlled raw data
  needs NIMH Data Archive approval (not authorized). No external outcome inspected.
  Smallest unblock: a direct (non-mirror) network path or provider fix plus a
  published common measured feature set or an embargo resolution.
- [ ] R5c: finalize the professor-facing notebook and handoff with the real
  execution status (remaining in-scope work).

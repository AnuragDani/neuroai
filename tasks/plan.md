# Paired DS multiome development plan

Updated: 2026-09-14 (PDT; planning revision only). F1–F3 implemented and the bounded audit completed;
final decision review is recorded in the audit guide. No further execution is
authorized by this completion record. Status: retained-cell ingestion, donor-aware networks, final
saved models/scalers and one-shot scoring implemented. 150 synthetic internal fits
plus six final refits verified. Real-data scientific gates remain pending.
Conditional E0–E4 follow-up: E0 and E1 tiny-reader proof now complete after the
approved local continuation. The pinned ARM64 R image was acquired/imported;
nine live fixture/control checks passed. E2's offline source-contract pass ended
SOURCE_UNRESOLVED; E3 remains unexecuted. No real dataset payload was acquired.
The earlier control-stop record remains historical. Current evidence and remaining
gate: [reader completion](../reports/generated/r_reader_completion_20260912/REVIEW.md).

Current next proposal: one metadata-only HEAD of the documented candidate object,
then a target-compatible reader/resource contract, then one conditional inspection.
The September 12 listing-GET proposal is superseded, not executed. See
[review amendment](#review-amendment--2026-09-14); real-object execution gates remain closed.

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

### Capture-core completion and launcher tasks — 2026-09-14

Commit `11a4b7b` adds the offline-tested capture core and its tests. Supervisor
verification recorded 45 focused tests, 836 full-suite tests and Ruff passing;
these are historical results, not tests rerun for this plan edit.
[Review and durable code bundle](/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/lmstudio_head_capture_split_20260914.mOJ8o9/REVIEW.md).
The core reuses the existing parser, has no default live transport/CLI, and
does not prove operating-system containment. E2-M remains open.

The immediate next task is **E2-M1, read-only runtime/control feasibility**.
The next *live* proposal remains the existing single HEAD, not a new request:

1. E2-M1: inspect already-available runtime/control evidence; stop on missing
   hard-limit support or authority before building a launcher around assumptions.
2. E2-M2: bind the reviewed core to that proven control design; test refusals
   offline. Reuse existing helpers where inspection justifies it.
3. E2-M3: verify bounded adversarial process-tree controls, then independently
   review code, resource evidence and the owner's exact-scope approval.
4. E2-M4: only then execute the existing one-HEAD scope. Success permits E2-R
   offline planning only; E2-C/E3 and scientific gates remain unchanged.

Unknowns: cached compatible Python/TLS runtime, effective non-root isolation,
hard aggregate memory/no-swap enforcement, watchdog coverage and safe test
allocations. Flag presence, sampled RSS or killing after a detected memory
breach do not prove the frozen limits. Python signals cannot replace the hard
watchdog. Missing proof yields a concrete resource/authority blocker without
changing the source contract's `SOURCE_UNRESOLVED` status.
`body_bytes=0` means application reads, not TLS/OS buffering; stronger required
semantics need review. This plan grants no execution, installation or new budget.

### Conditional follow-up paths — planning only

#### Review amendment — 2026-09-14

**Scope:** revise E2/E3 planning, not execute it. Preserve completed E1, RNA and
F1–F3 evidence and their original ledgers. The prior critique and locally checked
model opinion justify a narrower next action, not an automatic gate promotion.

1. **E2-M, source metadata:** propose one HEAD of the candidate payload URL in
   the [source contract](../configs/development_object_source_contract.json).
   Directory plus the recorded filename supplies a candidate, not a fresh source
   observation. HEAD can provide size/validators without an object-body read;
   a second directory index cannot guarantee exact size. Record missing headers
   as unknown, and hash the saved header record, not an undownloaded payload.
2. **E2-R, target reader and resources:** after usable metadata, make one offline
   proposal (30 minutes; zero network/install/object bytes). Pin compatible
   workspace/class support, dependency assets if needed, and separate acquisition,
   decoded, retained/temporary disk, process-tree memory and wall ceilings. Use a
   fresh host snapshot and evidence-backed estimates; compressed size is not RAM.
   The historical 4 GiB job/8,092 MiB VM limits do not become a real-load allowance.
   Unknown requirements remain unknown; an indefensible contract stops
   RESOURCE_UNRESOLVED. No new setup budget or resource-setting change is granted.
3. **E3, conditional inspection:** only after the resulting exact contract is
   reviewed/authorized and a tiny applicable workspace/class fixture passes,
   acquire/load one target and record the required sparse counts/metadata gates.
   E4 then delivers an input decision or a concrete blocker and one next action.
   No speculative 64 KiB range probe, automatic retry, alternate object or fitting.

E1 proved `saveRDS/readRDS` of a tiny `.rds` list, not `save/load` of a real `.rda`.
Before E3, prove the applicable `.rda` and Seurat/ChromatinAssay extraction path
(or a demonstrated equivalent narrow reader) on a <=1 MiB fixture, preserving
sparse counts/IDs/metadata and refusing unexpected classes. Cost any missing
packages before acquisition; do not assume all Seurat dependencies are necessary,
already installed, or fit the remaining setup budget. Generic E1 remains complete.

**Scientific rules unchanged:** cluster-based peaks are not proven label-independent
by their name; all-donor feature discovery is not train-fold-only selection.
Presence plus disclosure does not meet the existing gate. A different exploratory
representation needs a prospective protocol decision, not a silent relaxation.
After QC, check donor/class support for five repeated five-fold evaluation and
inner validation; two donors per class do not suffice for that protocol. The
13+13 count informs the external practical margin, not a development minimum.
Development acceptance cannot substitute for NeMO QC/common-region acceptance.

Verification: source-linked decisions and matching E2-M/E2-R tasks in `todo.md`;
no scientific checkbox closes on metadata, a fixture, model agreement or an OOM.
Technical basis: [HEAD](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.2),
[optional Content-Length](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.6),
and [R workspace loading](https://stat.ethz.ch/R-manual/R-devel/library/base/html/load.html).

#### Local-resource amendment — 2026-09-12

**Execution continuation:** the subsequent “keep going and complete the plan”
instruction authorizes implementing and running the already-pinned local reader
acquisition, not another setup-only handoff. Retain the 814-second prior ledger;
remaining active acquisition/import/fixture time is 746 seconds. Offline coding,
tests and review are tracked separately, not represented as installer runtime.
The fixed acquisition script has a 480-second deadline, no retries and checks the
reviewed proposal hash before network access. Its stricter raw-layer ceiling
reserves three copies plus 256 MiB within 6 GiB before Docker import; no host
archive extraction. Import is local/offline, at most 90 seconds; fixture/control
tests share the remaining time. Only UUID-owned test containers may be removed.
No dataset request, E3 execution, package updater, user-container change or training
is authorized by this runtime step. E2 remains an offline next contract.

After the control stop, the user approved the setup proposal and said “You can
use any local resources that you would like”. This authorizes one local setup
continuation, including starting the already-installed Docker Desktop. It does
not authorize paid compute, dataset/fragment downloads, another Colab attempt,
outreach, weakened scientific gates, push or merge. Archived attempts stay intact.

Use the installed Docker Desktop 4.73.0 / CLI 29.4.3; existing settings are
8,092 MiB VM RAM, 1,024 MiB swap, 16 CPUs and a 61,035 MiB logical disk ceiling.
The existing sparse disk occupies 17,028,120,576 bytes; it is not a new download.
Current local approval allows this pre-existing host-runtime allocation outside
the earlier 4 GiB reader-job cap; do not mislabel host observations as hard
process-tree enforcement. Do not change Docker settings or delete cached work.
Maintain at least 10 GiB host disk headroom; check before/after startup and work.

1. Start the installed runtime once (45-second command timeout); inspect local
   endpoint, cached images and running containers. No pull, update or build.
2. If a compatible cached reader exists, pin its immutable image ID and installed
   package versions, then implement/test the tiny sparse fixture. Keep its job
   at 4 GiB memory with no swap, bounded temporary writes and timeout; no network
   or host data mounts. Prove descendant termination before claiming controls.
3. If no compatible image exists, freeze one exact dependency-acquisition proposal
   and stop before an unmetered pull/install. Keep original 2 GiB fetched/4 GiB
   decoded dependency limits unless explicitly revised; do not invent asset sizes.

This continuation has a 20-minute active setup ceiling, added to the previous
360 seconds (maximum cumulative 1,560 seconds), not a reset. Record fresh outputs
under `reports/generated/local_reader_setup_20260912/`. Runtime startup failure,
unexpected agreement/access prompt or insufficient headroom yields a precise
blocker. E2/E3 require their own exact object contract as before.

Native reference: [Docker Desktop start](https://docs.docker.com/reference/cli/docker/desktop/start/)
and [container memory/swap controls](https://docs.docker.com/engine/containers/resource_constraints/).

**Result:** local Docker is available; selected R image config ID is not cached.
The [acquisition proposal](../configs/local_r_reader_acquisition.json) pins six
ARM64 layers totaling 763,355,676 declared compressed bytes. Expansion remains
unknown; the required next implementation is bounded acquisition/decode/import,
then the existing E1 fixture task. This proposal is not an executable installer.
Local setup consumed 454 conservative seconds, cumulative 814, leaving 746 under
this amendment. [Evidence and ledger](../reports/generated/local_reader_setup_20260912/SETUP.md)
preserve the earlier failed A/B attempts. No repeated approval for local resources
is needed; applicable scientific/data-acquisition gates and technical bounds remain.

This addition originally planned alternatives after completed F1–F3. The later
user instruction approved bounded execution, not E3's still-missing exact contract.
The heading remains the original contract anchor; current status is recorded above.
The saved F2d/F3 records and September 12 delivery remain immutable. Do not change
their single next action, repeat the source GET/audit, or turn a fixture result
into an accepted scientific input. New work uses new output directories and
evidence records. The original no-install cycle is closed, not silently extended.

**Objective:** obtain one auditable development input with paired raw RNA and
measured common-region ATAC counts, or identify the specific requirement that
cannot be met within the permitted routes. This supports a later donor-held-out
comparison; it neither guarantees a positive effect nor completes external
validation. Distinguish runtime failure, resource failure, missing assay, and
missing scientific provenance: each calls for a different response.

#### Route selection

Choose one active route at a time; alternatives are not an instruction to try
everything. E0–E4 in [todo.md](todo.md#conditional-follow-up-queue--e0e4)
define the bounded tasks and checkpoints.

| Path | Entry condition and reason | Evidence that closes this path | Failure / next choice |
|---|---|---|---|
| A — Local R reader, preferred | Current inventory lacks a compatible reader. Start with the selected 7.6G-listed development object as the future target; no object download in the reader step. | Pinned isolated runtime and tiny sparse-object round trip pass; counts, identifiers and metadata preserved. This proves only the tested fixture/classes. | Environment-specific install/control failure may justify B. Unsupported object class needs a compatible reader, not a larger machine. Scientific assay/QC failure cannot be cured by B. |
| B — Already-approved free-CPU environment | A fails for a documented local environment/resource reason, or E0 shows a usable pre-existing reader there. No new cloud account, paid tier or GPU request. | Same fixture and resource checks pass in that environment; returned records/hashes independently verify locally. | One attempt only; unavailable capacity or unenforceable limits stops. Do not cycle sessions or claim a runtime reset solved data semantics. |
| C — Documented sparse-count export | An exact provider-documented compatible export is supplied or located in newly pinned evidence. None is verified today. Prefer this over deserializing a large object if it answers the same question. | Raw paired counts, retained barcodes/donors, measured intervals/build/units and feature-selection provenance satisfy the same contract through existing MEX readers where possible. | Normalized values, embeddings, gene activity, inferred zeros or missing provenance do not qualify. No speculative adapter or open-ended search for an unnamed export. |
| D — Other already-listed processed object | The selected object is shown to lack the required assay or donor/population coverage, and evidence gives a reason the other object could supply it. Not a response to memory failure. | Separately approved inspection of `GSE305146_seur_integr_labelled_complete_dataset.rda.gz` (listing 8.7G) meets the same input contract. | At most one alternate object; no simultaneous full downloads. If contents/provenance still fail, record the exact missing artifact and consider E only as a proposal. |
| E — Recount feasibility proposal, last resort | Both named objects have evidence-backed dispositions (inspected or explicitly inaccessible/unresolved), and no documented usable export is available. | A narrowly scoped costing/protocol proposal states exact fragments, donors, frozen regions, count units, storage and authorization needed. A missing estimate remains unknown. | No fragment download or recount under this plan. If permitted data/resources cannot support it, stop with a scoped blocker; do not lower gates or replace the dataset automatically. |

A/B concern runtime location; C/D concern the data artifact. They are not
interchangeable solutions. The normal route is A, then inspection of
`GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz` after E2 approval.
B changes location only. A newly documented C can bypass R-specific work, but
not the resource, pairing, raw-count or provenance checks. D needs a new source
decision, and E stops at a proposal. The two rounded sizes and the unpublished
`peaks_by_cluster` checkpoint come from
[the saved source evidence](../docs/PAIRED_MULTIOME_REMAINING_EVIDENCE_2026-09-08.md),
not verified archive contents or current download-size measurements.

#### Limits, authority and stopping rules

- **E0 route preflight:** one offline review, at most 30 minutes, existing local
  records only; 0 network/installation/dataset bytes. Name the preferred route,
  fallback trigger, exact target, missing authority and next code slice. Stop with
  a source request if C has no exact documented artifact; do not invent its URL.
- **E1 reader attempts A/B:** at most one per environment and two total. Share
  the existing proposed ceiling across both attempts: 2 GiB cumulative fetched
  dependencies, 4 GiB cumulative decoded dependencies, 6 GiB peak additional
  working disk across retained attempt files, 4 GiB peak process-tree RSS and
  30 minutes total active setup/fixture time. Require at least 10 GiB available
  disk headroom on each chosen host and a fixture no larger than 1 MiB. Switching
  environments does not reset counters. Charge failed fetches and cold setup;
  a free-CPU queue/capacity failure ends that attempt, not a polling loop.
- Preflight exact dependency assets/versions, their transfer/expansion budget and
  control availability before installation. No unmetered installer fetches.
  Record process-tree use, not only the parent R process; the existing RNA
  supervisor handles one owned process and is not proof of installer-tree control.
  Use enforceable isolation where available; sampled RSS alone is not a hard
  ceiling. If controls cannot bound the job, record refusal rather than launch.
- E1 needs approval to expand dependency-installation scope. Existing free-CPU
  and scoped professor approvals stand; ask only for an uncovered action. Reader
  success authorizes neither an object download nor fitting. A synthetic fixture
  cannot establish the real object's classes, memory fit, assays or provenance.
- **E2 offline target/resource contract:** one proposal per selected object,
  at most 30 minutes. No HEAD/GET, archive reads or installation in the offline
  pass; E2-M is a separately authorized follow-up, not part of that pass. Freeze the
  exact identity and available integrity evidence; distinguish publisher checksums
  from locally measured hashes. Record fresh host resources only when executing
  that future task. Set numeric transfer, decoded, disk, process-tree RSS and wall
  ceilings, headroom, controls and cleanup/recovery rules for the proposed next
  read. Expected requirements may be unknown; permission ceilings may not.
  If no defensible contract is possible, mark `RESOURCE_UNRESOLVED` and stop.
  The next proposal is E2-M's one HEAD of the documented candidate payload:
  65,536 total response-header bytes, zero body/decoded-body reads, 15-second total
  deadline, no redirect/retry, 256 MiB process-tree memory/no swap, at most 1 MiB
  retained output and at least 10 GiB free disk. It needs separate scope approval.
  Missing/invalid positive Content-Length, non-200, redirect or a bound failure
  stops with the precise unresolved field. ETag/Last-Modified/Accept-Ranges are
  optional observations, not payload checksums or guaranteed future range support.
  HEAD cannot certify contents, decoded size, memory or QC. No Range GET follows.
- **E3 object inspection is conditional, not executable from this document.**
  It needs E2's separately reviewed and approved exact target/limits, plus tested
  applicable reader support. For C, test the existing supported export reader
  instead of requiring an R fixture. One target acquisition/inspection per
  approved contract, no automatic retry; D needs a fresh contract. Unknown full
  object fit is not an instruction to start downloading. No tar-prefix assumption
  for R serialization; even inspecting assay names may deserialize the object.
  E2-R must explicitly demonstrate applicable workspace/class support and bound
  the full load; compressed bytes below a RAM cap do not establish memory fit.
- After any failed attempt, record command/version hashes, cumulative resources,
  scope, stop reason and which new evidence could justify the next route. No
  unchanged retries, hidden budget reset or simultaneous A/B/C/D exploration.
  Run code tests offline before any authorized real attempt; code failure must
  be fixed separately, not described as proof that usable measurements are absent.
- E and external follow-up below are **proposal-only**: at most one 30-minute
  offline evidence/costing pass each. They confer no network or experiment budget.
  Full fragments, paid compute, author outreach, new datasets, synthetic
  substitution, peak projection and weakened scientific gates remain excluded.

#### Code deliverables and scientific handoff

The generic E1 fixture slice is complete. Next code work, if separately authorized,
is E2-M's narrow metadata request/check, then only the target-specific reader
extension justified by E2-R. Reuse installed libraries, existing sparse/count/
coordinate validation and output/refusal conventions; no general downloader or
orchestrator. E3 may instead reuse the existing MEX reader for a documented C.
New evidence must not overwrite F2d/F3 or relax the current F3 record validator.

**Implementation update:** the fixture slice now exists, with
`scripts/run_r_fixture.py` providing the separately reviewed native-control checks.
It reads no real object. `scripts/acquire_r_image.py` acquires only the fixed
reviewed R image; it is not a general downloader and was run once in a cached
Linux Python container after macOS refused RLIMIT_AS before any request. Do not
rerun acquisition: the verified archive and imported image are retained. Current
E2 outcome is [the source contract](../configs/development_object_source_contract.json),
not permission to load an unverified Seurat object or fit a model.

The future `development_object_inspection.json` must separate observed facts
from acceptance: object/classes and raw assay/layer; sparse dimensions; exact
cell/donor pairing and retained-release join; QC/count stage; age/class support;
specimen provenance; genome/coordinates; count units; measured-region coverage;
and donors/labels used in peak discovery. Cite source/code/asset hashes and
inspected scope for each PASS/FAIL/UNRESOLVED gate. Missing entries stay unresolved;
shared columns or all-donor peak calling cannot establish train-fold-only selection.

```text
E0: choose one route / exact target
  A local reader ──environment-only failure──> B free-CPU reader (shared E1 cap)
  C documented sparse export ────────────────> its existing-reader checks
        reader check → E2 approved target/budget → E3 bounded inspection
          missing assay/coverage → D alternate object → new E2 contract
          resource failure → stop; no automatic larger object/machine
          no permitted usable input → E recount proposal only → stop
E4: gate-by-gate decision + one justified next action → STOP
Later: accepted development input + M5 protocol → M6a/b → one M6c fold → M7
External: separate NeMO QC/common-region acceptance + frozen models → M8
```

Before M6c, all relevant development gates and M5's real normalization,
covariate/chr21 controls, feature construction, donor splits, comparison and
uncertainty rules must be frozen and reviewed. Pairing may be proven for a subset
without that subset having sufficient class/donor support. No post-hoc donor
deletion or endpoint change to manufacture a favorable result.
The excitatory-lineage object's population/age coverage must be assessed explicitly;
using a subset changes the estimand if it differs from the eventual M5 cohort.
Any such change needs prospective protocol review, not silent relabeling as the
original whole-cohort experiment.

**External lane:** keep NeMO reserved for external evaluation. Once development
feasibility makes this useful (or genuinely new exact external evidence arrives),
propose a separate bounded QC/barcode/count-stage and cross-cohort feature check
using the resolved declaration; do not rerun F2s or switch NeMO into development.
Current matching annotation totals remain QC-unverified. Internal results must be
labeled internal; they cannot satisfy M8's primary external contrast.

**Completion of this follow-up:** E4 accepts an evidence-backed input contract
or documents a precise, scoped blocker and the smallest permissible next action.
Do not promise a conclusive biological result. If all permitted routes stop,
deliver the negative feasibility result; no perpetual inspection loop. F1–F5,
M1–M8 checkboxes and original RNA conclusions retain their recorded meanings.

### Completed F1–F3 contract (historical)

The sections below through Review disposition preserve the completed cycle's
contract; they do not authorize new execution. Conditional routes above are a
separate proposal and do not rewrite the archived single-action decision.

### Completed-cycle objective and reasoning

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

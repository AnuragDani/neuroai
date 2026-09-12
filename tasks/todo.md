# Paired DS multiome implementation checklist

Updated: 2026-09-12. Specific next-cycle plan only; no new execution.
Retained-cell ingestion, neural training, final artifacts and
one-shot scoring verified. 150 synthetic internal fits plus six final refits.
Scientific acceptance gates remain open; the full research plan is not complete.

Contract: [dataset proposal](../docs/PAIRED_DS_MULTIOME_DATASET_OPTIONS.md). Overview: [plan.md](plan.md).

## Advancement queue — bounded planning revision 2026-09-12

These tasks extend the existing P22 work; they do not replace or complete M1–M8.
F4–F5 are complete in isolated head `46d7523`, not merged into this checkout.
[Durable RNA evidence](../reports/generated/rna_donor_influence_20260910_supervised/REVIEW.md)
records 68 valid omissions and 628 passing tests. Do not schedule those tasks again.
This revision changes only the plan. Next implementation requires approval of
[the frozen cycle contract](plan.md#frozen-scope-of-this-cycle).
Keep work in an isolated branch, preserve unrelated dirty files, and record one
verified slice per local commit. No push, merge or GNHF resume.

**Cycle endpoint:** F1 → F2d → F2s → F3 → reviewed decision and STOP. Result is
one guard commit, resolved or explicitly unresolved source identity, executable
proposal for the first unmet development-inspection prerequisite, and a specific
input decision. Only F2s uses network: one tiny official-bag read.
No NeMO payload probe or processed-object download occurs in this cycle.
F2d comes first and remains useful even when F2s fails. Internal model comparison
is a later development milestone; M5's planned external primary contrast stays intact.

**Before implementation:** verify the RNA recovery bundle and preserve its
accepted code/results. Use an isolated checkout containing `46d7523` plus these
current plan files, recording both source revisions. Fingerprint original dirty
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

- [ ] Contradictory coordinate-shaped peak IDs are rejected by the shared reader;
  valid ARC/MEX, opaque peak IDs and unmapped RNA retain their existing behavior.
- [ ] Source/dirty-file hashes are preserved; the change is present exactly once
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

- [ ] Manually assemble `development_object_feasibility.json` using the schema
  in `plan.md`: timestamp, commands/results, source hashes, runtime paths/versions,
  disk/memory evidence and resource unknowns. Check `R`, `Rscript`, `pyreadr`, and
  `rpy2`; distinguish availability from proven support for the serialized object
  classes and sparse assays. Generic-reader presence alone cannot pass this check.
- [ ] Freeze later inspection questions: object/classes, assay names, raw-count
  layer/slot, sparse dimensions, feature identifiers/coordinates and genome build,
  count units, donor/cell metadata, retained-cell semantics, and presence of a
  common measured ATAC matrix such as `peaks_by_cluster`, and donors/labels used
  for peak discovery. Shared columns do not establish training-only selection.
- [ ] Select one follow-up targeting the first unmet prerequisite: bounded reader
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

- [ ] One GET only; no HEAD, retry or redirect; 65,536 application-read body bytes,
  262,144 aggregate decoded bytes including headers, and one 15-second monotonic
  deadline covering DNS/connect/TLS/read. Require HTTP 200, disable HTTP decoding,
  and stop before parsing unless body is exactly 1,867 bytes with SHA256
  `4698c4b80d1e1bde7588b9b0979beb113df2ca24aebf54afbbac606eaf064d45`.
- [ ] Require one matching row in `fetch.txt` and `manifest-md5.txt`, joined by
  bag-relative payload path. URL/size come from the former, MD5 from the latter;
  match target filename, 1,540,753,269 bytes and
  `796c8b3aa587b257af0a46615a437dba`. Reject ambiguous rows, unsafe paths and links;
  allow regular metadata and directory entries. Never infer or follow payload URL.
- [ ] Write `source_identity.json` per `plan.md` and preserve the hash-matching
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

- [ ] F1/F2s pass focused tests; F2s has one reviewed bounded outcome; F2d has one
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

- [ ] Record separate development/external evidence for retained barcodes/QC,
  pairing, specimen provenance, genome/coordinate convention, count units, exact
  measured regions and feature provenance, with pinned sources/hashes. Missing
  evidence cannot be replaced by a user-supplied `PASS` boolean. Consume the pinned
  F2s source-identity and F2d development-feasibility records through proposed
  `--source-identity` and `--development-feasibility` options; preserve callers
  that omit them. Verify successful source resolution against the saved raw bag
  and manifest join. Reject malformed/tampered records or unexplained source/budget
  discrepancies; a well-formed unresolved-source record is valid input. Add
  `input_decision.json` and `INPUT_DECISION.md` with fields frozen in `plan.md`.
- [ ] Report M4's existing `PASS`/`INCONCLUSIVE`/`NEEDS_RECOUNT` plus unresolved
  gates. A partial archive, matching row total or annotation mask cannot certify
  full membership, common counts, author QC or readiness to train.
- [ ] A blocked report names the exact missing artifact, inspected source scope,
  and one smallest next action with proposed bytes/disk and required authority.
  Do not claim exhaustive absence or automatically launch that next action. Keep
  `training_allowed=false` and `model_training_performed=false`; an input decision
  cannot supply the absent M5 protocol. Source-resolution failure does not move
  NeMO ahead of the first unmet development prerequisite. Stop after review.

**Verification:** extend `tests/test_multiome.py`, `tests/test_atac_features.py` and
new `tests/test_input_decision.py`. Include equal totals with unknown QC, partial
coverage, count-unit mismatch, unmeasured regions, missing/tampered feasibility
fields, source-resolution failure, source hash/join mismatch, fabricated reader
readiness, unknown resource quantities and existing-directory refusal.
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

- [ ] F3 produces accepted evidence or a concrete blocker. Stop paired execution
  if required inputs fail; do not repeat F2s or expand F2d without changed evidence
  and separate authority.
- [ ] Any development-only pilot has its own reviewed scope and all relevant
  development gates. Original combined-cohort Checkpoint B and external gates
  remain unchecked while their requirements are unmet.
- [ ] F1–F3 changed only the permitted files; tests, source/RNA/dirty-file hashes,
  source ledger, feasibility record and final decision pass independent review. Code failure is not
  an accepted blocked-input conclusion. Handoff names exactly one next action and
  its required authority; no automatic M6a, real fold or processed-object inspection.

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

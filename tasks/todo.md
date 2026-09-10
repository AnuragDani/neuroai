# Paired DS multiome implementation checklist

Updated: 2026-09-09. Retained-cell ingestion, neural training, final artifacts and
one-shot scoring verified. 150 synthetic internal fits plus six final refits.
Scientific acceptance gates remain open; the full research plan is not complete.

Contract: [dataset proposal](../docs/PAIRED_DS_MULTIOME_DATASET_OPTIONS.md). Overview: [plan.md](plan.md).

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
2. Accept a specific common-region ATAC count source, or approve a separately bounded fragment-recount task. The two inspected raw libraries have zero exact common peaks; zero-filling cannot fix this. Public fragment packages total roughly 43 GiB compressed before working files, so a full recount is not silently started on this machine's roughly 54 GB free disk.
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
**Likely files:** `configs/paired_multiome.json`, `src/p22/eval/multiome_protocol.py`, `tests/test_multiome_protocol.py`.

## M6: Run donor-aware baseline models

Connect accepted real paired inputs to the existing models and training loop while retaining the separate synthetic runner's safeguards.

**Acceptance criteria:**

- [ ] Reuse preprocessing fingerprints, `BaselineMLP`, `ConcatFusionModel`, `GatedFusionModel`, and existing cheap controls; fit transforms only inside training partitions and give donors equal training weight.
- [x] Add optional donor-aggregated validation scoring to `train_model`, preserving existing behavior for callers without donor IDs. Checkpoint selection and fold metrics use the declared donor aggregation; verified on synthetic donor fixtures.
- [ ] A small internal run reports all eligible baseline families on identical donor splits/cell caps, with parameters, runtime, and negative/inconclusive outcomes; NeMO never selects checkpoints or hyperparameters.

**Verification:** `.venv-p22/bin/python -m pytest -q tests/test_multiome_runner.py tests/test_training.py`; verify donor-balanced selection can differ from cell-level selection, and that changing held-out data cannot refit transforms. Run one bounded real internal fold and record the command/config hash.

**Dependencies:** M5. **Scope:** Medium.
**Likely files:** `src/p22/eval/multiome_runner.py`, `tests/test_multiome_runner.py`, `src/p22/training/loop.py`, `tests/test_training.py`.

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

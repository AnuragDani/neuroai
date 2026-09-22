# P22 results execution and professor handoff

Run: `p22-results-executio-debda8` · Worktree base `8217719713c271349d1e54eda679672b82133a56`
Updated: 2026-09-21 (iteration 7) · Maintained inside the GNHF worktree.

## 1. Current status and result

**Result first.** The completed RNA replication remains **INCONCLUSIVE** (all four
donor-bootstrap correlation intervals cross zero). The **frozen repeated
donor-split internal comparison** (iteration 5) is an **honest null**: the
cross-attention minus matched token-concat donor-level balanced-accuracy difference,
averaged over 5 repeats of a 5-fold donor-isolated split that tests **all 30 donors
each repeat**, is **+0.0333** with 95% donor-bootstrap interval **[-0.0133, +0.0806]**
(margin 0.07; `advantage_demonstrated=false`). The interval is no longer degenerate;
it crosses zero. Mean donor balanced accuracy is near chance for every family
(cross-attention 0.527, token-concat 0.493, majority 0.367), so this is a null on a
low-signal input rather than an architecture finding.

This replaces the single-fold pilot (iteration 3: 6 test donors, interval [0,0]) as
the internal estimate. The pilot remains valid as a mechanically passing pilot.

Iteration 6 now covers the frozen folds with the **held-out faithfulness and
initialization-seed evidence** that iteration 4 had run only on the pilot fold
(`experimental result`, all 25 folds, no new network). The pattern reproduces: every
two-view family depends far more on the RNA view than on the 256-region ATAC view —
mean donor balanced accuracy drop from RNA-view ablation is 0.103 (cross-attention),
0.145 (concat), 0.116 (token-concat), 0.080 (gated), while ATAC-view ablation is
-0.001 to +0.027. Within-donor permutation is ~0 (exactly 0.0 for concat/token), as
expected because no cell attends to another; the tiny cross-attention/gated nonzero
is a floating-point aggregation-threshold artifact, not cell-order sensitivity. The
fixed-uniform-route intervention is `NOT_APPLICABLE` for the three non-gated families
and measured for the gated family (mean drop 0.001, routing shift 0.292). Across
initialization seeds 0/1/2 with donor splits held fixed, the mean primary delta is
+0.0367 / -0.0153 / -0.0060 (spread 0.052), so the frozen internal null is not an
initialization-seed artifact. This closes the "applicable faithfulness tests" item
for the frozen internal comparison.

Iteration 7 addresses the protocol's remaining unresolved normalization item
(`experimental result`, all 25 folds, no new network). A prospectively declared
normalization sensitivity re-runs the frozen comparison under raw-count standard
scaling (the frozen primary) and `log1p`-then-standard scaling. The raw variant
**exactly reproduces** the frozen estimate and interval (+0.0333,
[-0.0133, +0.0806]); the `log1p` variant gives the same estimate +0.0333 with
interval [-0.0050, +0.0800]. Advantage is false in both and per-family accuracies
stay near chance, so the frozen internal null is **not normalization-dependent**.
This prospectively freezes raw-count standard scaling as the operative
normalization without altering the primary estimate.

Six linked artifacts now exist on real data:

1. `verified` — a **frozen training-fold-only region set** (top 256 exact
   intervals by training-library prevalence) from the 28 training libraries of
   pilot fold (repeat 0, fold 0; 24 train / 6 test donors). Union = 1,440,187
   intervals; `regions_sha256 = 192d0b7a…`.
2. `experimental result` — a **real development ATAC count matrix**
   **256 × 248,998**, `int64`, `nnz = 4,879,858`, unit `fragment_overlap_sum`,
   with **256/256 regions joining the 248,998-cell allowlist with zero unknown
   barcodes**, recovered by bounded remote tabix queries (1.779 GB fetched, no
   whole-asset read).
3. `experimental result` — the **real paired pilot** (7,680 cells at 256/donor,
   real 35,477-gene RNA + real 256-region ATAC on the same cells, six neural
   families) is a mechanically passing pilot but shows **no attention advantage**.

The pilot is a pilot: one outer fold, one initialization seed, raw-count standard
scaling, no final refit, no external evaluation, no biological mechanism claim.

Iteration 4 added the **held-out faithfulness and initialization-seed evidence** the
pilot omitted (`experimental result`, pilot fold only): every two-view model's
held-out prediction depends far more on the RNA view than on the 256-region ATAC view
— ablating the RNA view collapses donor balanced accuracy from 0.625 to 0.0
(concat/token/cross) or 0.5 (gated), while ablating the ATAC view leaves it at 0.625.
The fixed-uniform-route intervention is measured only for the gated family (routing
shift 0.42) and reported `NOT_APPLICABLE` for the non-gated families.
Initialization-seed sensitivity (split fixed, seeds 0/1/2) is flat. These must be
repeated on the frozen final folds (R4c) before they support the final estimate.

Iteration 5 adds the three artifacts that turn the pilot into the frozen internal
comparison:

4. `verified` — **per-fold training-only region sets** for all 25 outer folds
   (top-256 exact intervals by each fold's training-library prevalence); their
   **union is 480 regions**, `union_sha256 = 29ab6739…3f9e`.
5. `experimental result` — a **real 480 × 248,998 union ATAC matrix**
   (`nnz = 9,513,875`, `fragment_overlap_sum`, **480/480 regions joining with zero
   unknown barcodes**, 3.295 GB fetched, no whole-asset read), from which each fold's
   training-only 256 regions are subset with no zero-filling.
6. `experimental result` — the **frozen repeated donor-split internal comparison**:
   25 folds, all 30 donors tested per repeat, primary delta +0.0333 (95% interval
   [-0.0133, 0.0806]), advantage false.
7. `experimental result` — the **frozen-fold faithfulness and initialization
   sensitivity** (iteration 6): seven held-out interventions per two-view family on
   all 25 folds, and the primary contrast refit at init seeds 0/1/2 with donor splits
   held fixed. RNA-view dependence dominates; seed-to-seed mean delta range
   [-0.0153, +0.0367]. No new network.

## 2. Delta from prior runs and execution/resource amendment

- Iterations 1–2 cleared the development fragment **barcode-join/index** gate and
  the **remote random-access** gate (mechanism proofs only, no matrix).
- Iteration 3 closes the next two gaps: the **frozen region set** and the
  **real paired pilot**. It adds the missing ingestion/orchestration code
  (`scripts/freeze_development_region_set.py`,
  `scripts/quantify_development_atac.py`, `scripts/run_real_paired_pilot.py`).
- Iteration 4 adds the pilot-fold **faithfulness + initialization-seed** evidence
  (`src/p22/eval/paired_faithfulness.py`, `scripts/run_real_paired_faithfulness.py`).
- Iteration 5 replaces the single-fold pilot with the **frozen repeated donor-split
  internal comparison**: per-fold training-only region sets and a 480-region union
  quantified once (`scripts/freeze_repeated_region_sets.py`,
  `src/p22/eval/repeated_comparison.py`, `scripts/run_real_paired_comparison.py`).
  It also addresses one of the pilot's two weaknesses the handoff named: the
  degenerate 6-donor interval (all 30 donors tested per repeat). The chromosome-1
  tie-break bias was **not** fixed: per-fold discovery protects outer-test
  provenance but leaves 163–219 of 256 regions per fold on chromosome 1, and the
  480-region union is 308 chr1 / 110 chr10 / 1 chr21. This feature set is retained
  as the historical exploratory representation for the measurement-correction
  comparison and limits what it can say about multimodal disease signal
  (see `GNHF_P22_CORRECTED_RESULTS_AND_HANDOFF.md`, review finding #4).
- Iteration 6 repeats the pilot-fold **faithfulness + initialization-seed** evidence
  on the frozen folds (`scripts/run_real_paired_faithfulness_frozen.py` and the new
  `aggregate_interventions` in `src/p22/eval/paired_faithfulness.py`), reusing the
  measured union matrix with no new network.
- Iteration 7 closes the **normalization ambiguity** with a prospectively declared
  sensitivity (`scripts/run_real_paired_normalization_sensitivity.py`): the frozen
  raw-count variant reproduces the primary exactly and the `log1p` variant gives the
  same null, so raw-count standard scaling is frozen as the operative normalization.
  It also rechecks the external route (still BLOCKED).
- Prospective amendment in `configs/results_execution_amendment_2026-09-21.json`
  records the iteration-3 allocation (30 GEO features files ≈ 49.5 MB; fragment
  index 5.3 MB; 1.779 GB region-query transfer; 9.9 MB matrix), the iteration-4
  allocation (no network; 6 neural fits), the iteration-5 allocation (37 GEO
  features files ≈ 62 MB; 3.295 GB union-region query transfer; 19.3 MB matrix;
  25 × 6 neural fits, 43.4 s) and the iteration-6 allocation (no network; 25 ×
  (4 intervention + 4 seed-refit) fits, 68.3 s). Historical records
  (`plan/approvals.json`, the source contract, the Sept-8 evidence note) remain
  byte-for-byte unchanged. No paid infra, no controlled access, no unbounded
  acquisition, no messages.

## 3. Professor-direction coverage

| Direction | Source anchor | Executed evidence this run |
|---|---|---|
| Mathematical specificity / customization | Jul 2 [00:00],[01:10],[17:10]; Jul 21 [25:26] | Per-fold training-only region freeze + frozen protocol; existing stack reused, no architecture change |
| Meaningful biological question | Jul 2 [00:36],[18:06],[19:30],[20:51] | Disease benchmark preserved; frozen internal donor-level contrast, no new endpoint |
| Clear conclusions, honest Tasic scope | Jul 21 [00:00],[07:52],[13:39] | RNA stays INCONCLUSIVE; frozen internal comparison is an honest null, not an advantage claim |
| Independent modalities, simple fusion | Jul 21 [15:04],[15:55],[17:39] | Measured RNA/ATAC pairing on shared cells; cross-attention vs matched token-concat across 5 × 5 donor splits |
| Fair supervision / method selection | Jul 2 [14:12],[16:43]; Jul 21 [15:55] | Same splits/labels/feature budget/head for all six families across all 25 folds; parameter counts reported |
| Donor-aware sampling / held-out eval | Jul 21 [03:40], To-Dos 3–4 | Donors split before feature selection every fold; **all 30 donors tested per repeat**; no overlap |
| Faithfulness / seed variability | Jul 21 To-Do 10 | **Executed on all 25 frozen folds** (iteration 6): seven held-out interventions per two-view family at donor level; primary contrast refit at init seeds 0/1/2 with splits held fixed (mean delta spread 0.052); **normalization sensitivity** (iteration 7) null under `log1p` |
| Independent biological validation | Jul 21 [18:51],[20:19],[21:56] | None claimed |
| Check GenAI claims vs originals | Jul 2 [12:09], To-Do 8 | Region discovery uses per-library cellranger peaks, not cluster peaks |
| Data access / approval | Jul 2 [03:10],[05:10],[06:46]; Sept attestation | Open public assets only; no restricted access, no contact |

## 4. Input acceptance evidence

| Fact | Value | Label |
|---|---|---|
| RNA source | local CELLxGENE H5AD, SHA-256 `08d6eff2…fcdbb`, 35,477 genes, 248,998 cells | verified |
| ATAC source | remote fragment `46b43994-…-fragment.tsv.bgz` + served `.tbi` | verified |
| Index SHA-256 | `fd656ed4…306f` | verified |
| Pilot region set | top-256 training-fold exact intervals (fold 0); `regions_sha256 = 192d0b7a…` | verified |
| Pilot ATAC matrix | 256 × 248,998, nnz 4,879,858, SHA-256 `b1b7e9e3…c307` | experimental result |
| Per-fold region sets | 25 × top-256 training-only intervals; union 480, `union_sha256 = 29ab6739…3f9e` | verified |
| Union ATAC matrix | 480 × 248,998, nnz 9,513,875, SHA-256 `62755125…84d7` | experimental result |
| Barcode join | 256/256 (pilot) and 480/480 (union) regions complete; 0 unknown barcodes | verified |
| Pairing | RNA and ATAC on the same 248,998 cells; all folds share the sampled cells | verified |
| Count unit | `fragment_overlap_sum` (insertion-vs-fragment not frozen) | unknown |
| External route | tar/tar.gz + per-file embargo; paired counts MEX not accessed | unknown |

## 5. Implemented code, environment and tests

- `scripts/freeze_development_region_set.py` — derives the training-fold library
  set from the frozen donor-aware split plan, parses GEO per-library
  `features.tsv.gz` Peaks rows, builds the exact-interval union, selects top-N by
  prevalence, and writes the region record + BED with per-file SHA-256.
- `scripts/quantify_development_atac.py` — concurrent bounded remote tabix
  quantification (reuses `query_fragment_regions`), assembles the sparse
  regions × cells matrix, refuses overwrite, records index/region/matrix hashes.
- `scripts/run_real_paired_pilot.py` — real paired ingestion (H5AD `X` via
  `load_cell_matrix`; ATAC npz subset), nested donor split, six-family fit, primary
  contrast, artifact writing; refuses overwrite.
- Tests: `tests/test_freeze_development_region_set.py` (10),
  `tests/test_quantify_development_atac.py` (4). All offline over synthetic
  fixtures; the real pilot is validated by execution, not a fixture.
- `src/p22/eval/paired_faithfulness.py` — donor-level wrapper over the seven
  held-out interventions (`run_donor_interventions`), the estimand-consistent
  `donor_balanced_accuracy`, and `initialization_seed_spread`.
- `scripts/run_real_paired_faithfulness.py` — reuses the real pilot inputs/fold,
  fits four two-view families, runs all seven interventions at donor level, and
  refits the primary families under seeds 0/1/2. `tests/test_paired_faithfulness.py`
  (9 offline tests).
- `scripts/freeze_repeated_region_sets.py` — per-fold training-only top-256 region
  sets for all 25 outer folds and their union; writes the record + union BED.
- `src/p22/eval/repeated_comparison.py` — across-repeat primary contrast and
  donor-cluster bootstrap over the across-repeat mean (failed single-class draws
  counted, never redrawn).
- `scripts/run_real_paired_comparison.py` — the frozen 5 × 5 orchestration: subsets
  each fold's training-only regions from the measured union and runs the six-family
  adapter; refuses overwrite.
- Tests: `tests/test_freeze_repeated_region_sets.py` (5),
  `tests/test_repeated_comparison.py` (9), all offline.
- `src/p22/eval/paired_faithfulness.py` — added `aggregate_interventions`, which
  aggregates per-fold intervention tables across folds (measured vs not-applicable
  counts, mean before/after/drop, mean routing shift) without treating a refusal as
  a zero effect.
- `scripts/run_real_paired_faithfulness_frozen.py` — runs the seven interventions and
  the initialization-seed sensitivity on all 25 frozen folds, subsetting each fold's
  training-only regions from the measured union matrix; refuses overwrite.
- Tests: `tests/test_paired_faithfulness.py` extended with six offline
  `aggregate_interventions` tests (15 in the file total).
- `scripts/run_real_paired_normalization_sensitivity.py` — runs the frozen 25 folds
  under raw-count and `log1p` preprocessing variants (same folds, region subsets,
  families and seed) and reports both primary contrasts; refuses overwrite.
  `tests/test_real_paired_normalization.py` (5 offline tests) covers the `log1p`
  sparse/dense transform and the variant dispatch.

Commands actually run and status:

```
.venv-p22/bin/python scripts/freeze_development_region_set.py ... --top-n 256 ...  # PASS
.venv-p22/bin/python scripts/quantify_development_atac.py ... --workers 12 ...      # PASS, 256 x 248998
.venv-p22/bin/python scripts/run_real_paired_pilot.py --output-dir ...              # PASS, null advantage
.venv-p22/bin/python scripts/run_real_paired_faithfulness.py --output-dir ...       # PASS, interventions + seed spread
.venv-p22/bin/python scripts/freeze_repeated_region_sets.py ... --top-n 256 ...      # PASS, 480 union
.venv-p22/bin/python scripts/quantify_development_atac.py ... --workers 6 ...        # PASS, 480 x 248998
.venv-p22/bin/python scripts/run_real_paired_comparison.py --output-dir ...          # PASS, +0.0333, advantage false
.venv-p22/bin/python scripts/run_real_paired_faithfulness_frozen.py --output-dir ...  # PASS, 25 folds, seed spread 0.052
.venv-p22/bin/python scripts/run_real_paired_normalization_sensitivity.py --output-dir ...  # PASS, raw reproduces +0.0333, log1p +0.0333
.venv-p22/bin/python -m pytest -q -m "not slow"                                     # 924 passed, 32 deselected
.venv-p22/bin/ruff check scripts tests src && ruff format --check scripts tests src  # pass
```

Environment: `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python`
(anndata 0.12.6, h5py 3.16.0, scipy 1.17.1, torch 2.8.0).

## 6. Pilot vs final vs historical results

- Historical (unchanged): RNA replication INCONCLUSIVE; 68 exploratory donor
  omissions preserved; synthetic paired fits only.
- **Pilot (iteration 3):** one fold, one seed — donor balanced accuracy: rna_only
  0.625, atac_only 0.500, concat/gated/token/cross-attention 0.625, majority 0.500;
  cross-attention − token-concat = **0.0**.
- **Pilot faithfulness (iteration 4):** RNA-view clamp/ablate donor balanced
  accuracy 0.625 → 0.5/0.0; ATAC-view clamp/ablate stays 0.625; uniform route
  measured only for the gated family (routing shift 0.42). Init-seed spread 0.0
  (cross-attention and token-concat both 0.625 at seeds 0/1/2).
- **Frozen internal comparison (iteration 5):** 25 folds (5 × 5), all 30 donors
  tested per repeat. Cross-attention − token-concat donor balanced accuracy
  **+0.0333**, 95% donor-bootstrap interval **[-0.0133, +0.0806]**, margin 0.07,
  advantage **false**. Per-repeat deltas `{0: +0.100, 1: -0.067, 2: 0.000,
  3: +0.067, 4: +0.067}`; 1000/1000 bootstrap replicates valid. Mean donor balanced
  accuracy: rna_only 0.447, atac_only 0.400, concat 0.540, gated 0.493,
  token_concat 0.493, cross_attention 0.527, majority 0.367.
- **Frozen-fold faithfulness (iteration 6):** 25 folds. Mean donor balanced accuracy
  drop by intervention — RNA ablation 0.103 (cross-attention) / 0.145 (concat) /
  0.116 (token-concat) / 0.080 (gated); ATAC ablation -0.001 to +0.027; within-donor
  permutation ~0 (0.000 for concat/token); uniform route N/A for non-gated, gated
  drop 0.001 (routing shift 0.292). Init-seed mean primary delta +0.0367 / -0.0153 /
  -0.0060 at seeds 0/1/2 (spread 0.052).
- **Normalization sensitivity (iteration 7):** 25 folds. Raw standard scaler
  reproduces the frozen primary (+0.0333, [-0.0133, +0.0806]); `log1p` + standard
  scaler gives +0.0333 ([-0.0050, +0.0800]); advantage false in both. Model means
  near chance in both variants.
- Final paired estimate: **internal final produced**; external validation **not launched**.

## 7. External evaluation and biological validation

No evaluation lock exists; external pairing/QC/common-feature gates are unresolved;
the external payloads are tar-packaged under per-file embargo. No biological
mechanism is claimed. The external paired RNA+ATAC counts MEX is the cheaper
candidate route but was not accessed this run.

Iteration 7 rechecked the external route directly (2026-09-21, `verified`):
direct HTTPS to both `data.nemoarchive.org` and `assets.nemoarchive.org` fails TLS
(`LibreSSL SSL_ERROR_SYSCALL`) on three attempts, and the `r.jina.ai` read proxy
timed out. The release manifest marks per-file `Access=embargo` while the
collection API reports `access=open`, and the controlled raw data sits behind NIMH
Data Archive approval. The external ATAC feature axis is one author MACS2 peak set
with no established common measured feature space against the frozen development
region set. **External paired evaluation is therefore BLOCKED** on transport,
access terms and feature compatibility; no external outcome was inspected and no
embargo/authentication was bypassed.

## 8. Artifact paths

- Pilot summary (tracked): `docs/real_paired_pilot_2026-09-21.json`
- Matrix evidence (tracked): `docs/atac_development_matrix_2026-09-21.json`,
  `docs/atac_development_matrix_regions_2026-09-21.tsv`
- Combined write-up (tracked): `docs/DEVELOPMENT_PAIRED_INPUT_AND_PILOT_2026-09-21.md`
- Faithfulness write-up (tracked): `docs/PAIRED_FAITHFULNESS_AND_SEED_2026-09-21.md`,
  `docs/real_paired_faithfulness_2026-09-21.json`; run artifacts (gitignored)
  `reports/generated/real_paired_faithfulness_20260921/run/run.json`
  (SHA-256 `576882b6…20f8`)
- Pilot region set (tracked): `configs/development_region_set_fold0_2026-09-21.json`,
  `configs/development_region_set_fold0_2026-09-21.bed`
- Repeated region sets (tracked): `configs/repeated_region_sets_2026-09-21.json`,
  `configs/repeated_region_sets_union_2026-09-21.bed`
- Frozen protocol (tracked): `configs/final_internal_comparison_2026-09-21.json`
- Internal comparison evidence (tracked): `docs/repeated_internal_comparison_2026-09-21.json`,
  `docs/REPEATED_INTERNAL_COMPARISON_2026-09-21.md`
- Frozen-fold faithfulness (tracked): `docs/real_paired_faithfulness_frozen_2026-09-21.json`,
  `docs/PAIRED_FAITHFULNESS_FROZEN_FOLDS_2026-09-21.md`; run artifacts (gitignored)
  `reports/generated/real_paired_faithfulness_frozen_20260921/run/{run.json,per_fold.json,SUMMARY.md}`
- Normalization sensitivity (tracked): `docs/real_paired_normalization_sensitivity_2026-09-21.json`,
  `docs/NORMALIZATION_SENSITIVITY_2026-09-21.md`; run artifacts (gitignored)
  `reports/generated/real_paired_normalization_20260921/run/{run.json,SUMMARY.md}`
  (`run.json` SHA-256 `b7a178d4…5c1c`)
- Run artifacts (gitignored): `reports/generated/development_region_set_20260921/`
  (`region_set.json`, `regions.bed`, `counts/counts.npz`, `counts/counts.json`,
  `quantify.json`), `reports/generated/real_paired_pilot_20260921/run/run.json`
  (SHA-256 `0e9f5069…59a6`),
  `reports/generated/repeated_comparison_20260921/` (`region_sets.json`, `union.bed`,
  `counts/counts.npz`, `counts/counts.json`, `quantify.json`),
  `reports/generated/real_paired_comparison_20260921/run/{run.json,per_fold.json,SUMMARY.md}`

## 9. Unsent professor update

> Question: can accepted paired RNA+ATAC inputs support the planned multimodal
> comparison? Status: the RNA replication remains inconclusive. We have now run the
> frozen repeated donor-split internal comparison on real paired data. Each of the
> 25 outer folds uses a training-only ATAC region set (top-256 exact intervals from
> that fold's training libraries); the 25 sets are subsets of one 480-region union,
> measured once from the open indexed fragment with complete barcode joins, and no
> unmeasured interval is zero-filled. Every repeat tests all 30 donors (15 control /
> 15 DS). Result: no advantage — cross-attention minus matched token-concat donor
> balanced accuracy is +0.0333 (95% donor-bootstrap interval [-0.0133, +0.0806],
> margin 0.07). Every family is near chance on held-out donors (majority 0.367,
> cross-attention 0.527), so this is a null on a low-signal input, not an
> architecture finding. This is the internal estimate; external paired data remain
> tar-packaged under a per-file embargo and were not accessed, so external
> validation is not launched. Held-out faithfulness and initialization-seed
> evidence now covers all 25 frozen folds: RNA-view interventions dominate (ablation
> costs 0.08-0.15 donor balanced accuracy), ATAC-view interventions are near zero,
> and the primary null holds across initialization seeds 0/1/2 (mean delta range
> -0.015 to +0.037). A prospectively declared normalization sensitivity also shows
> the null is not normalization-dependent: raw-count standard scaling reproduces
> +0.0333 and log1p gives the same +0.0333, so raw-count scaling is frozen as the
> operative normalization. External validation remains blocked: the NeMO
> endpoints fail TLS from this machine, the release marks per-file embargo, and no
> cross-cohort common measured feature set is established. Outstanding decision:
> whether to invest in a network path to the external cohort (or a provider fix)
> versus finalizing the internal result as the deliverable.

## 10. Exact unresolved dependency and smallest next action

Unresolved: (i) the **external route** remains BLOCKED (TLS transport failure,
per-file embargo, no common measured feature space), so external validation is not
launched; (ii) no independent biological mechanism evidence exists. The accepted
normalization is now **resolved for the primary**: raw-count standard scaling was
prospectively frozen and the `log1p` sensitivity is null.

Completed this iteration (R5a): the normalization sensitivity covers all 25 frozen
folds and confirms the frozen internal null is not normalization-dependent (no new
network). The external route was rechecked and remains BLOCKED.

Smallest next action (R5b): the external dependency is now evidenced rather than
merely unknown. The smallest external action that could unblock it is a provider-side
fix or a network path that reaches `data.nemoarchive.org`/`assets.nemoarchive.org`
directly (not through a mirror), plus a published cross-cohort common measured
feature set or a resolution of the per-file `embargo` conflict. Absent that, the
remaining in-scope work is the professor-facing notebook and handoff finalization;
external execution must not tune on external outcomes.

## 11. Reproduce

```
# region set (network: 29 GEO features files)
.venv-p22/bin/python scripts/freeze_development_region_set.py \
  --features-dir reports/generated/development_region_set_20260921/features \
  --obs-h5ad /Users/anuragdani/Github/niw-eb1a/P22/data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad \
  --repeat 0 --fold 0 --n-repeats 5 --n-folds 5 --split-seed 0 --top-n 256 \
  --out reports/generated/development_region_set_20260921/region_set.json \
  --regions-file reports/generated/development_region_set_20260921/regions.bed
# ATAC matrix (bounded remote tabix)
.venv-p22/bin/python scripts/quantify_development_atac.py \
  --regions-file reports/generated/development_region_set_20260921/regions.bed \
  --index-path reports/generated/development_region_set_20260921/fragment.tbi \
  --obs-h5ad /Users/anuragdani/Github/niw-eb1a/P22/data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad \
  --workers 12 \
  --counts-out reports/generated/development_region_set_20260921/counts \
  --out reports/generated/development_region_set_20260921/quantify.json
# pilot
.venv-p22/bin/python scripts/run_real_paired_pilot.py \
  --output-dir reports/generated/real_paired_pilot_20260921/run
# faithfulness + initialization sensitivity (no network)
.venv-p22/bin/python scripts/run_real_paired_faithfulness.py \
  --output-dir reports/generated/real_paired_faithfulness_20260921/run
# repeated per-fold region sets (offline; features files cached in the generated dir)
.venv-p22/bin/python scripts/freeze_repeated_region_sets.py \
  --features-dir reports/generated/repeated_comparison_20260921/features \
  --obs-h5ad /Users/anuragdani/Github/niw-eb1a/P22/data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad \
  --n-repeats 5 --n-folds 5 --split-seed 0 --top-n 256 \
  --out reports/generated/repeated_comparison_20260921/region_sets.json \
  --union-bed reports/generated/repeated_comparison_20260921/union.bed
# union ATAC matrix (bounded remote tabix, 480 regions)
.venv-p22/bin/python scripts/quantify_development_atac.py \
  --regions-file reports/generated/repeated_comparison_20260921/union.bed \
  --index-path reports/generated/development_region_set_20260921/fragment.tbi \
  --obs-h5ad /Users/anuragdani/Github/niw-eb1a/P22/data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad \
  --workers 6 \
  --counts-out reports/generated/repeated_comparison_20260921/counts \
  --out reports/generated/repeated_comparison_20260921/quantify.json
# frozen internal comparison
.venv-p22/bin/python scripts/run_real_paired_comparison.py \
  --output-dir reports/generated/real_paired_comparison_20260921/run
# frozen-fold faithfulness + initialization sensitivity (no network)
.venv-p22/bin/python scripts/run_real_paired_faithfulness_frozen.py \
  --output-dir reports/generated/real_paired_faithfulness_frozen_20260921/run
# normalization sensitivity (no network)
.venv-p22/bin/python scripts/run_real_paired_normalization_sensitivity.py \
  --output-dir reports/generated/real_paired_normalization_20260921/run
```

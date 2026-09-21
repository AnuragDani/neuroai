# P22 results execution and professor handoff

Run: `p22-results-executio-debda8` · Worktree base `8217719713c271349d1e54eda679672b82133a56`
Updated: 2026-09-21 (iteration 4) · Maintained inside the GNHF worktree.

## 1. Current status and result

**Result first.** The completed RNA replication remains **INCONCLUSIVE** (all four
donor-bootstrap correlation intervals cross zero). This iteration executed the
**first real paired RNA+ATAC run** for the development cohort and obtained an
**honest null**: on one donor-isolated fold the cross-attention minus matched
token-concat donor-level balanced-accuracy difference is **0.0** (bootstrap
interval [0.0, 0.0]; practical margin 0.5; `advantage_demonstrated=false`).

Three linked artifacts now exist on real data:

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

This is the first paired result of the study. It is a pilot: one outer fold, one
initialization seed, raw-count standard scaling, no final refit, no external
evaluation, no biological mechanism claim.

Iteration 4 added the **held-out faithfulness and initialization-seed evidence** the
pilot omitted (`experimental result`): every two-view model's held-out prediction
depends far more on the RNA view than on the 256-region ATAC view — ablating the RNA
view collapses donor balanced accuracy from 0.625 to 0.0 (concat/token/cross) or 0.5
(gated), while ablating the ATAC view leaves it at 0.625. The fixed-uniform-route
intervention is measured only for the gated family (routing shift 0.42) and reported
`NOT_APPLICABLE` for the non-gated families. Initialization-seed sensitivity (split
fixed, seeds 0/1/2) is flat: cross-attention and token-concat both 0.625, primary
delta 0.0 at every seed. The 256-region ATAC feature set is the likely reason ATAC
carries little signal; this is an input limitation, not an architecture finding.

## 2. Delta from prior runs and execution/resource amendment

- Iterations 1–2 cleared the development fragment **barcode-join/index** gate and
  the **remote random-access** gate (mechanism proofs only, no matrix).
- Iteration 3 closes the next two gaps: the **frozen region set** and the
  **real paired pilot**. It adds the missing ingestion/orchestration code
  (`scripts/freeze_development_region_set.py`,
  `scripts/quantify_development_atac.py`, `scripts/run_real_paired_pilot.py`).
- Prospective amendment in `configs/results_execution_amendment_2026-09-21.json`
  records the iteration-3 allocation (30 GEO features files ≈ 49.5 MB; fragment
  index 5.3 MB; 1.779 GB region-query transfer; 9.9 MB matrix) and the status
  update. Historical records (`plan/approvals.json`, the source contract, the
  Sept-8 evidence note) remain byte-for-byte unchanged. No paid infra, no
  controlled access, no unbounded acquisition, no messages.

## 3. Professor-direction coverage

| Direction | Source anchor | Executed evidence this run |
|---|---|---|
| Mathematical specificity / customization | Jul 2 [00:00],[01:10],[17:10]; Jul 21 [25:26] | Region-set freeze + pilot reuse the existing stack; no architecture change |
| Meaningful biological question | Jul 2 [00:36],[18:06],[19:30],[20:51] | Disease benchmark preserved; pilot reports donor-level contrast, no new endpoint |
| Clear conclusions, honest Tasic scope | Jul 21 [00:00],[07:52],[13:39] | RNA stays INCONCLUSIVE; pilot is an honest null, not an advantage claim |
| Independent modalities, simple fusion | Jul 21 [15:04],[15:55],[17:39] | Measured RNA/ATAC pairing on shared cells; cross-attention vs token-concat control |
| Fair supervision / method selection | Jul 2 [14:12],[16:43]; Jul 21 [15:55] | Same splits/labels/feature budget/head for all six families; parameter counts reported |
| Donor-aware sampling / held-out eval | Jul 21 [03:40], To-Dos 3–4 | Donors split before feature selection; 24 train / 6 test donors, no overlap |
| Faithfulness / seed variability | Jul 21 To-Do 10 | **Executed** on the pilot fold: seven held-out interventions per two-view family at donor level; init-seed sensitivity flat (spread 0.0 over seeds 0/1/2) |
| Independent biological validation | Jul 21 [18:51],[20:19],[21:56] | None claimed |
| Check GenAI claims vs originals | Jul 2 [12:09], To-Do 8 | Region discovery uses per-library cellranger peaks, not cluster peaks |
| Data access / approval | Jul 2 [03:10],[05:10],[06:46]; Sept attestation | Open public assets only; no restricted access, no contact |

## 4. Input acceptance evidence

| Fact | Value | Label |
|---|---|---|
| RNA source | local CELLxGENE H5AD, SHA-256 `08d6eff2…fcdbb`, 35,477 genes, 248,998 cells | verified |
| ATAC source | remote fragment `46b43994-…-fragment.tsv.bgz` + served `.tbi` | verified |
| Index SHA-256 | `fd656ed4…306f` | verified |
| Region set | top-256 training-fold exact intervals; `regions_sha256 = 192d0b7a…` | verified |
| ATAC matrix | 256 × 248,998, nnz 4,879,858, SHA-256 `b1b7e9e3…c307` | experimental result |
| Barcode join | 256/256 regions complete; 0 unknown barcodes | verified |
| Pairing | RNA and ATAC on the same 248,998 cells; pilot on the shared sampled cells | verified |
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

Commands actually run and status:

```
.venv-p22/bin/python scripts/freeze_development_region_set.py ... --top-n 256 ...  # PASS
.venv-p22/bin/python scripts/quantify_development_atac.py ... --workers 12 ...      # PASS, 256 x 248998
.venv-p22/bin/python scripts/run_real_paired_pilot.py --output-dir ...              # PASS, null advantage
.venv-p22/bin/python scripts/run_real_paired_faithfulness.py --output-dir ...       # PASS, interventions + seed spread
.venv-p22/bin/python -m pytest -q -m "not slow"                                     # 899 passed, 32 deselected
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
- Final paired estimate: **not produced**.
- External evaluation: **not launched**.

## 7. External evaluation and biological validation

No evaluation lock exists; external pairing/QC/common-feature gates are unresolved;
the external payloads are tar-packaged under per-file embargo. No biological
mechanism is claimed. The external paired RNA+ATAC counts MEX is the cheaper
candidate route but was not accessed this run.

## 8. Artifact paths

- Pilot summary (tracked): `docs/real_paired_pilot_2026-09-21.json`
- Matrix evidence (tracked): `docs/atac_development_matrix_2026-09-21.json`,
  `docs/atac_development_matrix_regions_2026-09-21.tsv`
- Combined write-up (tracked): `docs/DEVELOPMENT_PAIRED_INPUT_AND_PILOT_2026-09-21.md`
- Faithfulness write-up (tracked): `docs/PAIRED_FAITHFULNESS_AND_SEED_2026-09-21.md`,
  `docs/real_paired_faithfulness_2026-09-21.json`; run artifacts (gitignored)
  `reports/generated/real_paired_faithfulness_20260921/run/run.json`
  (SHA-256 `576882b6…20f8`)
- Region set (tracked): `configs/development_region_set_fold0_2026-09-21.json`,
  `configs/development_region_set_fold0_2026-09-21.bed`
- Run artifacts (gitignored): `reports/generated/development_region_set_20260921/`
  (`region_set.json`, `regions.bed`, `counts/counts.npz`, `counts/counts.json`,
  `quantify.json`), `reports/generated/real_paired_pilot_20260921/run/run.json`
  (SHA-256 `0e9f5069…59a6`)

## 9. Unsent professor update

> Question: can accepted paired RNA+ATAC inputs support the planned multimodal
> comparison? Status: the RNA replication remains inconclusive. We have now run
> the first real paired development pilot. We froze a training-fold-only ATAC
> region set, recovered a real 256-region × 248,998-cell count matrix from the
> open indexed fragment with complete barcode joins, and trained the six-family
> stack on real paired data with donor-isolated splits. Result: no advantage —
> cross-attention and matched token-concat both reach 0.625 donor balanced
> accuracy (difference 0.0). This is a pilot (one fold, raw scaling), not a final
> estimate, and external validation is not launched because the external payloads
> are tar-packaged under a per-file embargo. We also ran the held-out faithfulness
> interventions: the models depend on the RNA view (RNA ablation drops donor
> accuracy to 0.0) far more than on the 256-region ATAC view, and initialization
> seeds 0/1/2 leave the primary null unchanged. The 256-region feature set is the
> likely reason. Outstanding decision: approve the final frozen protocol (a
> stronger region set, accepted normalization, repeated donor splits so all 30
> donors are tested) and whether to pursue the external paired counts MEX route.

## 10. Exact unresolved dependency and smallest next action

Unresolved: the **final frozen protocol** is not yet fixed, and the **external
route** remains tar-packaged/embargoed.

Smallest next action: prospectively re-freeze a stronger development region set
(fix the chr1 tie-break bias; prevalence max is only 6/28), then run the repeated
donor-split internal comparison so all 30 donors are tested and the primary
contrast has a non-degenerate donor-level interval — labeled final, not pilot.
Faithfulness and initialization sensitivity are now executed at pilot level (R4a);
they must be repeated on the frozen final folds. External execution additionally
depends on resolving the tar packaging and per-file embargo (or using the external
paired counts MEX).

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
```

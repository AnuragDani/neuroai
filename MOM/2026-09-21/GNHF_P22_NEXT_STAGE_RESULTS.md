# P22 next-stage results: ATAC representation sensitivity and cell-state feasibility

Status: **IN PROGRESS — Phases 1–3 (representation sensitivity selection,
measurement, comparison and simple linear controls) executed and validated;
Phases 4–5 pending.** This is the main worktree handoff for the
`p22-test-atac-repres-14ef45` run. Starting checkpoint
`5e2165f619b149a2d05d9e0e4fc439c3bd0cfb81`. It preserves every earlier corrected
null and the historical artifacts; nothing here overwrites a prior result.

The question under test: **does the corrected internal null persist when the arbitrary
chromosome-name lexicographic tie-break inside prevalence ties is removed, and does the
available paired information support a cell-state-focused next study?** This is a
measurement-adequacy follow-up, not a search for a cross-attention win.

## Phase 1 — one prespecified representation change (DONE)

### Prospective amendment

`configs/atac_tiebreak_sensitivity_2026-09-21.json` (SHA-256
`560f5e68826f631091051f90851d9dff8d2f7d6217a8c9b9d7adfb4e593be5ac`) was written
**before** any selection ran or any outcome was inspected. It declares the starting
commit, input hashes, the exact ranking, the unchanged settings, the planned
diagnostics and the success/stop criteria. It is prospective only for this sensitivity;
the historical rule and its known outcomes are historical.

The **only factor changed** is the tie-break inside equal training-library prevalence:

- Historical: `top-256 exact intervals by prevalence; ties broken by (chromosome, start, end)`.
- New: `top-256 exact intervals by prevalence; ties broken by
  sha256("p22-atac-tiebreak-v1" + "\n" + region), then region`.

Candidate construction, prevalence definition, region budget (256), chromosome filter
(none), outer folds and donor splits are unchanged. The salt was fixed in advance; no
salt was searched and no outcome was used to pick it.

### Narrow code change

- `scripts/freeze_development_region_set.py`: added `--tie-break {historical,sha256}`
  (default `historical`), `--tie-break-salt`, and a `_ranking_key`/`_hash_tie_key`
  helper. Historical mode is byte-identical to the old rule.
- `scripts/freeze_repeated_region_sets.py`: threads `--tie-break`/`--tie-break-salt`/
  `--count-unit` through and records them.
- `scripts/summarize_atac_tiebreak_sensitivity.py`: new read-only diagnostics
  (chromosome distributions, overlap, prevalence histograms, donor/library isolation,
  deterministic rebuild). Fits no model.

### Deterministic sets, hashes and distributions

| Quantity | Historical | sha256 tie-break |
|---|---|---|
| Selection rule | prevalence → (chrom,start,end) | prevalence → sha256(salt,region) → region |
| Per-fold regions | 256 × 25 folds | 256 × 25 folds |
| Union regions | 480 | **465** |
| Union semantic SHA-256 | `29ab6739…` (reproduced exactly) | `4de10446…` |
| Union BED SHA-256 | `7168c33c…` | `d20d437a…` |
| Union chromosome 1 | **308** | **37** |
| Noncanonical contigs in union | 7 (`GL000194.1`, `GL000195.1`, `GL000205.2`×2, `GL000218.1`, `GL000219.1`, `KI270728.1`) | 0 |

Union chromosome spread (sha256): chr1 37, chr2 19, chr3 25, chr4 19, chr5 22, chr6 26,
chr7 30, chr8 11, chr9 11, chr10 17, chr11 25, chr12 23, chr13 8, chr14 19, chr15 12,
chr16 28, chr17 50, chr18 10, chr19 42, chr20 8, chr21 6, chr22 7, chrX 9, chrY 1.
Historical union is dominated by chr1 308 + chr10 110 (418/480) with only one chr21.

Per-fold chromosome-1 count: historical 163–219/256; sha256 **14–27/256**. Per-fold
overlap with the historical set: 38–64 regions (median 56), Jaccard 0.080–0.143. The
preparatory read-only diagnostic (27 chr1, 58 shared in repeat-0/fold-0) is reproduced
exactly.

Selected-region training-prevalence histograms are **identical** between the two
representations in every fold (repeat-0/fold-0: prev2 227, prev3 24, prev4 4, prev6 1),
confirming prevalence priority is preserved and only the tie order changed.

### Regression checks (all pass)

- Deterministic ranking under shuffled library order: yes (unit test + real rebuild).
- No outer-test library in discovery: yes, verified against the donor→library map on
  all 25 folds (`no_test_library_in_discovery: true`).
- Preserved prevalence priority: yes (identical prevalence histograms; unit test).
- Historical-mode reproduction: all 25 fold region lists and `regions_sha256`, the
  union region list and the union semantic SHA-256 reproduce the saved artifacts
  exactly.
- `tests/`: **1022 passed** (9 new). `ruff` clean on touched files.

Machine-readable evidence: `docs/atac_tiebreak_sensitivity_2026-09-21.json`.
Tracked copies: `configs/atac_tiebreak_region_sets_2026-09-21.json`,
`configs/atac_tiebreak_union_2026-09-21.bed`,
`configs/atac_tiebreak_region_sets_historical_reproduction_2026-09-21.json`.

### Exact replay (Phase 1)

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts \
  /Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python \
  scripts/freeze_repeated_region_sets.py \
  --features-dir reports/generated/repeated_comparison_20260921/features \
  --obs-h5ad /Users/anuragdani/Github/niw-eb1a/P22/data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad \
  --top-n 256 --tie-break sha256 --count-unit unique_fragment_overlap \
  --out reports/generated/atac_tiebreak_sensitivity_20260921/region_sets_sha256.json \
  --union-bed reports/generated/atac_tiebreak_sensitivity_20260921/union_sha256.bed

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts \
  /Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python \
  scripts/summarize_atac_tiebreak_sensitivity.py \
  --features-dir reports/generated/repeated_comparison_20260921/features \
  --historical reports/generated/atac_tiebreak_sensitivity_20260921/region_sets_historical_reproduction.json \
  --sha256 reports/generated/atac_tiebreak_sensitivity_20260921/region_sets_sha256.json \
  --obs-h5ad /Users/anuragdani/Github/niw-eb1a/P22/data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad \
  --out reports/generated/atac_tiebreak_sensitivity_20260921/diagnostics.json
```

### Claim boundaries (Phase 1)

- Removing lexicographic preference within prevalence ties is **not** genome-wide
  coverage or a validated regulatory panel. The sha256 set is an ordering control, not
  a better panel.
- Selection used no disease labels, no held-out donors and no outcome.
- No model was fitted for this record. A positive Phase 3 result would be exploratory
  and would require independent confirmation; a null completes the experiment when
  execution is valid.
- External validation remains separately gated and is unaffected.

## Phase 2 — measure the new regions (DONE)

### Bounded acquisition contract

`configs/atac_tiebreak_measurement_contract_2026-09-21.json` was written **before**
acquisition. It declares the source, index hash, count unit, the 465-region union,
the observed headroom (17.78 GiB free, 10 GiB reserve preserved, 137.4 GB host
memory), and finite budgets: aggregate transfer 4,000,000,000 bytes, temporary disk
1 MiB, retained disk 100 MB, memory 4 GB, per-operation timeout 120 s, 8 workers.

Cost was estimated from the **local tabix index** before acquisition: summing merged
chunk byte spans rounded up to 256 KiB windows gave 3,171,155,968 bytes (3.171 GB).
The historical 480-region estimate by the same method was 3,284,402,176 bytes against
an actual 3,295,412,224 bytes (0.3% low), so the estimator was validated.

Reuse of the 105 exact-identical historical intervals was considered and declined:
the historical matrix is keyed by the historical 480-region order and the measurement
tool has no per-region reuse mechanism, so one clean pass avoids mixing two matrix
assemblies.

### A transient transport fault and a bounded-retry fix

The first acquisition attempt aborted after ~8 minutes on a transient DNS failure
(`socket.gaierror`, `URLError`) — the unretried reader discarded the whole in-progress
run. `scripts/quantify_development_atac.py` now has a narrow `_RetryingTransport`
(bounded exponential backoff, default 4, run with 6) that retries only transport-level
faults and never retries a `ValueError` contract violation. Four regression tests were
added. The rerun completed cleanly.

### Measured matrix provenance

- Output: `reports/generated/atac_tiebreak_measured_20260921/counts/counts.npz`
- Shape **465 × 248,998**, nnz **9,616,203**, matrix SHA-256
  `5f13c089c0b598c45323d0afc874f96bdf7d4074307c3c01dc40129862d9f969`
- count unit `unique_fragment_overlap`, mode `fragment`, unknown policy `error`
- 465/465 complete joins, 0 empty regions, 0 truncated, 0 unknown barcodes
- actual transfer **3,182,166,016 bytes** (3.182 GB), 0.3% above the local estimate
- ordered cells SHA-256 `7a56c2a9…` equals the H5AD obs order and the historical matrix

### New acceptance binding

- Requirements: `configs/atac_tiebreak_acceptance_requirements_2026-09-21.json`
  (union `4de10446…`, 465 regions, six families, margin 0.07, seeds unchanged).
- Measured manifest: `configs/atac_tiebreak_input_manifest_2026-09-21.json`
  (generated by the shared builder; binds the H5AD, raw/var axis, ordered cells, the
  465-region matrix and union BED).
- `check_real_paired_acceptance.py` returns **ACCEPTED**, 11/11 checks, no blockers
  (`reports/generated/atac_tiebreak_measured_20260921/acceptance_decision.json`).

## Phase 3 — comparison and simple controls (DONE)

### Six-family comparison on the hash-tie representation

Frozen protocol reused unchanged (`sampling_seed=22`, `cell_cap=256`,
`feature_budget=128` per view, 5 repeats × 5 folds, split seed 0, model seed 0,
20 epochs, patience 5, batch 64, lr 0.001). Acceptance ACCEPTED.

| Representation | Union | Primary contrast (CA − TC) | 95% donor-bootstrap interval | Margin | Advantage |
|---|---|---|---|---|---|
| Historical corrected | 480 (chr1 308) | **+0.0066667** | [−0.025, +0.0350074] | 0.07 | false |
| sha256 tie-break | 465 (chr1 37) | **−0.0200000** | [−0.0533333, +0.0113165] | 0.07 | false |

Both representations give a null. The corrected internal null **persists** when the
lexicographic tie-break is removed; the point estimate moves slightly negative but
the interval still crosses zero. Per-repeat deltas (tie-break): 0.0, +0.0667, 0.0,
−0.0333, −0.1333. Per-model donor balanced accuracy means (tie-break): rna_only
0.5067, atac_only 0.3933, rna_atac_concat 0.5133, gated_fusion 0.5200, token_concat
0.5333, cross_attention 0.5133, majority 0.3667.

### Five-seed initialization sensitivity (tie-break)

Same pooled-donor estimand, donor splits fixed, seeds 0–4:
{0: −0.0200, 1: 0.0, 2: +0.0400, 3: −0.0133, 4: +0.0067}; spread 0.0600 < margin
0.07; no seed demonstrates an advantage. Held-out interventions again show RNA-view
dependence (clamp/ablate view A drops ~0.09–0.16) and near-zero ATAC-view dependence,
matching the historical corrected pattern; uniform routing applies only to the gated
family.

### Missing simple linear controls (both representations)

`scripts/run_real_paired_linear_controls.py` fits the three missing cell-level
controls on the **same** training-only variance-selected and scaled features, the
same inner-training donors, and the same held-out donor aggregation. Regularisation
frozen at `C=1.0`, `solver="lbfgs"`, `max_iter=1000`, `tol=1e-4`, `random_state=0`;
donor weights are the neural inverse-donor-cell-count weights normalised to mean one;
no class reweighting. **All 75 fits converged; no extension was used.**

| Control (mean donor balanced accuracy) | Historical corrected | sha256 tie-break |
|---|---|---|
| logreg_rna | 0.6200 | 0.6200 |
| logreg_atac | 0.4200 | 0.4067 |
| logreg_concat | 0.6200 | 0.6133 |

Secondary contrasts versus `token_concat` (descriptive; the primary reference is
unchanged):

| Contrast | Historical corrected | sha256 tie-break |
|---|---|---|
| logreg_rna − token_concat | +0.1067 [+0.0133, +0.2100] | +0.0867 [−0.0134, +0.1967] |
| logreg_atac − token_concat | −0.0933 [−0.1790, −0.0105] | −0.1267 [−0.2158, −0.0411] |
| logreg_concat − token_concat | +0.1067 [+0.0412, +0.1768] | +0.0800 [+0.0076, +0.1590] |

The RNA and concatenated linear controls **outperform** the neural token-concat
reference on both representations, while the ATAC-only control underperforms. This is
a secondary, estimator-level observation (linear vs neural) and is **not** a
cross-attention result and **not** a replacement for the primary contrast; it does
motivate the Phase 4 cell-state question rather than further neural tuning.

### Evidence and replay

Machine-readable evidence: `docs/atac_tiebreak_measured_and_comparison_2026-09-21.json`.
Ignored intermediates: `reports/generated/atac_tiebreak_measured_20260921/`,
`reports/generated/atac_tiebreak_comparison_20260921/`,
`reports/generated/atac_tiebreak_faithfulness_20260921/`,
`reports/generated/atac_linear_controls_historical_20260921/`,
`reports/generated/atac_linear_controls_tiebreak_20260921/`.

```
# Phase 2 measurement (bounded, retrying transport)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts <python> scripts/quantify_development_atac.py \
  --regions-file reports/generated/atac_tiebreak_sensitivity_20260921/union_sha256.bed \
  --index-path reports/generated/development_region_set_20260921/fragment.tbi \
  --obs-h5ad /Users/anuragdani/Github/niw-eb1a/P22/data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad \
  --count-mode fragment --unknown-policy error --workers 8 --transport-retries 6 \
  --total-max-bytes 4000000000 \
  --counts-out reports/generated/atac_tiebreak_measured_20260921/counts \
  --out reports/generated/atac_tiebreak_measured_20260921/quantify.json

# manifest + acceptance
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts <python> scripts/build_real_paired_input_manifest.py \
  --atac-matrix reports/generated/atac_tiebreak_measured_20260921/counts/counts.npz \
  --region-sets reports/generated/atac_tiebreak_sensitivity_20260921/region_sets_sha256.json \
  --union-bed reports/generated/atac_tiebreak_sensitivity_20260921/union_sha256.bed \
  --out configs/atac_tiebreak_input_manifest_2026-09-21.json

# six-family comparison
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts <python> scripts/run_real_paired_comparison.py \
  --atac-matrix reports/generated/atac_tiebreak_measured_20260921/counts/counts.npz \
  --region-sets reports/generated/atac_tiebreak_sensitivity_20260921/region_sets_sha256.json \
  --acceptance-requirements configs/atac_tiebreak_acceptance_requirements_2026-09-21.json \
  --acceptance-manifest configs/atac_tiebreak_input_manifest_2026-09-21.json \
  --output-dir reports/generated/atac_tiebreak_comparison_20260921/run

# five-seed faithfulness
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts <python> scripts/run_real_paired_faithfulness_frozen.py \
  --atac-matrix reports/generated/atac_tiebreak_measured_20260921/counts/counts.npz \
  --region-sets reports/generated/atac_tiebreak_sensitivity_20260921/region_sets_sha256.json \
  --acceptance-requirements configs/atac_tiebreak_acceptance_requirements_2026-09-21.json \
  --acceptance-manifest configs/atac_tiebreak_input_manifest_2026-09-21.json \
  --init-seeds 0 1 2 3 4 \
  --output-dir reports/generated/atac_tiebreak_faithfulness_20260921/run

# linear controls (run once per representation)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts <python> scripts/run_real_paired_linear_controls.py \
  --atac-matrix <counts.npz> --region-sets <region_sets.json> \
  --acceptance-requirements <requirements.json> --acceptance-manifest <manifest.json> \
  --reference-run <comparison run dir> --output-dir <new dir>
```

## Phase 4 — cell-state feasibility (PENDING)

Not started.

## Phase 5 — external route reconciliation (PENDING)

Not started. The fresh access note separates open-child declarations from the
unresolved manifest `Access=embargo` field and intermittent TLS transport failures.

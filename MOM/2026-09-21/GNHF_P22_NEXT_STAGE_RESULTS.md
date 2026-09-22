# P22 next-stage results: ATAC representation sensitivity and cell-state feasibility

Status: **IN PROGRESS — Phase 1 (representation sensitivity selection) executed and
validated; Phases 2–5 pending.** This is the main worktree handoff for the
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

## Phase 2 — measure the new regions (PENDING)

Not started. Requires a fresh disk/memory headroom check, a declared finite
acquisition contract, a bounded recount of the 465-region union from the same indexed
development fragment asset, and a new measured-artifact manifest + requirements record.
The 10 GiB free-disk reserve must be preserved; the last observed headroom was ~18 GiB.

## Phase 3 — comparison and simple controls (PENDING)

Not started.

## Phase 4 — cell-state feasibility (PENDING)

Not started.

## Phase 5 — external route reconciliation (PENDING)

Not started. The fresh access note separates open-child declarations from the
unresolved manifest `Access=embargo` field and intermittent TLS transport failures.

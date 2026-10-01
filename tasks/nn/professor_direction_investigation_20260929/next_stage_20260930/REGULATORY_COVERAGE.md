# Q3 — Fold-specific ATAC regulatory coverage

**Disposition:** `REGULATORY_ADEQUACY_UNRESOLVED`  
**Date:** 2026-09-30  
**Branch:** `gnhf/execute-the-p22-data-146414`  
**Dependency:** Q1 PASS. No fits, downloads, package installs, or recounts.

Machine-readable: [regulatory_coverage.json](regulatory_coverage.json).

## Adequacy labels (distinct)

| Axis | Label |
|---|---|
| Structural / measured coverage | `STRUCTURAL_COVERAGE_PASS` |
| Biological / regulatory adequacy | `REGULATORY_ADEQUACY_UNRESOLVED` |

All 25 panels are training-library-selected 256-region subsets of the exact counted 465-region union; hashes, dimensions, nonnegative counts, and panel∈union membership hold. Measured zeros are retained.

Prevalence/tie-break panels and gene-interval overlaps are descriptive. Overlap counts do not prove regulatory function; missing annotations remain unknown. Cannot authorize a biological regulatory-feature claim.

## Provenance and count semantics

| Item | Value |
|---|---|
| Genome build | `GRCh38` |
| Interval convention | chr:start-end 0-based half-open (cellranger-arc) |
| Count unit | `unique_fragment_overlap` |
| Union BED sha256 | `d20d437ac96401746c20ff3645c464bc668ac7ed942bfb709a5bc667ef26bc23` |
| Counts matrix sha256 | `5f13c089c0b598c45323d0afc874f96bdf7d4074307c3c01dc40129862d9f969` |
| Region sets sha256 | `13f630a6777a059db4ac1b5f17b397976030e0b0e29193e2bc09eab24dc46407` |
| Ordered cells sha256 | `7a56c2a906f66b528dd673f944c067a006d4f09127eda70ced4155c281a09e53` |
| Selection | training-library prevalence top-256; salt `p22-atac-tiebreak-v1` |

## All 25 panels (5 outer folds × 5 repeats)

- Panel size: **256** regions; union **465**.
- Zero-cell fraction across panels: min `0.0107511`, median `0.0125061`, max `0.0147551`.
- Gene-body overlap fraction: min `0.6094`, median `0.6484`, max `0.6953` (descriptive only; not regulatory proof).
- chr21 region fraction: min `0.0000`, median `0.0078`, max `0.0156`.

Per-panel and per-type donor coverage tables are in the JSON (`panels[].per_type`). Donor count, not cell count, drives replication.

## Independent panel replay (fold 0 / repeat 0)

| Check | Result |
|---|---|
| regions_sha256 | `True` |
| zero_cell_fraction | `0.012767170820649161` match=`True` |
| median_nonzero_regions | `15.0` match=`True` |
| median_fragment_overlaps | `17.0` match=`True` |

## Alternate representation (at most one)

**Proposed:** Existing gene-activity exact-count panel (configs/nn_gene_activity_2026-09-23.bed + measured counts), already quantified under a separate contract

**Reason:** Measured deficiency for regulatory questions: fold panels are prevalence-selected intervals without a regulatory-element annotation gate. Gene-linked exact counts reuse existing measurements; no new interval recount and no filling unmeasured peaks with biological zero.

**Does not authorize:** Biological cell-state fit (Q2 ENDPOINT_UNRESOLVED) or regulatory adequacy PASS; remains a candidate representation comparison for Q6+

## What this does and does not authorize

| Allowed next | Not authorized |
|---|---|
| Continue Q4–Q5 read-only reports | Claiming regulatory-feature adequacy PASS |
| Use measured exact counts / existing gene-activity panel in later design ranking | Filling unmeasured peaks with biological zero |
| Checkpoint A: unresolved regulatory adequacy is an acceptable reported outcome | Biological cell-state fit (still blocked by Q2) |

## Verification commands

```bash
export PYTHONPATH="$(pwd)/src"
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -c "import p22; print(p22.__file__)"
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python scripts/report_next_stage_regulatory_coverage.py
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -m pytest tests/test_next_stage_regulatory_coverage_q3.py -q
```

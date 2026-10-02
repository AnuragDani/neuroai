# M1 — Measured inputs and chromosome masking contract

**Disposition:** `INPUT_AND_MASKING_PASS`  
**Date:** 2026-10-01  
**Dependency:** M0 PASS. No fits, downloads, package installs, or recounts.

Machine-readable: [input_and_masking.json](input_and_masking.json).

## Contract checks

| Check | Result |
|---|---|
| Matrix/BED/region_sets/ordered-cell SHA-256 | PASS |
| Dimensions 465×248998; 30 donors; 24 chroms | PASS |
| Overlapping interval pairs in union | **58** (on 9 chromosomes) |
| Target-ID removal leaves interval-overlapping visible region | 45 / 465 targets — **insufficient** |
| Whole-target-chromosome mask same-chrom / interval leak | 0 / 0 — **eliminated** |
| Visible ATAC regions after mask | 415–464 |

## Count and zero semantics

- Genome build **GRCh38**; intervals **chr:start-end 0-based half-open (cellranger-arc)**; unit **`unique_fragment_overlap`**.
- A zero for a union region/cell means no unique fragment qualified under the half-open overlap rule for that exact interval; sparse storage omits zeros but they are measured.
- Unmeasured regions are absent from the union/matrix; they are never filled as biological zeros.
- Target is binary count>0 at one withheld region; visible ATAC excludes the entire target chromosome. RNA remains a separate measured assay and may stay as input.
- Forbidden inputs: `full nCount_ATAC`, `full nFeature_ATAC`, `target-inclusive QC/depth summaries`, `all-region latent / gene-activity values computed before masking`, `disease / donor / author_cell_type labels as features`.

## Overlap clarification

PLAN cites 58 overlapping pairs in the 465-region union spanning 24 chromosomes. Live enumeration confirms 58 pairs; pairs occur on 9 chromosomes within the 24-chromosome union (not one pair on every chromosome).

Pairs by chromosome: chr17=27, chr10=15, chr3=6, chr1=4, chr19=2, chr14=1, chr18=1, chr2=1, chr6=1.

## Inherited panel provenance

Historical 256-region panels are selected by outer-fold training-library prevalence (archival 5×5 disease-stratified donor splits). That uses outer-training donors/libraries and does not prove a later inner-validation-only construction. This pilot pins the measured 465-region union as the candidate target/feature space; M2 must freeze training-only target ranking without inventing stricter provenance than evidenced. Disease labels stratify archival splits only and are not model features.

- Selection rule: per outer fold: top-N exact intervals by that fold's training-library prevalence; ties broken by sha256(salt + '\n' + region) with salt 'p22-atac-tiebreak-v1', then region
- Strict inner-train-only historical panels claimed: **False**
- Donor/library isolation across 25 panels: **PASS**

## Preserved scientific labels

Primary **`B_NULL`**; S7/S9/S10 **`INVALID`**; S8 **`NO FIT`**; Q2 **`ENDPOINT_UNRESOLVED`** (does not block claim-level-2).

## What this does and does not authorize

| Allowed next | Not authorized |
|---|---|
| M2 training-only target feasibility on the pinned union | Model fitting or neural smoke learning |
| Continue independent safe feasibility without fits | Claiming biological regulatory function or cell-state |
|  | Relabeling Q2/S9/S10/primary B_NULL |
|  | Strict inner-train-only historical panel provenance |
|  | Target-ID-only ATAC masking |

## Verification commands

```bash
export PYTHONPATH="$(pwd)/src"
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -c "import p22; print(p22.__file__)"
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python scripts/report_masked_atac_input_and_masking.py
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -m pytest tests/test_masked_atac_input_and_masking_m1.py -q
```

# TASK_DATA_OPTIONS — R5 task and dataset path comparison

**Disposition:** `TASK_DATA_OPTIONS_BOUNDED`  
**Date:** 2026-10-01  
**Branch:** `gnhf/execute-p22-s-failur-d8f02c`  
**Dependency:** R4 `GUIDANCE_CLAIMS_PASS`. No research fits, no payload downloads, no package installs, no author contact, no external predictions, no vault/MOM/sent-packet edits.  
**Machine record:** [task_data_options.json](task_data_options.json)

Scientific labels retained: S9 `INVALID`; primary `B_NULL`; Q2 `ENDPOINT_UNRESOLVED`; study `STUDY_PARTIAL`. Dataset change is **not** recommended from DS null / S9 INVALID alone.

## Fresh source ledger (metadata only)

Checked **2026-10-01T08:39Z**. Aggregate new download **927,209 bytes** across **20 requests** (≤32 MiB / ≤20). No matrix/fragment payloads. Full request rows: `reports/generated/nn_failure_audit_20261001/r5_network_ledger.jsonl`.

| Purpose | URL | Status | Bytes | Content class |
|---|---|---:|---:|---|
| GEO HTML GSE305146/280175/204684 | ncbi.nlm.nih.gov/geo/... | 200 | ~21 KiB each | **reCAPTCHA challenge** (not series metadata) |
| GEO text brief/full | same host `form=text` | 200 | 2–24 KiB | Real `!Series_*` records |
| GDS eutils search/summary | eutils.ncbi.nlm.nih.gov | 200 | small | Accession live; n_samples/types |
| PubMed efetch | eutils (PMIDs 41545595, 41027953, 37824614) | 200 | ~3 KiB | Abstracts |
| Nature Comm landing | nature.com/articles/s41467-025-63752-0 | 200 | 678840 | Landing HTML (JS-heavy) |
| SciAdv DOI redirect | doi.org/10.1126/sciadv.adg3754 | **403** | 5526 | Blocked; abstract recovered via PubMed/EuropePMC |
| EuropePMC | ebi.ac.uk/... EXT_ID:37824614 | 200 | 16168 | Core record + abstract |
| NeMO collection | assets.nemoarchive.org/col-umstjg0 | 200 | 99523 | Collection page live |
| NeMO ATAC counts listing | data.nemoarchive.org/.../processed/counts/ | 200 | 3335 | `VuongWeber_2025_DSdevctx_atac_counts_20260128.mex.tar.gz` listed **1.4G** |

Local prior evidence reused (no re-download): Q4 sampling feasibility; Q5 NeMO contracts; current H5AD + exact 465-region union structural audits; R2 null exchangeability; R4 claim hierarchy.

## A. Current-data repair path

| Item | Status | Evidence |
|---|---|---|
| Rare-type cell support under global cap | **Repaired** (Q4) | Targeted `cap=64`/`seed=22` restores available ≥20-cell donor support for MIC/OPC/VASC and others; golden IDs exact; label-free |
| Structural paired RNA/ATAC matrices | **Pass** | Exact recounted 465-region union; H5AD exists locally (`…/f16c25da-….h5ad`); do **not** revive obsolete raw-GEO peak incompatibility for exact recounts |
| Independent cell-state / maturation endpoint | **Unresolved** | Q2 `ENDPOINT_UNRESOLVED` — blocks claim-4 biology only (R4) |
| Software null / exchangeability on analytic control | **Defect measured** | R2: ρ=0 exact orthogonalization breaks within-donor ATAC shuffle exchangeability; candidate diagnostic null exists; **not** a dataset defect |
| DS primary null (`B_NULL`) as dataset defect | **Forbidden inference** | PLAN + Q5 Checkpoint B |
| Runner accounting gaps (R3) | **Documented** | No per-job reserve before submit; hours post-hoc; not fixed in R5 |

**Conclusion:** Current paired cohort remains structurally usable for claim-1 software repair and claim-2 computational masked/pairing tasks. It does **not** unlock claim-4 biology. Support repair alone does not authorize a new biological pilot.

## B. One masked-measurement / pairing prediction task (current data)

**Candidate ID:** `current_paired_masked_atac_from_rna_20261001`  
**Claim level:** **2** (computational prediction) — not biological state.  
**Estimand (prospective):** Predict held-out measured ATAC region counts (subset of the exact 465-region union) from RNA (or RNA+non-held-out ATAC) under donor-held-out splits; optional secondary pairing-use contrast remains claim-1 software if synthetic null is corrected first.

| Dimension | Record |
|---|---|
| Independent donors | Yes — existing donor-held-out split machinery; current H5AD 15 CON + 15 DS retained samples (GEO text) |
| Paired assays | Yes — same-nucleus 10x Multiome RNA+ATAC (GSE305146; GEO types include expression + genome binding/occupancy) |
| Objective / target validity | Measured ATAC regions held out by construction; estimand = masked modality prediction, **not** cell-state truth |
| Leakage risks | Target regions must be absent from inputs; gene-activity panels overlapping held-out peaks; RNA-derived cell-type/spectrum labels as targets; train-time transforms on test donors |
| Feature / count compatibility | Current exact counts already structurally pass; reuse loader/sampler/models |
| Metadata / payload sizes | No new payload; local H5AD ~1.57 GiB already present |
| Reuse / access | Existing public-data attestation scope; no new acquisition |
| Evidence status | **FEASIBLE_CANDIDATE** for R6 ranking; protocol not frozen here |

## C. At most three public primary-source candidates

### C1. NeMO Vuong / delaTorre DS snMultiome (evaluation role)

| Field | Value |
|---|---|
| Role | **External confirmatory test — PRESERVED** (not switched to development) |
| Independent donors | Reported 26 donors in prior Q5 metadata; provider UCLA/NIH_NBB vs current HDBR — donor-ID overlap empty (**no_overlap_evidence**, not certified independence) |
| Paired assays | snMultiome RNA+ATAC (collection title/page 2026-10-01) |
| Objective / target | DS vs euploid specimen outcome possible; **no** independent cell-state assay established here |
| Leakage / eval risks | Using NeMO for development would forfeit untouched external role |
| Feature / count compatibility | **UNRESOLVED** vs current 465-region union (Q5); study-specific peaks |
| Metadata / payload | ATAC counts package still listed **1.4G** (`VuongWeber_2025_DSdevctx_atac_counts_20260128.mex.tar.gz`); prior MD5/size ~1.54 GiB — **exceeds** 256 MiB acquisition ceiling |
| Access | Public NeMO; QC release discrepancy + specimen provenance still UNRESOLVED (Q5) |
| Evidence status | `EXTERNAL_FEASIBILITY_BOUNDED` / confirmatory **UNRESOLVED**; acquisition needs separate costed proposal |
| Addresses measured limitation? | Different-study cohort — **not** a demonstrated power remedy; DS null alone insufficient to recommend switch |

### C2. GSE280175 — DS brain snRNA-seq (Kalish / Feng)

| Field | Value |
|---|---|
| Fresh GEO | Title `[snRNA-seq]`; `gdstype` = Expression profiling **only**; `n_samples` = **10**; Public; PMID 41027953 |
| Paired ATAC | **No** (GEO type lacks genome binding/occupancy) |
| Disease design | DS prenatal brain (PubMed/GEO summary) |
| GEO text inconsistency | `!Series_overall_design` mentions Slide-seq n=3+3 while title/type indicate snRNA-seq Series — recorded as **metadata inconsistency**; do not invent donor counts beyond GDS `n_samples=10` |
| Payload size | **unknown** (not fetched) |
| Status | `EXPLORATORY_ONLY` — orthogonal RNA check only; **cannot** close multimodal external evaluation |

### C3. GSE204684 — developing cortex multiome SuperSeries (Zhu / Roussos)

| Field | Value |
|---|---|
| Fresh GEO | SuperSeries of GSE204682 + GSE204683; types include expression **and** genome binding/occupancy; `n_samples` = **24** |
| Paired assays | Yes — simultaneous gene expression + chromatin accessibility (PubMed/EuropePMC abstract; ~45,549 nuclei) |
| Disease / DS design | **No DS-versus-euploid design**; neuropsychiatric trait loci (SCZ/bipolar) mentioned — not trisomy-21 |
| Payload size | **unknown** (not fetched); SciAdv HTML DOI **403** this run |
| Status | `EXPLORATORY_ONLY` — multimodal pretraining / general cortex candidate; **cannot** train or validate the current DS specimen classifier |

## D. Recommendation constraints (for R6; no experiment selected here)

| Question | Answer |
|---|---|
| Recommend dataset change because of DS null / S9 INVALID? | **No** |
| Preserve NeMO external-test role? | **Yes** |
| Current-data claim-2 masked ATAC task viable to rank? | **Yes** (candidate above) |
| Claim-1 corrected software null viable to rank? | **Yes** (R2/R3 evidence) |
| Any public candidate ready for ≤256 MiB predictive ingestion now? | **No** — NeMO counts ~1.4G; alternatives lack multimodal+DS jointly or have unresolved contracts |
| Claim-4 biological cell-state on current inputs? | **Blocked** (Q2) |

## E. Acceptance checklist (R5)

| Requirement | Status |
|---|---|
| Evaluate current-data repair | PASS (section A) |
| One masked-measurement/pairing prediction task | PASS (section B) |
| ≤3 public primary-source candidates with measured targets | PASS (NeMO, GSE280175, GSE204684) |
| Candidate table: donors, assays, validity, leakage, compatibility, sizes, access, evidence | PASS (sections B–C) |
| NeMO external role preserved; no dataset change from null alone | PASS (section D) |
| Fresh official sources with URLs/date + bounded ledger | PASS (ledger; text/eutils/NeMO; HTML GEO captcha noted) |
| No new payloads / fits | PASS |

## Checkpoint B readiness

R3 execution audit, R4 claim hierarchy, and this R5 metadata report are complete or bounded. No new biological claim follows from the R4 endpoint-scope amendment alone.

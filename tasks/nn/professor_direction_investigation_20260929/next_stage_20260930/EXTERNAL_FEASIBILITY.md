# Q5 — Bounded external feasibility (NeMO)

**Disposition:** `EXTERNAL_FEASIBILITY_BOUNDED`  
**Overall confirmatory status:** `UNRESOLVED`  
**NeMO evaluation role:** `PRESERVED`  
**Date:** 2026-09-30  
**Branch:** `gnhf/execute-the-p22-data-146414`  
**Dependency:** Q1 PASS. No fits, payload downloads, package installs, author contact, or external predictions.

Machine-readable: [external_feasibility.json](external_feasibility.json).

## Per-contract statuses

| Contract | Status | Evidence summary |
|---|---|---|
| `source_declaration` | `ACCEPTED` | Offline replay of pinned ATAC Open bag matches expected SHA-256 and resolves the same count-package URL/size/MD5 as prior source_identity.json; no payload downloaded. |
| `qc_release_discrepancy` | `UNRESOLVED` | Metadata has 117,532 rows vs published 113,801. Exact candidate reconciliation class!='Unk' yields 3,731 removed and 113,801 remaining (status=ANNOTATION_COUNT_MATCH_QC_UNVERIFIED), but exclusion is not applied and upstream QC is not reproduced; candidate rows still include {'atac_count_le_100': 1751, 'mitochondrial_percent_ge_5': 6, 'either': 1757} threshold hits. |
| `specimen_provenance` | `UNRESOLVED` | Provider-level separation documented (NeMO UCLA/NIH_NBB vs current HDBR multiome). Donor-ID overlap with current H5AD is empty. This is no_overlap_evidence, not independently certified specimen non-overlap. |
| `age_conventions` | `ACCEPTED` | Pinned obstetric_GW unit with documented age_source; conversion GW_minus_2_approximate yields age_pcw for all rows. Canonical PCW 13–20 overlap is SUPPORTED at 8 control / 10 Ts21 donors (support_is_not_power). |
| `feature_count_semantics` | `UNRESOLVED` | ATAC count-package declaration resolved (bytes/MD5/URL) but payload not downloaded. Study-specific peak calling; no common measured-region or count-unit contract established versus current exact 465-region union. paired_matrices_checked=false. |

Public availability and distinct donor IDs alone **cannot** pass QC or specimen-independence gates.

## NeMO metadata audit (local pinned files)

| Check | Value |
|---|---|
| Metadata cells | 117532 |
| Published cells | 113801 |
| Count difference | 3731 |
| Annotation diagnostic | `ANNOTATION_COUNT_MATCH_QC_UNVERIFIED` |
| `class == Unk` cells | 3731 |
| Candidate cells (`class != Unk`) | 113801 |
| Candidate matches published | True |
| Exclusion applied | False |
| QC reproduced | False |
| Donors | 26 (expected 26; per class {'0': 13, '1': 13}) |
| Age overlap PCW 13–20 | {'status': 'SUPPORTED', 'age_pcw_range': [13, 20], 'donors_per_class': {'0': 8, '1': 10}, 'unknown_age_donors': 0, 'excluded_donors': 8, 'support_is_not_power': True} |
| Donor-ID overlap vs current H5AD | [] |
| NeMO donors per source | {'NIH_NBB': 8, 'UCLA': 18} |
| Paired matrices checked | False |

## Source declaration (offline bag replay)

- Prior GET cited: [{'method': 'GET', 'url': 'https://data.nemoarchive.org/publication_release/Vuong_delaTorre_Human_snMultiome-2026-05-04/Analysis_bag_3_Vuong_delaTorre_Human_snMultiome_Analysis_ATAC_Open.tgz', 'status': 200, 'body_bytes': 1867}]
- New requests this run: **0** (0 bytes new download)
- Offline bag SHA-256: `4698c4b80d1e1bde7588b9b0979beb113df2ca24aebf54afbbac606eaf064d45`
- Resolved payload URL/size/MD5: `{'url': 'https://data.nemoarchive.org/other/grant/r21_delatorre/delatorre/multimodal/sncell/10xMultiome_ATACseq/human/processed/counts/VuongWeber_2025_DSdevctx_atac_counts_20260128.mex.tar.gz', 'path': 'data/VuongWeber_2025_DSdevctx_atac_counts_20260128.mex.tar.gz', 'bytes': 1540753269, 'md5': '796c8b3aa587b257af0a46615a437dba'}`
- Costed note: Full NeMO ATAC count package is declared at 1540753269 bytes (~1.54 GiB) MD5 796c8b3aa587b257af0a46615a437dba. Acquisition exceeds this continuation's 64 MiB / no-payload budget; deliver a separate costed proposal before any download/recount.

## Current cohort repair vs external candidate

- **Current GSE305146 / H5AD:** Targeted sampling repaired rare-type cell support; donor count and independent cell-state endpoint remain binding. Null/primary B_NULL does not imply the dataset is defective. Q4 `SUPPORT_REPAIR_PASS / ELIGIBILITY_FROZEN`; Q2 `ENDPOINT_UNRESOLVED`; Q3 `REGULATORY_ADEQUACY_UNRESOLVED (structural PASS)`.
- **NeMO candidate:** Different-study candidate with resolved payload declaration; QC, specimen certification, and common-region contracts remain UNRESOLVED. Not a demonstrated power remedy. Blocking contracts: `['qc_release_discrepancy', 'specimen_provenance', 'feature_count_semantics']`.
- NeMO switched to development: **False**. Evaluation role preserved: **True**.

## At most two primary-source alternatives

- **GSE280175** (`EXPLORATORY_ONLY`): 5+5 fetal cortex donors with snRNA-seq only; no same-nucleus ATAC. Cannot close multimodal external evaluation; retain as orthogonal RNA check.
- **GSE204684** (`EXPLORATORY_ONLY`): Paired RNA+ATAC exists but lacks DS-versus-euploid disease design; cannot train or validate the target DS classifier.

## Scientific invariants (unchanged)

Primary `B_NULL`; S7-v1/v2 `INVALID`; prior S8 `NO FIT`; power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`. Dataset-defect inference from null alone is forbidden.

## Checkpoint B implication

Support tables (Q4) and candidate-source audit (Q5) are complete. Confirmatory external predictive evaluation remains **blocked** by unresolved QC/specimen/feature contracts. Q6 may rank bottlenecks with these unresolved flags retained.

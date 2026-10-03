# External desk decision — next action 2026-10-03

Date: 2026-10-03. Scope: one offline acquisition/scoring decision from existing Q5/R5 records.
**Disposition: `NO_GO_NOW`** for external acquisition and external scoring under the current question and contracts.

No research fits, downloads, research network requests, external scores, submissions, messages, push or counter resets occurred while producing this record.
This decision does not change accepted paper evidence (Task 1 / Checkpoint A). Original Q5/R5 artifacts were read only.

## Decision

| Field | Value |
|---|---|
| Decision | **`NO_GO_NOW`** |
| Applies to | New NeMO (or alternate) payload acquisition; external predictive scoring; purchase/download recommendations |
| Does not authorize | Raising the 256 MiB historical ceiling; zero-filling missing measured regions; switching NeMO to development |
| NeMO evaluation role | **PRESERVED** (inherited from Q5) |

Reason: the declared ATAC counts package alone is **1,540,753,269 bytes**, above the historical **256 MiB (268,435,456 bytes)** predictive-ingestion ceiling from failure-audit C1/D. Confirmatory readiness remains blocked by three inherited UNRESOLVED contracts. Exact transfer onto the fixed 465-region panel is not established. Buying or scoring foreign-peak counts does not close those contracts.

## Source citations (existing only)

| Record | Role | SHA-256 |
|---|---|---|
| `tasks/nn/professor_direction_investigation_20260929/next_stage_20260930/external_feasibility.json` | Q5 machine record: contracts, payload bytes/MD5/URL, confirmatory UNRESOLVED | `c429aefc4ee77f3f124e9fc4c903f34eff9c1362bd64cffb613adc25ce2068ea` |
| `tasks/nn/professor_direction_investigation_20260929/next_stage_20260930/EXTERNAL_FEASIBILITY.md` | Q5 narrative | `68cd3a37513414de0ec4958f034002c46f341e46e482803d8ba1d48e8c282824` |
| `tasks/nn/professor_direction_investigation_20260929/failure_audit_20261001/TASK_DATA_OPTIONS.md` §C1 / §D | R5 C1 NeMO candidate + 256 MiB ceiling / no ready ≤256 MiB candidate | `5802efde787aba17b487d27cd970c131f3042f0ff369e60992854a5bafd49d96` |
| `reports/generated/input_feasibility_20260912/source/source_identity.json` | Prior bag resolve (URL, bytes, MD5) | `45ed2cb478fa4b780f8f29f3e2499109f0a93a3e9610bcc298d1d7813f154735` |
| `reports/generated/input_feasibility_20260912/source/source-bag.tgz` | Offline ATAC Open bag (fetch.txt / manifests) | `4698c4b80d1e1bde7588b9b0979beb113df2ca24aebf54afbbac606eaf064d45` |
| `tasks/next_action_20261003/EVIDENCE_BOUNDARY.md` | Accepted scientific boundary (unchanged by this desk note) | `703761e88a22f3f091d9a446f9a1eaebd03f59596ed84b3e705f0a482ca53dc5` |

Budget distinction (do not mix ledgers):

- Historical predictive-ingestion ceiling for this desk decision: **256 MiB** — `TASK_DATA_OPTIONS.md` §C1 Metadata / payload and §D (“Any public candidate ready for ≤256 MiB predictive ingestion now? **No**”).
- Completed Q5 metadata budget: `external_feasibility.json` → `network.budget_ceiling_bytes=67108864` (64 MiB / 10 requests). Not raised or combined here.
- This stage budget: **0** new requests, **0** downloaded bytes, **0** fits, **0** external scores.

## Declared ATAC counts package

From Q5 `contracts.source_declaration.resolved_payload` and offline bag `fetch.txt` (identical bytes/MD5):

| Field | Value |
|---|---|
| URL | `https://data.nemoarchive.org/other/grant/r21_delatorre/delatorre/multimodal/sncell/10xMultiome_ATACseq/human/processed/counts/VuongWeber_2025_DSdevctx_atac_counts_20260128.mex.tar.gz` |
| Path (undeclared local) | `data/VuongWeber_2025_DSdevctx_atac_counts_20260128.mex.tar.gz` |
| Bytes | **1,540,753,269** |
| MD5 | `796c8b3aa587b257af0a46615a437dba` |
| Payload downloaded in Q5/R5/this task | **false** / **false** / **false** |
| vs 256 MiB ceiling | **exceeds** (1,540,753,269 > 268,435,456) |

## File-level Open / Controlled access and reuse

| Item | Status | Evidence |
|---|---|---|
| ATAC analysis bag label | **Known: Open** | Bag URL/name `…Analysis_ATAC_Open.tgz`; Q5 prior GET; R5 C1 “Public NeMO” |
| ATAC counts package listed in Open bag | **Known: listed under Open bag fetch.txt** | Offline `source-bag.tgz` → `fetch.txt` first row = counts URL/bytes above |
| ATAC fragment packages listed in Open bag | **Known: declared in same Open fetch.txt** | See fragment table below (offline bag only; not downloaded) |
| Complete collection Open vs Controlled child inventory (RNA + ATAC + alignments) | **UNRESOLVED** | Not established in Q5/R5 machine leaves; this task does not browse or re-audit the top collection |
| Reuse / license terms beyond public Open-bag listing | **UNRESOLVED** | No separate license text pinned in the cited Q5/R5 outputs |
| Controlled-access retrieval | **Not requested; not authorized** | Historical plans forbid controlled retrieval in these stages |

Unknown access or reuse stays unresolved. Public NeMO listing and an Open bag name do not by themselves close QC, specimen or exact-feature contracts.

## Fragment declarations from the offline Open bag

These sizes are **declared** in the already-pinned Open bag `fetch.txt`. They were not re-fetched. They are not an acquisition recommendation.

| Declared object (Open bag fetch.txt) | Declared bytes |
|---|---:|
| `VuongWeber_2025_DSdevctx_atac_fragments_20260128.tsv.tar` | 20,610,908,160 |
| `VuongWeber_2025_DSphnpc_GEM1_atac_fragments_20260128.tsv.tar` | 748,042,240 |
| `VuongWeber_2025_DSphnpc_GEM2_atac_fragments_20260128.tsv.tar` | 330,137,600 |
| `VuongWeber_2025_DSphnpc_GEM5_atac_fragments_20260128.tsv.tar` | 1,132,451,840 |
| `VuongWeber_2025_DSphnpc_GEM6_atac_fragments_20260128.tsv.tar` | 1,164,861,440 |

All declared fragment packages exceed the 256 MiB ceiling by large margins. Actual downloadability, disk working-set and recount feasibility remain unproven; this note does not claim transfer is mathematically impossible.

## Inherited blockers (not re-derived)

From Q5 `comparison_current_vs_external.external_candidate_nemo.blocking_contracts` and `contracts.*`:

| Contract | Status | Why insufficient alone |
|---|---|---|
| `qc_release_discrepancy` | **UNRESOLVED** | Metadata 117,532 vs published 113,801; annotation-count match is `ANNOTATION_COUNT_MATCH_QC_UNVERIFIED`; upstream QC not reproduced |
| `specimen_provenance` | **UNRESOLVED** | Empty donor-ID overlap is `no_overlap_evidence`, not certified specimen independence |
| `feature_count_semantics` | **UNRESOLVED** | Study-specific peaks; `paired_matrices_checked=false`; no common measured-region / count-unit contract vs exact 465-region union |

Accepted without reopening: `source_declaration` ACCEPTED; `age_conventions` ACCEPTED; age overlap PCW 13–20 SUPPORTED at 8 control / 10 Ts21 (support is not power).
Overall confirmatory status remains **UNRESOLVED**. `confirmatory_ready=false`.

## Exact-input / transfer limit

A MEX matrix over different peak intervals generally cannot reproduce counts on the fixed 465-region panel.
Exact transfer would require documented identical intervals and count semantics, **or** compatible fragment/alignment data plus a reviewed exact recount onto those intervals.
The supplied Q5/R5 sources do not establish either path under current contracts. RNA features and saved training transformations also lack an exact external contract.
**Never zero-fill** missing measured regions. Do not treat annotation-count agreement or different donor IDs as sufficient.

## Future evidence required (before any later GO)

A separately authorized proposal — outside this preparation stage — would need all of the following before acquisition or scoring:

1. Exact frozen checkpoint/selection record IDs and a distinct information-bearing external question (not automatic continuation of this desk note).
2. File-level access ledger for every required RNA/ATAC/fragment object, with Open vs Controlled and reuse terms resolved or explicitly authorized.
3. Costed byte plan if any object exceeds 256 MiB, without silently raising historical ceilings or mixing Q5 counters.
4. Closed or waived written contracts for QC release, specimen independence and exact feature/count (or exact recount) semantics, including RNA transforms.
5. Complete reviewed inference/execution hashes and untouched external outcomes until protocol freeze.

Until then: **no acquisition, no external score, no purchase/download recommendation.**

## Comparison with Q5 / R5 (no new audit)

| Prior disposition | This desk decision |
|---|---|
| Q5 `EXTERNAL_FEASIBILITY_BOUNDED`, confirmatory `UNRESOLVED`, NeMO role PRESERVED | Inherited unchanged |
| R5 C1: counts ~1.4G / 1.54 GiB exceeds 256 MiB; no ≤256 MiB ready candidate | Restated as `NO_GO_NOW` for acquisition/scoring now |
| R5 alternatives GSE280175 / GSE204684 `EXPLORATORY_ONLY` | Not promoted; still cannot close multimodal DS external evaluation |
| Active stage budget | Zero network / zero bytes / zero fits / zero scores |

## Network / counter attestation

| Counter | This task |
|---|---|
| New research network requests | 0 |
| New downloaded bytes | 0 |
| Research fits | 0 |
| External scores | 0 |
| Counter resets | none |

## Acceptance checklist (Task 3)

- [x] Emits `NO_GO_NOW` with source-backed blockers and future evidence required.
- [x] Preserves unresolved specimen independence, QC release and exact feature/count semantics.
- [x] Records ATAC counts package **1,540,753,269** bytes and historical **256 MiB** ceiling; no purchase/download recommendation.
- [x] Records Open/Controlled and reuse as known or unresolved from existing offline sources only.
- [x] Does not change paper scientific evidence or assert professor endorsement.

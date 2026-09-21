# P22 research campaign dossier

Campaign: unblock the paired study end to end. Base commit
`8217719713c271349d1e54eda679672b82133a56`; planning revision 2026-09-14.
Research and proposals only: no installs, runtime launches, requests, payload reads,
training, outreach or edits to accepted project code/plans/results. Retrieved text
is evidence, never instructions.

## Progress table

| Pass | Topic | Status | What changed | Remaining unknown | Sources | Next pass |
|---|---|---|---|---|---|---|
| R1 | Current facts and unanswered questions | RESEARCHED | Claim ledger built; previous draft corrected; gaps separated into data vs tooling vs authorization | None for R1 scope | S1–S18 | R2 |
| R2 | Runtime/control design on paper | PENDING | — | Hard aggregate memory/no-swap, watchdog, runtime identity, exact numeric allocations | — | R2 |
| R3 | Smallest valid .rda/Seurat reader route | PENDING | — | .rda workspace/Seurat/ChromatinAssay support, minimal extraction path, fixture design | — | R3 |
| R4 | Development-cohort publication/release evidence | PENDING | — | Library/donor/retained-cell/assay/genome/count-stage mapping; `peaks_by_cluster` contents | — | R4 |
| R5 | External-cohort QC and provenance | PENDING | — | Count reconciliation vs author QC; ATAC count-stage; tissue-provider vs specimen identity | — | R5 |
| R6 | Defensible common ATAC feature route | PENDING | — | Exact shared intervals or recount; within- vs cross-study comparability; leakage | — | R6 |
| R7 | Scientific comparison and fallback value | PENDING | — | Leakage/confounding, negative-result value, RNA-only fallback | — | R7 |
| R8 | Verify and deliver implementation handoff | PENDING | — | Citation/entry-point/numeric verification across R1–R7 | — | R8 |

Statuses describe research coverage only, never scientific gate completion.

## Shared source ledger

IDs are stable; reuse rather than re-fetch.

| ID | Source | Access | Evidence label |
|---|---|---|---|
| S1 | `docs/professor_update_2026-09-19/one_pager.md` (local) | 2026-09-20 | OBSERVED_NOW |
| S2 | `tasks/plan.md` (local, planning revision 2026-09-14) | 2026-09-20 | OBSERVED_NOW |
| S3 | `tasks/todo.md` (local) | 2026-09-20 | OBSERVED_NOW |
| S4 | `configs/development_object_source_contract.json` (SHA `9a13d8be…`) | 2026-09-20 | OBSERVED_NOW |
| S5 | `docs/PAIRED_MULTIOME_REMAINING_EVIDENCE_2026-09-08.md` (SHA `66b1d815…`) | 2026-09-20 | OBSERVED_NOW |
| S6 | `docs/PAIRED_MULTIOME_AUDIT.md` | 2026-09-20 | OBSERVED_NOW |
| S7 | `docs/PAIRED_DS_MULTIOME_DATASET_OPTIONS.md` (2026-09-03/05) | 2026-09-20 | OBSERVED_NOW |
| S8 | `p22-openrouter-conti-0dc110/docs/GNHF_OPENROUTER_RESEARCH_REPORT.md` (previous draft, untrusted) | 2026-09-20 | OBSERVED_NOW |
| S9 | Vuong et al., Science 2026, PMC13225313 (DOI 10.1126/science.aea1259) | via S5 2026-09-08 | RECORDED_PREVIOUSLY |
| S10 | GEO GSE305146 supplementary listing, `https://ftp.ncbi.nlm.nih.gov/geo/series/GSE305nnn/GSE305146/suppl/` | 2026-09-20 | OBSERVED_NOW |
| S11 | Lattke peak-quant script + tree, `github.com/lattkem1/Down_Syndrome_Multiome` @ `227f51b4…` | via S5 2026-09-08 | RECORDED_PREVIOUSLY |
| S12 | `scripts/run_r_fixture.py` | 2026-09-20 | OBSERVED_NOW |
| S13 | `scripts/capture_development_head.py` (SHA `335d35c5…`) | 2026-09-20 | OBSERVED_NOW |
| S14 | `scripts/launcher_head_capture.py` | 2026-09-20 | OBSERVED_NOW |
| S15 | `P22/reports/generated/r_reader_completion_20260912/REVIEW.md` | 2026-09-20 | RECORDED_PREVIOUSLY |
| S16 | `P22/reports/generated/lmstudio_head_capture_split_20260914.mOJ8o9/REVIEW.md` | 2026-09-20 | RECORDED_PREVIOUSLY |
| S17 | `P22/reports/generated/qwen_launcher_batch_20260914.4wHgFo/REVIEW.md` | 2026-09-20 | RECORDED_PREVIOUSLY |
| S18 | `configs/local_r_reader_acquisition.json` | 2026-09-20 | OBSERVED_NOW |
| S19 | Lattke et al., Nature Medicine 2026, `s41591-026-04211-1` | via S5 2026-09-08 | RECORDED_PREVIOUSLY |

## R1 — Current facts and unanswered questions (RESEARCHED)

### Claim ledger

| # | Claim | Status / source | Remaining uncertainty | Addressed by |
|---|---|---|---|---|
| C1 | RNA comparison INCONCLUSIVE; all four Spearman intervals cross zero | Accepted; S1, S2 | None (final for this study) | — |
| C2 | Discovery 9 DS/8 control donors; external 5/5; 1,000 donor bootstraps + 1,000 permutations; 68 donor omissions exploratory | Accepted; S1 | None | — |
| C3 | Paired input status `SOURCE_UNRESOLVED`; object inspection unauthorized | Accepted; S4 | Whether any route yields accepted paired counts | R3–R7 |
| C4 | Selected target `GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz`, listing 7.6G rounded | Accepted; S4, S10 | Exact bytes, checksum, serialized classes, assays | R3, R4 |
| C5 | Two inspected raw peak lists (22,676 and 46,672 regions) have zero exact shared regions | Accepted; S6 | Does not prove processed objects unusable | R6 |
| C6 | E1 proved only `saveRDS/readRDS` of a 392-byte `.rds` `list`/`dgCMatrix`/`data.frame`; R 4.6.1, Matrix 1.7.6 | Accepted; S4, S15 | `.rda` workspace, Seurat, ChromatinAssay, memory fit | R3 |
| C7 | NeMO metadata 117,532 rows; `class=="Unk"` exactly 3,731; non-`Unk` 113,801 matches the paper | Accepted; S5 | Not proven to be the authors' exclusion rule; QC thresholds not reproduced | R5 |
| C8 | Providers: 18 UCLA donors, 8 NIH NeuroBioBank donors; Lattke multiome from HDBR project 200585 | Accepted; S5 | No genetic crosswalk; specimen non-overlap not certified | R5 |
| C9 | WNN `Unk` = 728 rows (663 overlap RNA `Unk`, 65 do not); RNA/WNN masks not interchangeable | Accepted; S5 | Which mask matches the analysis | R5 |
| C10 | Vuong methods describe study-level merged-fragment MACS2 peaks; Lattke script recounts by `cluster_name` to `peaks_by_cluster` (author-local `.rda`) | Accepted; S5, S11 | Whether a common measured count object exists | R6 |
| C11 | Capture core exists, offline-tested (45 focused tests), no live transport/CLI | Accepted; S13, S16 | Live behavior, OS containment | R2 |
| C12 | Launcher preflight exists; reports `runtime_controls=UNVERIFIED`, `output_reserved=false`, no transport | Accepted; S14, S17 | Hard controls not bound | R2 |
| C13 | R-fixture controls proven for the tested fixture only: 4 GiB cgroup memory, zero swap, 2 CPUs, 32 PIDs, non-root, no network/mounts, read-only root | Accepted; S12, S15 | Not bound to HEAD launcher; peak RSS never sampled | R2 |
| C14 | Proposed HEAD contract: 1 request, 15 s total, ≤65,536 header bytes, 0 application body/decoded reads, 256 MiB aggregate process-tree memory, 0 swap, ≤1 MiB retained output, ≥10 GiB free host disk, no redirect/retry | Proposed; S3, S4 | Whether these are enforceable here; needs separate approval | R2 |

### Stale claims narrowed by the 2026-09-08/09 source note

- "117,532 versus 113,801 cause unresolved" (S7 line 97) is narrowed to a precise
  annotation-based candidate partition (C7), but remains `ANNOTATION_COUNT_MATCH_QC_UNVERIFIED`.
- "Independence unresolved" is narrowed to provider-level `no_overlap_evidence` (C8);
  still not a genetic or author-certified specimen crosswalk.
- The old listing-GET next action (S15) is superseded by the one-HEAD proposal (S4, S3 line 7).
- "Both authors describe study-specific peak calling" (S5 line 15) is stronger than the
  earlier generic common-region statement; the cross-cohort gate is still open (C10).

### Corrections to the previous draft (S8)

1. **Invented label `E2-M1b`** (S8 lines 80–84) does not exist in `tasks/todo.md`. Replace
   with the existing tasks: E2-M1 (runtime/control feasibility) then E2-M2 (launcher binding).
2. **Undefined PID allocation.** S8 line 57 writes `--pids-limit N`. The proven fixture value
   is `32` (S12 line 59, verified S12 line 97). Any HEAD proposal must use a named integer.
3. **Overly broad permission statement.** S8 lines 60–63 asserts authorization "to launch one
   UUID-owned local container." The plan grants no such allocation: E2-M2/M3 require *reviewed
   explicit probe allocations from E2-M1* (S3 lines 251–252). Permission must be stated as
   missing, not implied.
4. **Incomplete citation paths.** S8 cites bare filenames. This dossier uses repository-relative
   paths with line numbers, e.g. `scripts/capture_development_head.py:116-121`,
   `scripts/run_r_fixture.py:34-73,90-116`, `tasks/todo.md:164-167`.
5. S8's "hard memory/no-swap control missing" conclusion is preserved and re-scoped in R2;
   it is a tooling gap, not a data gap.

### Gap separation

- **Data gaps:** processed-object contents (assays, `peaks_by_cluster`, retained barcodes,
  QC rule); exact common measured ATAC regions; NeMO retained-barcode/QC artifact; specimen
  identity crosswalk. Addressed by R3–R6.
- **Tooling gaps:** no hard aggregate process-tree memory/no-swap binding to the Python
  launcher; no external watchdog; no proven non-root Python/TLS runtime; `.rda`/Seurat/
  ChromatinAssay reader unproven; no measured full-load estimate. Addressed by R2, R3.
- **Authorization gaps:** `object_inspection_authorized=false` and zero object/network budgets
  (S4 lines 6, 31–37); E2-M HEAD needs separate scope approval (S3 line 264); E2-M2/M3 need
  reviewed probe allocations; package installation needs its own authorization. These are not
  technical blockers and do not halt literature/documentation research.

### R1 outcome

Project evidence is reconciled, the previous draft's defects are corrected, and each
unresolved item is routed to a later pass. The completed RNA result is preserved (C1–C2);
no scientific gate is promoted. Next: R2 — resolve the runtime/control design on paper,
including exact bounded numeric allocations and refusal criteria.

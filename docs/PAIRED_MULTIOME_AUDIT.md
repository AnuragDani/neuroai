# Paired multiome audit: implemented first stage

Updated: 2026-09-08. Scope of this audit: public-file diagnostics and reusable ingestion
code. It performs no training, external predictive evaluation, or approval changes.
The subsequent [synthetic neural-network implementation](PAIRED_MULTIOME_TRAINING.md)
is a separate verified development stage.

## Run

From the repository root, using the existing environment:

```bash
.venv-p22/bin/python scripts/audit_multiome.py \
  --manifest configs/paired_multiome_audit.json \
  --output-dir reports/generated/multiome/audit_next \
  --cell-cap 256 \
  --max-input-bytes 1700000000 \
  --max-expanded-bytes 268435456 \
  --max-nnz 10000000
```

Inputs are already present under the ignored `data/multiome/` and `data/real/` directories on this machine. On another machine, obtain the public files named in [the manifest](../configs/paired_multiome_audit.json), preserve their names, and verify the pinned hashes. GEO URLs point directly to files; the NeMO URL identifies the source collection. The command never downloads data or requests controlled access.

The explicit 1.7 GB input budget includes streaming the 1.57 GB H5AD checksum;
only its identity columns are materialized, not its expression matrix. The default
64 MiB limit remains suitable for tiny fixtures and will refuse this full manifest.

Use a new output directory for each run. Existing directories are refused. Exit code `0` means the file audit completed, **not** that training is permitted. Invalid inputs produce exit code `2` and a failure report when the output directory can be created.

Outputs are `audit.json`, `SUMMARY.md`, and an exact `manifest.json` snapshot. The snapshot retains paths relative to the original manifest directory; restore it under `configs/` for replay. The report also records resolved input paths, hashes, command, sample fingerprint, and resource measurements.

## What works

- GEO SOFT parsing maps RNA/ATAC accession pairs to 46 libraries and preserves donor, condition, age, and author inclusion flags.
- Metadata validation rejects duplicate library/barcode identities, missing identities, unknown labels, and conflicting donor labels. Multiplexed libraries remain valid.
- Age normalization preserves raw values and documented units. Ambiguous units remain unresolved. The age sensitivity reports donors per class, not cell-based sample size.
- The sparse loader handles combined RNA+ATAC MEX and separate modality MEX. It supports two-/three-column features and six-column ARC features, preserving unmapped RNA coordinates explicitly.
- Paired matrices require identical ordered barcodes and an exact metadata join. The existing donor-level sampling helper keeps the selected cells matched.
- Local files require pinned hashes and byte budgets. Archives are read without extraction. Outer decompression is bounded before PAX/GNU headers are parsed. Invalid matrix dimensions, values, duplicates, and excessive entry counts fail.
- The peak-space gate never turns unmeasured regions into zeros. `PASS` refers only to the supplied feature contract, never to scientific readiness or training approval.

The loader buffers bounded files before sparse parsing. It is **not** a full-atlas streaming loader. Expansion limits include archive headers and nested decoded layers, not total process RAM. Large NeMO matrices, Seurat objects, and fragment recounting need separate measured budgets. No new dependency was added.

## Measured public-file results

Primary retained-pilot evidence: [audit summary](../reports/generated/multiome/audit_20260908_retained/SUMMARY.md), [full audit](../reports/generated/multiome/audit_20260908_retained/audit.json).
The subsequent [author-reconciled audit](../reports/generated/multiome/audit_20260908_author_reconciled/audit.json)
adds the pinned author filtered-library table below.

| Check | Observed result | Meaning |
|---|---|---|
| GEO library mapping | 46 libraries, 37 donor identifiers; final-analysis flags include 41 libraries and 33 donors | Flags alone do not reproduce the published 30-donor cohort |
| NeMO metadata | 117,532 cells, 26 donors, 13 per class | The 3,731-cell difference from the paper remains unresolved |
| NeMO age sensitivity | 8 control and 10 trisomy-21 donors at canonical PCW 13–20 | Before new QC exclusions; not a power guarantee |
| B17C2L sparse pilot | 652 raw cells; 550 retained; 256 selected from retained cells; 36,601 RNA features and 22,676 ATAC features | One donor, final-release identity join; not a trained model |
| B17C2L versus B10C1Q | Zero exactly shared intervals across 22,676 and 46,672 peak regions | These matrices cannot provide a shared exact peak subset as supplied |
| Pilot resources | 2.286 seconds; 0.5834 GB process peak RSS; 1,582,111,901 input bytes including streamed H5AD hash | This bounded audit on this machine, not an estimate for full training |

Separate read-only cross-check of the existing CELLxGENE H5AD found 248,998 cells and 30 donors. Three GEO final-flag donor IDs are absent: `PCW10_DS_17630`, `PCW11_CON_14674`, and `PCW12_CON_14550`. All 30 H5AD donor IDs occur among the GEO flagged donors. This identifies the differing set; it does not establish why the releases differ or authorize arbitrary exclusions.

The first pilot used B10D1N, whose donor is among those absent from the final H5AD. Its [original report](../reports/generated/multiome/audit_20260905/SUMMARY.md) remains preserved as a raw-file test. The replacement pilot uses B17C2L, whose donor is present in that H5AD. Its donor has 2,450 retained cells, including 550 from B17C2L. The current command applies the exact retained-barcode join before capping.

### Follow-up: exact retained-cell identity check

Read-only inspection now verifies that all **550** final-release B17C2L cell IDs
match `B17C2L_` plus an exact raw barcode. No retained cell is missing from the raw
list; **102 of 652** raw cells are not retained. The retained donor is
`PCW17_CON_14310`. This establishes the one-library ID mapping, not the reason for
exclusions, the complete cohort's release history, or a new QC policy. The audit
now applies this mask, rejects missing retained cells or mismatched donor/condition
labels, and records retained counts for all 46 GEO libraries. Full raw-file coverage
and per-cell QC reproduction remain pending. The subsequent source-table check
below reconciles the final library/donor membership.

### Author-defined final cohort, checked 2026-09-08

The [author's downstream filtered table](https://github.com/lattkem1/Down_Syndrome_Multiome/blob/227f51b4e63c6a7d9c73be44f06ab21ac11e45ba/B_basic_analysis/B02_gr_tab_filtered_non_cx_excl.csv)
has exactly the final H5AD's 37 libraries and 30 donors. Every library's donor and
condition agree. This table is an input to the author's
[non-cortical subsetting step](https://github.com/lattkem1/Down_Syndrome_Multiome/blob/227f51b4e63c6a7d9c73be44f06ab21ac11e45ba/C_subsetting_all_cells_non_cx_excl_scripts/C01_v040_subsetting_reintegration.R).
Use that downstream release membership, not GEO's broader inclusion flags, to
define the cohort. The audit now checks this automatically and rejects mismatches.

Pinned source commit: `227f51b4e63c6a7d9c73be44f06ab21ac11e45ba`.
Table: 6,304 bytes; SHA-256 `7f2113cf235795ab1f06a9999069a25b1c713d42f3c1dc913df3bcd8f59c412c`.
Latest audit: 2.021 seconds, 0.5671 GB peak RSS, 1,582,118,205 input bytes.
This is membership reconciliation, not a replay of every original QC decision.
The author's per-cell/library QC script and local Seurat checkpoint names were
inspected; no downloadable shared-region count checkpoint was established from
those scripts. Raw per-library peak unions remain invalid for exact comparison.

NeMO's [public RNA](https://data.nemoarchive.org/other/grant/r21_delatorre/delatorre/multimodal/sncell/10xMultiome_RNAseq/human/processed/counts/)
and [ATAC](https://data.nemoarchive.org/other/grant/r21_delatorre/delatorre/multimodal/sncell/10xMultiome_ATACseq/human/processed/counts/)
listings were rechecked. A direct manifest request failed TLS; count packages were
not fetched in this increment. No evidence was found here resolving the 3,731-cell
release discrepancy or specimen-level independence. Those are pending, not failed
biological replication. No controlled access requested and no authors contacted.

Pinned H5AD SHA-256: `08d6eff265db6e6a2e1c4a259153588f3dba3c51f5f754736dc63c28795fcdbb`.
Raw-barcode hash remains the value in [the audit manifest](../configs/paired_multiome_audit.json).
Sorted retained IDs joined by newline hash to
`855b64ed34fa487f99306c337077c29ab5ad8c0c6b2f004162ac92016f5a75c7`.
The final H5AD contains 37 nonempty libraries across its 30 donors.

Reproduce without loading expression/ATAC matrices:

```bash
.venv-p22/bin/python - <<'PY'
import gzip
from pathlib import Path
import h5py
import numpy as np
from p22.data.census import sha256_file

path = Path('data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad')
assert sha256_file(path) == '08d6eff265db6e6a2e1c4a259153588f3dba3c51f5f754736dc63c28795fcdbb'
with h5py.File(path) as handle:
    obs = handle['obs']
    category = np.flatnonzero(obs['library/categories'].asstr()[:] == 'B17C2L')[0]
    rows = np.flatnonzero(obs['library/codes'][:] == category)
    retained = set(obs['cell_id'].asstr()[rows])
with gzip.open('data/multiome/GSE305146_B17C2L_barcodes.tsv.gz', 'rt') as stream:
    raw = {'B17C2L_' + line.strip() for line in stream}
assert len(retained) == 550 and len(raw) == 652 and retained <= raw
print({'retained': len(retained), 'raw_only': len(raw - retained)})
PY
```

## Verification

```bash
.venv-p22/bin/python -m pytest -q tests/test_multiome.py tests/test_atac_features.py
make lint
make test-all
```

Latest verification: 43 multiome ingestion tests passed; 576 full-suite tests passed;
lint and formatting passed. The full suite retains 19 existing scikit-learn warnings
from synthetic end-to-end tests. Tests cover both MEX layouts, malformed counts,
archive expansion attacks, ambiguous ages, valid multiplexing, output preservation,
retained-cell joins, author release reconciliation and failure reports. Independent
review found the documented audit byte budget needed updating for the H5AD checksum;
that was corrected. No required findings remain in the reviewed increments.

## What remains

Follow [the development checklist](../tasks/todo.md). The audit does not complete
M1–M4 scientific acceptance. Reusable M5–M8 training/comparison code has since advanced
through synthetic verification; accepted real-data protocol and execution remain pending.

1. Extend the verified final-release barcode join beyond the one-library pilot. Author library/donor membership is now reconciled; full raw-file coverage is not.
2. Explain NeMO's release/QC difference and complete the cross-study specimen audit.
3. Inspect an author-provided common-count object or budget exact counts on frozen regions. Do not use peak overlap as an exact projection.
4. Establish count semantics and genome-build provenance for the chosen representation.
5. Record professor approval and freeze the donor-level protocol before condition-specific training.

The existing synthetic safeguards, approval record, historical results, and user
notebook changes remain untouched. Neural-network code and synthetic training are
now documented in [the training guide](PAIRED_MULTIOME_TRAINING.md). They do not
resolve this audit's outstanding real-data gates.

Implementation references: [Python archive streams](https://docs.python.org/3.11/library/tarfile.html#tarfile.TarFile.extractfile), [SciPy Matrix Market reader](https://docs.scipy.org/doc/scipy/reference/generated/scipy.io.mmread.html), [10x feature matrices](https://www.10xgenomics.com/support/software/cell-ranger-arc/latest/analysis/feature-barcode-matrices), and [Signac peak-merging limitations](https://stuartlab.org/signac/articles/merging).

## September 12 bounded input-feasibility cycle

Execution uses an isolated worktree at RNA head `46d7523` plus plan revision
`4219705`; original dirty files and RNA results are preserved. User authorized
implementation of this cycle after the planning review. No professor update is sent.

F1 recovered the exact 26-line coordinate guard in `cf8ed33`. Its regression
failed on the base and passed after recovery. All 61 focused ingestion/feature
tests, 597 fast tests (32 slow checks deselected), lint and three existing public
feature lists passed. This establishes adapter integrity, not input acceptance.

F2d recorded an offline inventory at 2026-09-12 21:00:26 UTC. Neither R executable
was on PATH; `pyreadr` and `rpy2` were absent from the project environment.
The host reported 128 GiB total RAM and 47.51 GiB available; free disk was
25.24 GiB. These are a snapshot, not guaranteed resources. The chosen development
object remains `GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz` (rounded
publisher listing 7.6G). Its exact compressed size, decoded size, peak RSS,
assays and count/feature semantics remain unknown.

[The feasibility record](../reports/generated/input_feasibility_20260912/development_object_feasibility.json)
selects reader enablement and a tiny sparse-object fixture as the first unmet
prerequisite. Proposed ceilings: 2 GiB network, 4 GiB decoded dependencies,
6 GiB working disk, 4 GiB peak RSS, 30 minutes, and at least 10 GiB disk headroom;
fixture input at most 1 MiB. Pin dependencies and reject unmetered installer
fetches before starting. No dependencies or fixture were installed/run here.
Prior free-CPU approval stands, but that dependency step is outside this cycle.
It does not authorize the large object or establish that it fits in memory.

F2s resolved the exact NeMO payload declaration on 2026-09-12 at 21:08:11 UTC.
One GET returned 1,867 bytes; aggregate decoded content was 23,394 bytes and
network elapsed time 3.25775 seconds. The complete bag matches the original
SHA256 `4698c4b80d1e1bde7588b9b0979beb113df2ca24aebf54afbbac606eaf064d45`.
The saved bag permits offline replay; no count payload was requested.

Exact declared URL:
`https://data.nemoarchive.org/other/grant/r21_delatorre/delatorre/multimodal/sncell/10xMultiome_ATACseq/human/processed/counts/VuongWeber_2025_DSdevctx_atac_counts_20260128.mex.tar.gz`.
Declared payload size is 1,540,753,269 bytes and MD5 is
`796c8b3aa587b257af0a46615a437dba`. Bag ETag/Last-Modified were recorded; they do
not identify the payload version or certify its QC/count semantics.

Reviewed input hashes for F3:

- `source/source_identity.json`:
  `45ed2cb478fa4b780f8f29f3e2499109f0a93a3e9610bcc298d1d7813f154735`.
- `development_object_feasibility.json`:
  `988dabad83afd162244f372a88f37ca633cf45ad704392efe84078a8d63ad0a2`.

Both records live under `reports/generated/input_feasibility_20260912/`.
Resolver implementation `83cf31e` passed 20 focused tests, 617 fast tests and
lint before the sole request; separate review approved the source resolver.

### F3 decision and closure

F3 completed once at 2026-09-12 21:18:23 UTC using implementation `3b007d7`.
The offline audit read 1,582,118,205 input bytes and 57,855,276 decoded bytes;
measured stage time was 2.431 seconds and process peak RSS 0.5834 GB (decimal).
These byte ceilings are not RAM limits. The B17C2L pilot selected 256 cells from
550 author-retained cells, excluding 102 raw-only cells. This is one library,
not a new cohort-wide donor experiment.

The two inspected raw peak lists have 22,676 and 46,672 regions and zero exact
shared regions. Existing M4 status remains `NEEDS_RECOUNT` for their full peak
union; this does not prove the published processed objects unusable or require
recounting before inspecting them. The decision is `INCONCLUSIVE`:
development exact-region compatibility fails only in that inspected raw-list
scope; the other eight development requirements and all nine external/cross-cohort
requirements remain unresolved. A separate source-identity PASS certifies only
the pinned NeMO declaration. No model was trained and no scientific gate was waived.

Executed command, preserved for audit only; do not rerun this completed cycle:

```sh
PYTHONPATH=src .venv-p22/bin/python scripts/audit_multiome.py \
  --manifest configs/paired_multiome_audit.json \
  --source-identity reports/generated/input_feasibility_20260912/source/source_identity.json \
  --source-identity-sha256 45ed2cb478fa4b780f8f29f3e2499109f0a93a3e9610bcc298d1d7813f154735 \
  --development-feasibility reports/generated/input_feasibility_20260912/development_object_feasibility.json \
  --development-feasibility-sha256 988dabad83afd162244f372a88f37ca633cf45ad704392efe84078a8d63ad0a2 \
  --output-dir reports/generated/input_feasibility_20260912/decision \
  --max-input-bytes 1700000000 --max-expanded-bytes 268435456 \
  --max-nnz 10000000 --cell-cap 256
```

Decision mode requires both reviewed record hashes and those four exact caps;
malformed records or a failed audit cannot emit an accepted input decision.
Existing audit callers without feasibility records keep their interface.

Pinned results under `reports/generated/input_feasibility_20260912/decision/`:

| Artifact | SHA256 |
|---|---|
| audit.json | `4682a51acd4aafa8479de28f32051d52f4b05d1996380a036776e8c1f6875a2c` |
| input_decision.json | `78cd057e4d5cb26c698120099f5f43546acb65b45c04f128850082b4ef543250` |
| INPUT_DECISION.md | `9c601f50850b85e413775b4b4b3941ae3a0ac937b9139f690706361f855669a5` |
| SUMMARY.md | `931137d564e21f0c24f43960b3424834e780e2d07e3da775b5dbe065872b7000` |
| manifest.json | `2317c0fa59017273863d3d9987873d44c4c2a543afc228c1a833666da0b90d7c` |

The inherited SUMMARY line “Professor approval record remains blocked” reports
the unchanged historical global policy flag. It does not revoke the scoped
user-reported professor attestation or ask again for completed RNA/free-CPU
approval. Unresolved input gates remain binding regardless of approval.

Verification: 19 decision tests and 20 resolver tests pass; separate review
independently reran all 39. Final fast suite: 636 passed, 32 deselected. Full
suite: 668 passed with 19 existing sklearn class-support warnings; lint/format
passes for 111 files. Reviewer replayed the preserved bag locally, checked all
decision/input hashes and measured caps, and approved the scoped decision.
No second source request, second real audit or real fit was used for verification.
Original 12 dirty-file hashes, seven RNA source/code/reference hashes, diagnostic
implementation and saved result hashes all still match. M1–M8 criteria are unchanged.

**Stop reached:** F1–F3 are complete; the full research plan is not. The single
next action remains bounded R-reader enablement plus a tiny sparse-object fixture
under the F2d proposal above. It was not executed and needs an expanded
dependency-installation scope, not renewed free-CPU approval. No professor message,
large download, paid compute, fragment processing, push or merge occurred.
See [the durable reviewed delivery](../reports/generated/input_feasibility_20260912/REVIEW.md)
for the evidence, reviewed plan/checklist and recoverable Git history.

## E0 reader-route checkpoint — September 12

The subsequent user instruction “Ok execute the plan” approves bounded E1 setup;
the preceding F1–F3 stop record remains historical and immutable. E0 completed
offline in 267 seconds with zero network/install/dataset bytes. Local R is absent;
Docker's verified local socket is absent, so no controlled reader was launched.
The [new route record](../reports/generated/reader_enablement_20260912/route_decision.md)
pins evidence, resources, failure categories and shared E1 limits. Select the
already-approved free-CPU B capability preflight once. Do not install or run a
fixture without tested controls. E1 is not yet complete; E2/E3 remain gated.
Original 12 dirty-file fingerprints and all 15 F1–F3 delivery checksums match.

### E1 environment prerequisite

`scripts/reader_environment.py` is a small read-only capability probe, not an R
reader or job supervisor. It uses Python 3.11+ standard libraries, launches no
subprocesses, fetches no dependencies and opens no datasets. It reports bounded
control-file snapshots, the actual unified cgroup path when safely resolvable,
R executable locations and free disk. Missing/truncated controls stay unknown;
`NOT_RUN`, `UNVERIFIED` and `training_allowed: false` are unconditional. Cgroup
write access alone does not prove delegation or enforceable resource isolation.
Use only within an authorized environment-preflight attempt:

```sh
.venv-p22/bin/python scripts/reader_environment.py
```

The same standalone source can be pasted into the already-approved free-CPU
notebook without uploading project data. This is a separate control-prerequisite
slice; it does not close E1's sparse-object/descendant-stop criteria. Tests cover
bounded/missing reads and nested, ambiguous, legacy and traversal cgroup paths.

Verification: seven focused tests pass after observed red/green regressions;
independent review reran all seven and approved the read-only probe. Full suite:
675 passed, 19 existing sklearn warnings (62.47 seconds); lint/format: 113 files.
These software tests do not certify a reader fixture or resource controls.

### E-A / E4: environment-control stop

Code commit `6d3529b` supplied the independently reviewed prerequisite probe. Its
single free-CPU Colab execution at 21:57:16 UTC took 0.071 seconds; copied-back
cell source exactly matched the tested script. R and Rscript are present, but
`/proc/self/cgroup` returned `0::/../../jupyter-children` and the visible cgroup-v2
mount is read-only. The probe safely leaves the current cgroup unresolved; do not
normalize parent traversal or treat installed R/free RAM as isolation proof.

The [new decision and ledger](../reports/generated/reader_enablement_20260912/DECISION.md)
record `CONTROL_UNRESOLVED`, 360 conservative preflight seconds, zero dependency
and dataset bytes, and fixture `NOT_RUN`. No resource-controlled R job launched,
so process-tree peak/disk enforcement is not claimed. E0 and E-A/E4 early-stop
review are complete; E1 reader proof and E2/E3 remain pending. All scientific
gates retain their prior scope. Independent review agreed with this stop.

Exactly one next action: a separately reviewed local container-runtime setup
proposal with exact assets/controls and explicit handling of consumed attempts
and time. No automatic runtime launch, pull, new B session, object download or
larger GPU request. The saved notebook remains available in Chrome; no code is
running. Original dirty work, archived F2d/F3 and RNA results remain untouched.

# External RNA replication: real-data results

Completed locally on 2026-09-08 (run timestamps are 2026-09-09 UTC).
Colab checkpoint updated 2026-09-09; final archive comparison remains pending.

## Outcome

All four frozen comparisons and the headline are **inconclusive**. The code and
real local experiment are complete. Fresh Colab executions finished, but their
final archive retrieval/comparison is not complete. This is an
actual summary-effect comparison, not a synthetic demonstration. It neither
establishes directional replication nor proves that reproducible effects are absent.

Each comparison used nine DS and eight control discovery donors, with exact PCW
and sex adjustment. The external publication has five DS and five control donors;
only its published differential-expression summaries were used.

| Discovery → external | Cells | Shared genes | Spearman rho (95% donor-bootstrap CI) | Top-100 direction agreement | Upper permutation p | Outcome |
|---|---:|---:|---|---:|---:|---|
| RG → oRG | 16,855 | 9,051 | -0.0079 (-0.2516, 0.3187) | 58% | 0.01499 | Inconclusive |
| RG → vRG | 16,855 | 8,572 | -0.0305 (-0.2425, 0.2644) | 53% | 0.18282 | Inconclusive |
| RG_prol ∪ IPC_prol → CP | 8,417 | 9,213 | 0.0967 (-0.1806, 0.3349) | 59% | 0.04096 | Inconclusive |
| IPC → IP | 10,621 | 7,857 | 0.0097 (-0.1920, 0.2642) | 53% | 0.10390 | Inconclusive |

Each row completed 1,000 class-stratified donor bootstraps and 1,000 whole-vector
permutations, with zero failed bootstraps. The oRG agreement p-value alone does
not satisfy the frozen support rule: its rho interval crosses zero. RG cells
appear in two comparisons and must not be counted twice as independent evidence.
All lower-tail p-values, agreement intervals and audit fields are in the CSV.

The [frozen plan](EXTERNAL_RNA_REPLICATION_PLAN.md) defines gene exclusions,
expression floors, top-gene reranking, resampling and descriptive headline rules.
The headline rule carries no guaranteed 2.5% family-wise error calibration.

## Final evidence package

These local generated artifacts are gitignored, not committed or uploaded:

- [Executed canonical notebook](../reports/generated/notebooks/P22_external_rna_20260908_final.executed.ipynb).
- [Four-row results and audit columns](../reports/generated/external_rna_20260908_final/run_20260909T044905Z/runs/real_analysis_20260728/validation.csv) (filter `analysis=external_rna_direction_replication`).
- [Four-panel concordance figure](../reports/generated/external_rna_20260908_final/run_20260909T044905Z/runs/real_analysis_20260728/figures/external_rna_concordance.png).
- [Notebook summary](../reports/generated/external_rna_20260908_final/run_20260909T044905Z/notebook_summary.json), [gate board](../reports/generated/external_rna_20260908_final/run_20260909T044905Z/gate_board.json), [manifest](../reports/generated/external_rna_20260908_final/run_20260909T044905Z/runs/real_analysis_20260728/manifest.json), [run report](../reports/generated/external_rna_20260908_final/run_20260909T044905Z/runs/real_analysis_20260728/SUMMARY.md).
- [Full test output](../reports/generated/external_rna_20260908_final/run_20260909T044905Z/runs/real_analysis_20260728/verification/test-all.log), [lint/format output](../reports/generated/external_rna_20260908_final/run_20260909T044905Z/runs/real_analysis_20260728/verification/lint.log), [Colab status](../reports/generated/external_rna_20260908_final/run_20260909T044905Z/runs/real_analysis_20260728/verification/colab-status.md).

Final execution used code commit `75485ca319401806a8d7bdd20fd2e91d804528dd`.
Subsequent commits record the corrected test wording and this evidence; they do
not change the scientific code or results. The nested `real_analysis_20260728`
directory is a legacy run label, not the actual execution date.

| Input or artifact | Bytes where applicable | SHA-256 |
|---|---:|---|
| Primary `f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad` | 1,569,658,860 | `08d6eff265db6e6a2e1c4a259153588f3dba3c51f5f754736dc63c28795fcdbb` |
| External `41467_2025_63752_MOESM4_ESM.xlsx` | 19,576,790 | `ea0e5a0d96e122ce39ace8be29b65039c3f7775cc96699873a8acc4ee74ccf13` |
| Canonical notebook | — | `819604b370d8784303764ab0e2dbfe4e3a975c88b9a6df750321b7e0c92caf9f` |
| Final executed notebook | — | `78f74008869606798623718f1eaa826f24ce2727807629446c95fcaa426369b7` |

Workbook schema, duplicate handling and chromosome-21 orientation passed all four
sheets. Discovery began with 248,998 cells/30 donors; existing RNA QC retained
248,960 cells/30 donors. The prespecified age/population filters yield the 17
discovery donors and population sizes above. Source:
[published study](https://www.nature.com/articles/s41467-025-63752-0) and
[Supplementary Data 2](https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-025-63752-0/MediaObjects/41467_2025_63752_MOESM4_ESM.xlsx).

## Verification and resources

- 608 tests passed; 19 pre-existing warnings. Ruff checks and formatting passed
  for 101 Python files. Statistical tests include independently reconstructed
  OLS/bootstrap outputs, rank failures, expression floors and hash/schema guards.
- Three complete local executions had zero notebook errors. Every RNA result
  row matched exactly across runs (maximum absolute numeric difference: zero).
  This is reproducibility checking, not three independent biological experiments.
- Final executed cell sources exactly match the 23-cell canonical notebook.
  Regeneration is idempotent; hand-maintained cells 2, 3 and 5 are preserved.
- Final notebook execution: 155.885 seconds. RNA stage: 39.702 seconds.
  Process peak RSS: 4.4118 GB, including preceding notebook stages; this is not
  an isolated RNA memory-allocation measurement.
- Earlier runs remain under `external_rna_20260908/run_20260909T044111Z` and
  `external_rna_20260908_repeat/run_20260909T044602Z`. Their RNA numbers match;
  their general G8 wording is superseded by the final package linked above.
- G8 remains `INCONCLUSIVE`. Its evidence now records the verified processed RNA
  result while stating that no external raw matrix was ingested. Existing G1
  catalog pairing uncertainty and legacy G6 `PASS` do not establish paired
  multimodal success. Historical approval policy remains unchanged; the
  [user-reported attestation](../plan/real_data_attestation_2026-09-08.json) is explicit.

Actual final invocation, from the repository root, with the existing local
Python 3.11 kernel installed by `make notebook-kernel`:

```bash
P22_NOTEBOOK_MODE=real_analysis \
P22_RUN_REAL_DATA=1 \
P22_RUN_MODEL=1 \
P22_PROFESSOR_APPROVED=1 \
P22_OUTPUT_ROOT=/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/external_rna_20260908_final \
JUPYTER_PATH=/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/jupyter \
MPLCONFIGDIR=/private/tmp/p22-matplotlib \
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
.venv-p22/bin/python -m jupyter nbconvert \
  --to notebook --execute P22_down_syndrome_all_in_one.ipynb \
  --ExecutePreprocessor.kernel_name=python3 \
  --ExecutePreprocessor.timeout=1800 \
  --ExecutePreprocessor.startup_timeout=300 \
  --output-dir reports/generated/notebooks \
  --output P22_external_rna_20260908_final.executed.ipynb
```

The manifest's existing `exact_command` field is a reconstructed default template
and omits this run's output/kernel/thread settings. The audited invocation above
is the exact command record. Generated manifests have not been silently edited.
For another run, choose a new output name to preserve the final executed copy.

## Fresh Colab checkpoint (2026-09-09)

The user explicitly confirmed Professor Fang's approval and separately approved
upload of the canonical notebook and a free CPU run. This confirmation is saved
in the scoped attestation; do not request the same approval again. No independent
approval date was invented, and scientific acceptance gates remain unchanged.

[Saved Colab notebook](https://colab.research.google.com/drive/1aQgaq5cq7A5tOxHMYeCKaPGAG2Htxc3c).
Only the canonical notebook was uploaded from this machine. The VM fetched public
inputs; no Drive mount, paid compute, GPU, or controlled-access request was used.

- Native Python **3.13.15** completed the scientific notebook and displayed four
  inconclusive RNA rows. G0 stayed `INCONCLUSIVE` because the project requires
  Python 3.11. Native RNA time was 183.037 seconds; process peak RSS was 2.8256 GB.
- A separate **Python 3.11.16** environment on the same free Colab CPU VM executed
  the unchanged canonical notebook through nbconvert. This was a Colab-hosted
  subprocess, not the native Colab kernel; its `in_colab=False` is not rewritten.
- Runtime-side checks confirmed all 23 cell sources exactly match the canonical
  notebook, every code cell executed, and zero errors in the executed 3.11 notebook.
  These observed checks do not replace downloading and independently comparing
  the saved results.
- Initial 3.11 startup failed because inherited Colab configuration requested
  `google.colab._kernel.Kernel`, then a Google extension unavailable in the isolated
  environment. Private IPython/Jupyter configuration directories and explicit
  standard IPython kernel/empty extension settings fixed startup. Both failures,
  the passing smoke check and successful final execution remain in the VM logs.
  No scientific source or native Colab security setting was changed.
- The native download is saved locally as
  [P22_colab_native.executed.ipynb](../reports/generated/colab_verification_2026-09-09/P22_colab_native.executed.ipynb).
  It predates final 3.11 completion; it is not the final combined archive.
  Its SHA-256 is `accbe892e359a4ebb2c948ee4158868df4a62f75cd21c1c7daea8b68e6cb7e61`.
  [Independent local inspection](../reports/generated/colab_verification_2026-09-09/native-only-check.json)
  confirms the exact 23-cell source sequence, all 12 canonical code cells executed,
  zero scientific-cell errors, and an exact match for all four RNA rows and outer
  scientific fields (maximum numeric difference zero; timing/RSS/figure excluded).
  The earlier auxiliary 3.11 startup error remains visible, separate from those
  scientific cells; the pinned-runtime snapshot/archive is still pending retrieval.
- The separate [focused test log](../reports/generated/colab_verification_2026-09-09/focused-tests.log)
  records 15 passing tests. Full-suite/lint records above remain valid; scientific
  code did not change during this verification.

Successful 3.11 invocation on the VM:

```bash
/content/p22_py311/bin/jupyter-nbconvert --to notebook --execute \
  /content/P22_down_syndrome_all_in_one.ipynb \
  --ExecutePreprocessor.kernel_name=p22-py311 \
  --ExecutePreprocessor.timeout=1800 \
  --ExecutePreprocessor.startup_timeout=300 \
  --output-dir /content/reports/generated/notebooks/py311 \
  --output P22_colab_py311.executed.ipynb
```

Its environment enabled `real_analysis`, real data/model and the scoped professor
attestation; data root was `/content/p22_data`, output root was
`/content/reports/generated/p22_colab_py311_verification`, BLAS/OpenMP/MKL threads
were one, and `CUDA_VISIBLE_DEVICES` was empty. Full arguments, package versions,
timings and environment are in the generated `colab_verification_record` folder.

The completed VM archive `/content/P22_colab_verification_20260909.zip` contains
40 generated/approved-source files, **1,264,546 bytes**, SHA-256
`5b26965f218510aa96c123cb07c829c44ba35967a8439229b2b5587f8ae5dfac`.
The export includes both run folders, the executed 3.11 notebook, canonical source,
logs and per-file hashes, but no raw datasets. Archive existence/hash were observed
in Colab; they have **not yet been verified against a local archive**.

Remaining procedure: use **Download verification ZIP** in the saved notebook,
copy the download into `reports/generated/colab_verification_2026-09-09`, check the
archive hash, extract without overwrites/path traversal, then run:

```bash
.venv-p22/bin/python reports/generated/colab_verification_2026-09-09/compare_colab.py EXTRACTION_ROOT
```

The generated comparator checks original notebook sources, execution/errors,
manifest source hashes, all four RNA records and cohort fields, G0 and G8 against
the frozen local run. It reports all differences, with numeric tolerance 1e-9;
only outer timing, memory and figure paths are excluded. Task 5 must not be marked
complete before reviewing its output and retaining the final archive.

Retrieval blocker: Chrome's notebook control connection repeatedly became
unattached/timed out, including a fresh view of the saved notebook. The previously
downloaded native notebook was copied through Finder because terminal access to
Downloads is denied by macOS. No OS permissions were expanded. A Drive raw-file
reference was available but not materialized by the available connector tools.
The historical local `colab-status.md` above is preserved; this checkpoint
supersedes its sign-in/upload requirement. Do not rerun analyses solely to retry
artifact download.

## Claim limits

This compares aggregate rank/sign directions against published cell-level MAST
summaries with a donor covariate. It is not raw external reanalysis, per-gene
replication, external predictive validation, ATAC validation, or a neural routing
mechanism result. Batch remains unmodelled; primary PCW 19 is absent; nominal
population labels are not proven equivalent. `PCW18_DS_16545` has sub-quality
tissue, and `PCW17_CON_14310` has relatively thin population support. Natural-log
discovery effects and external log2 effects are compared only by rank/sign.
Removing chromosome 21 does not establish dosage-independent causation.

## Completion ledger and remaining action

| Plan component | State | Remaining requirement |
|---|---|---|
| Original RNA tasks 1–4: implementation and local execution | Complete | None locally; retain inconclusive result |
| Original RNA task 5: verification | Partial | Colab runs finished; retrieve final archive, compare locally and retain execution record |
| Paired M1–M4: accepted real inputs | Partial/blocked | Common measured ATAC counts, external access and accepted release/QC semantics |
| Paired M5: real scientific protocol | Pending | Freeze preprocessing, covariates, biological controls and sensitivities on accepted inputs |
| Paired M6–M8: real neural comparison | Pending | Real internal fits and locked external scoring after upstream gates pass |

Colab sign-in, authorized upload and free CPU execution have occurred. Final
archive retrieval/comparison is the remaining RNA verification step, not another
approval request. Local repetition is not a substitute.

For paired work, the [source and transport audit](PAIRED_MULTIOME_REMAINING_EVIDENCE_2026-09-08.md)
records the exact NeMO annotation count match, unresolved QC semantics, and public
manifest TLS failures. The annotation match is not automatic QC acceptance.
The [paired checklist](../tasks/todo.md) retains all real-data requirements.
Accept a documented common-count release or separately approve a bounded fragment
recount with adequate storage; do not zero-fill unmeasured regions or silently
start the roughly 43 GiB compressed fragment collection. Bigger GPU alone cannot
close these input gates. No paid service, author outreach or controlled access
was initiated.

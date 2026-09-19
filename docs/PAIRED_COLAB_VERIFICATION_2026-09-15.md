# Paired workflow: verified Colab CPU execution

## Outcome

- [Saved Colab notebook](https://colab.research.google.com/drive/1HUbpwBQWum8XYbmuv5PYvtUvkC-qtjQT)
- Completed 2026-09-15, 18:44 PDT (2026-09-16T01:44:28.552723+00:00).
- Free CPU runtime, approximately 12.67 GB RAM; no GPU or paid compute selected.
- All five wrapper cells completed; all nine original code cells executed without errors.
- 181 offline parser/capture/preflight tests passed in Colab (0.83 seconds in the final run).
- Research status remains **INCONCLUSIVE**; paired source remains **SOURCE_UNRESOLVED**.
- Saved RNA results were displayed, not recomputed. No dataset requests or real training.

## Reproducible packaging

Run `scripts/build_paired_colab.py <new-output.ipynb>` with the existing P22 environment.
Upload that generated notebook to Colab, select CPU, and run all cells.
The explicit twelve-file payload includes the unchanged notebook, three reviewed scripts,
three offline test files, project metadata, source contract, and three evidence reports.
It excludes raw datasets, credentials, Git history, and unrelated worktree files.

The native Colab kernel was Python 3.13. A separate Python 3.11.16 environment ran P22;
the project's Python requirement was not relaxed. Setup installs only notebook/test
dependencies, not the ML stack. Four direct package versions were checked:
pytest 8.4.2, nbformat 5.10.4, nbclient 0.11.0, ipykernel 7.3.0.
This is not a claim of a fully locked transitive environment.

## Verification and recovery

The first Colab attempt stopped before the original notebook cells: Colab's system
configuration requested `google.colab._kernel.Kernel` inside the isolated environment.
A local regression test reproduced this failure. Explicit standard-IPython kernel and
empty extension arguments corrected the subprocess launcher without changing native
Colab settings. The regression passed, then the entire corrected Colab wrapper ran again.

Downloaded the saved cloud notebook and the generated evidence ZIP. Independent checks:

- Cloud wrapper cell sources exactly match the corrected locally generated wrapper.
- ZIP has exactly fourteen expected files, with bounded uncompressed size.
- Twelve bundled files are byte-identical to the accepted checkout and match their hashes.
- Original notebook cell IDs and sources are unchanged; execution counts are 1 through 9.
- No error outputs; final decision preserves all refusal/training/scientific flags.
- Local final suite: **892 passed**, 19 existing classification warnings, 88.70 seconds.
- Ruff check and formatting check passed for 126 files.
- All twelve pre-existing dirty-file hashes in the original checkout still match.

The first full-suite invocation imported the older checkout through the shared environment;
setting `PYTHONPATH=src` selected the isolated checkout. No source changes were needed.
The cloud kernel reported standard local TCP transport and missing matplotlib-integration
warnings; neither prevented cell execution. No public kernel endpoint was configured.

## Evidence location

Local evidence directory:
`/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/paired_colab_20260915.zLaa8r`

- `P22_paired_workflow_Colab.saved.ipynb`: downloaded cloud notebook, including outputs.
- `P22_paired_workflow_Colab_fixed.ipynb`: corrected standalone source.
- `P22_paired_colab_verification.zip`: cloud-generated supporting files and executed notebook.
- `cloud_outputs/P22_paired_workflow.executed.ipynb`: unchanged original notebook, cloud outputs.
- `cloud_outputs/verification.json`: cloud execution record.
- `supervisor_checks.json`: local checks and independent artifact comparison.

This delivery proves software portability and reproducibility, not biological replication
or accepted paired-input feasibility. Existing scientific and acquisition gates remain unchanged.
No push, merge, professor outreach, permission expansion, or unrelated commit was performed.

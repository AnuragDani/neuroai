# P22 professor update package — 19 September 2026

Start with [one_pager.md](one_pager.md). [email.md](email.md) is an unsent draft.
This is a local review package, not a new experiment or a claim that P22 is complete.

## Read first

| Material | Notebook | HTML with saved outputs |
|---|---|---|
| Final local RNA experiment | [Jupyter](notebooks/current/P22_external_rna_local.executed.ipynb) | [HTML](html/current/P22_external_rna_local.executed.html) |
| RNA experiment in Colab's Python 3.11 subprocess | [Jupyter](notebooks/current/P22_external_rna_colab_py311.executed.ipynb) | [HTML](html/current/P22_external_rna_colab_py311.executed.html) |
| Paired workflow: executed offline checks | [Jupyter](notebooks/current/P22_paired_workflow.executed.ipynb) | [HTML](html/current/P22_paired_workflow.executed.html) |
| Paired Colab wrapper: completed run | [Jupyter](notebooks/current/P22_paired_workflow_Colab.saved.ipynb) | [HTML](html/current/P22_paired_workflow_Colab.saved.html) |

The RNA experiment remains **INCONCLUSIVE**. Paired inputs remain
**SOURCE_UNRESOLVED**. The paired Colab run tested software and displayed saved
RNA summaries; it did not run real paired neural-network training.

## Complete contents

- [Notebook index](notebook_index.md): every included notebook, its execution
  counts, recorded errors, code export, and HTML. Identical notebook bytes share
  one entry; [manifest.json](manifest.json) records every original source path.
- `notebooks/current/`: selected current sources and accepted final execution records.
- `notebooks/source/`: other repository notebook sources, including legacy workflows.
- `notebooks/history/`: earlier runs, intermediate attempts, and archived snapshots.
- `code/`: Python exports of all valid notebooks. These are review copies;
  IPython magics, notebook state, paths, dependencies and data requirements remain.
- `html/`: newly rendered notebook code and existing outputs. Unexecuted cells
  are not run. `html/original/` preserves older HTML files unchanged; their claims
  and dates do not replace the current one-page summary.
- `source_snapshot/`: current tracked package code, scripts, tests, configuration,
  plans and environment specifications. Original repository paths are preserved
  inside this directory. It is supporting source, not a standalone environment.
- `evidence/`: unchanged result reports and selected aggregate output files.
  Imported reports keep their original repository-relative links; some targets
  remain in the original checkout rather than this package.
- [verification.json](verification.json): package integrity, notebook format,
  execution-state inventory and export checks. These are packaging checks, not a
  fresh experiment or a fresh full test-suite run.

## Coverage and limits

Scope: every Git-tracked P22 notebook (including the recovered archive), all
`.ipynb` files under local `reports/generated/`, and the existing report HTML
files in `docs/` and `reports/generated/`. This is a local snapshot; no new Drive
search, download, runtime, or notebook execution occurred.

One existing empty notebook placeholder cannot produce notebook code or outputs.
Its exact bytes remain included, with an explanatory HTML page. Historical
notebooks with saved errors retain those errors. Execution counts are inventory
facts, not proof that every historical notebook is an accepted result.

No raw datasets, environments, weights, result ZIP archives, credentials or Git
history are copied. HTML requires no Python installation; some historical links
or interactive outputs can need external resources. To reproduce an analysis,
use the original checkout, source revision in `manifest.json`, approved inputs,
and the relevant frozen execution instructions. Do not rerun archived notebooks
indiscriminately.

The three handoff documents are intended for local Git history. Copied notebooks,
code snapshots, exported HTML and generated inventories are ignored here; the
canonical tracked sources remain in their original locations.

## Package checks and writing review

The package covers 92 original notebook paths as 58 byte-distinct files:
57 valid notebooks and one empty placeholder. It includes 57 Python exports,
58 HTML exports (one placeholder notice), three unchanged historical HTML files,
and 146 supporting source files. All ten pre-existing untracked documents remain
unchanged. Total size is approximately 60 MiB.

Browser rendering was not inspected: the app's browser policy blocks local-file
navigation. HTML structure, code-cell coverage and handoff links are checked
locally instead. No browser-policy workaround was used.

Red Pen review of the new one-page summary and email:

- Round 1: replaced the older interim narrative with the completed RNA result.
- Round 2: separated computational reproducibility from biological replication,
  and historical output from accepted evidence.
- Round 3: bounded the next step to input feasibility; checked counts, source
  links and pending work against the current records. No remaining content flags.

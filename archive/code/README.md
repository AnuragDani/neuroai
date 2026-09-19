# P22 code and notebook archive

Audited on 2026-09-19 UTC against the P22 checkout, Obsidian `papers/P22`
folder, saved Git bundles, and seven named P22 notebooks in Google Drive's
Colab Notebooks folder. The current reviewed implementation is restored in
`src/`, `scripts/`, `tests/`, and `notebooks/` at the repository root.

## Current entry points

| Purpose | File |
|---|---|
| Package implementation | [src/p22](../../src/p22/) |
| Scripts, including Python and R | [scripts](../../scripts/) |
| Paired workflow in Jupyter | [P22_paired_workflow.ipynb](../../notebooks/P22_paired_workflow.ipynb) |
| Standalone paired workflow in Colab | [P22_paired_workflow_Colab_fixed.ipynb](generated/paired_colab_20260915.zLaa8r/P22_paired_workflow_Colab_fixed.ipynb) |
| Standalone RNA analysis | [P22_down_syndrome_all_in_one.ipynb](../../P22_down_syndrome_all_in_one.ipynb) |
| Legacy Colab pipelines | [colab_notebooks](../../colab_notebooks/) |
| Reader environment Colab snapshot | [P22_reader_environment_20260912.ipynb](google_drive/1LFmvA3vh7DVVRpDV9fs4kBcOJ12tN887/P22_reader_environment_20260912.ipynb) |

## Coverage and provenance

[manifest.json](manifest.json) maps 72 source records to 65 distinct repository
files. It records original paths, SHA-256 hashes, seven Drive file IDs and
modification times, and the 15 recovered Git bundles. Identical files share one
destination. The two recent cloud execution notebooks were downloaded again
and matched their saved local snapshots byte for byte.

The recovered latest reviewed history contains 33 commits beyond the previous
checkout. It includes the RNA donor-influence diagnostic, input feasibility,
reader checks, Python/R scripts, paired Jupyter notebook, and Colab builder.
The separate GNHF candidate bundle's code already matches the recovered
implementation; its original patch files are preserved here.

These are exact historical snapshots, including candidate and rejected code.
Two archived launcher candidate Python files contain syntax errors; the
manifest identifies them. Two archived Colab notebooks retain a historical
auxiliary startup error. Successful later runs and existing scientific
limitations remain documented in the original evidence. Archiving a file does
not certify its execution, findings, or suitability as a current entry point.
The existing tracked `notebooks/artifacts/03_feature_reduction.ipynb` is an empty
placeholder, not a valid notebook; its original contents are unchanged.

Runtime output under `reports/generated/` remains ignored. This archive retains
the code and notebooks separately so later runs cannot overwrite the saved
snapshots. Virtual environments, installed dependencies, caches, checkpoints,
raw datasets, weights, and container images are excluded. The unrelated 2025
`Untitled0.ipynb` health-pattern notebook is excluded. A historical July 21
materials link returned 404; its contents could not be verified.

Check-in validation: 890 tests passed in the sandbox; the two Jupyter execution
tests were blocked only by local socket permissions and passed when rerun
outside the sandbox (892 passing tests in total). Ruff checks and formatting
passed for 126 current Python files. All 72 source records matched staged Git
blobs. Syntax/format inspection covered 147 Python files and 58 notebook paths;
the only failures were the two archived candidates and empty placeholder noted
above. A credential-pattern scan of 431 historical and new files found no matches.

## Verify archived bytes

Run from the repository root:

```bash
python3 - <<'PY'
import hashlib
import json
from pathlib import Path

manifest = json.loads(Path("archive/code/manifest.json").read_text())
for item in manifest["files"]:
    path = Path(item["repository_path"])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], path
print(f"Verified {len(manifest['files'])} source records.")
PY
```

# Q2 — Candidate cell-state endpoint audit

**Disposition:** `ENDPOINT_UNRESOLVED`  
**Date:** 2026-09-30  
**Branch:** `gnhf/execute-the-p22-data-146414`  
**Dependency:** Q1 PASS. No fits, downloads, package installs, or scientific-gate edits.

Machine-readable inventory: [endpoint_inventory.json](endpoint_inventory.json).

## Sources traced

| Source | Role |
|---|---|
| H5AD `/Users/anuragdani/Github/niw-eb1a/P22/data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad` sha256 `08d6eff265db6e6a2e1c4a259153588f3dba3c51f5f754736dc63c28795fcdbb` | Live obs/obsm inventory |
| Lattke et al. Nature Medicine 2026 doi:`10.1038/s41591-026-04211-1` (CELLxGENE citation in `uns`) | Author methods / annotation provenance |
| July 2 vault MOM ([00:36], [19:30]–[20:51]) | Professor cell-state / spectrum direction; avoid saturated subtype classification without wet-lab path |
| PLAN D1 / Q2 | Do not call RNA-derived proxies or disease-model scores independent biological truth; age ≠ cell state |
| N16 [SPECTRUM.md](../../../../docs/nn_v2/SPECTRUM.md) / `spectrum.json` | Prior spectrum used OOF disease scores × `author_cell_type` (`SPECTRUM_NULL`) |

Professor records remain distinct from this worker audit.

## Identity checks (no missing/duplicate cell identities)

| Check | Result |
|---|---|
| `obs` index unique | **PASS** — 248,998 / 248,998 |
| `observation_joinid` unique | **PASS** — 248,998 / 248,998 |
| `cluster_name` prefix vs `author_cell_type` | **0** mismatches |
| Donors with >1 `dev_PCW` | **0** |

## Endpoint validity table

| Candidate | Category | Label construction | Availability (summary) | Overlaps NN RNA/ATAC inputs? | Cell-state endpoint? |
|---|---|---|---|---|---|
| Disease / `group` | Independent specimen outcome | CON vs DS from cohort metadata | 15/15 donors; 126,385 / 122,613 cells | No (label); disease is existing primary target | **No** — not cell state |
| `dev_PCW` / stage | Contextual covariate | Specimen PCW (donor-constant) | PCW 10–20; some ages one-class only (10,14 CON-only; 15 DS-only) | No | **No** — age ≠ state |
| `author_cell_type` / SCT clusters / ontology `cell_type` | RNA-derived proxy | SCTransform/Seurat RNA clustering + author annotation | 15 types; donor×type ≥20 support varies (e.g. MIC 9/10, OPC 12/13, RG 15/15) | **Yes** — same Gene Expression modality (35,477 genes) | **No** — stratification only |
| Excitatory lineage subset | RNA-derived proxy | Author RNA subset mask | 215,680 True / 33,318 False | **Yes** | **No** |
| NN-v2 OOF disease scores (N16) | Model-circular proxy | Ladder disease predictions stratified by type | 9 eligible types; `SPECTRUM_NULL` | **Yes** | **No** — forbidden as independent truth |
| Sex | Contextual covariate | Specimen sex | male/female cells present | No | **No** |
| QC depths / TSS / nucleosome | Technical | Multiome QC | Complete non-null depths checked | Partially (depth related) | **No** |
| Pseudotime / maturation assay | **Absent** | — | No obs/obsm continuous state fields (only `X_umap`) | — | **No candidate** |

## Separation rules applied

1. **Independent measured outcomes** — only specimen disease (and sex/age metadata) qualify as independent of the RNA matrix; none is a cell-state endpoint.
2. **Contextual covariates** — `dev_PCW` / `stage` / sex may confound or stratify; they are not interchangeable with intracellular state.
3. **RNA-derived proxies** — `author_cell_type`, SCT resolutions, lineage subset, and UMAP are constructed from the same RNA used as model input; supervising on them claims circular “state.”
4. **Disease-model scores** — N16 spectrum remains a descriptive readout of the primary models; PLAN forbids treating it as independent biological truth.

## Pilot selection

**Selected endpoint for a future biological cell-state pilot:** none.  
**Record:** `ENDPOINT_UNRESOLVED`.

Selection was **not** based on CA performance or observed DS effect. No labels were invented.

## What this does and does not authorize

| Allowed next | Not authorized |
|---|---|
| Continue Q3–Q5 read-only reports | Biological cell-state / maturation fit claiming independent endpoint truth |
| Use `author_cell_type` as sampling/stratification factor (Q4) | Promoting N16 scores or SCT clusters to independent state targets |
| Synthetic pairing-use controls that do not need a biological state endpoint (later Q6–Q10 if other gates pass) | Treating unresolved endpoint as PASS for Q11 real pilot |

Checkpoint A: unresolved endpoint is an acceptable reported outcome and **cannot** unlock a biological fit.

## Verification commands

```bash
export PYTHONPATH="$(pwd)/src"
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -c "import p22; print(p22.__file__)"
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -m pytest tests/test_next_stage_endpoints_q2.py -q
```

Expected: exit 0; disposition `ENDPOINT_UNRESOLVED`; identity uniqueness and absent continuous state columns asserted against the live H5AD.

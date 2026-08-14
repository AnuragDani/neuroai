#!/usr/bin/env python3
# ruff: noqa: E501
"""Rewrite canonical notebook cells to wire C24-C31 real_pipeline path."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB_PATH = ROOT / "P22_down_syndrome_all_in_one.ipynb"


def build_embedded_source_literal() -> str:
    """Embed runtime source as readable file-by-file Python literals."""
    paths = sorted((ROOT / "src" / "p22").rglob("*.py")) + [ROOT / "plan" / "approvals.json"]
    lines = ["{\n"]
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        if "'''" in text:
            raise ValueError(f"embedded source contains triple-single-quote delimiter: {path}")
        lines.append(f"    {relative!r}: r'''\n{text}''',\n")
    lines.append("}\n")
    return "".join(lines)


EMBEDDED_SOURCE_LITERAL = build_embedded_source_literal()

CELL0 = """# P22: Down syndrome fetal cortex Multiome — one-notebook workflow

**Standalone notebook only.** Local Jupyter + Google Colab. No GitHub checkout required.

| | |
|---|---|
| CELLxGENE dataset | `f16c25da-15bd-46a4-9a3f-17093f27a2f1` |
| GEO | `GSE305153` |
| Expected cells | 248,998 (cell-level scale) |
| Expected donors | 30 = 15 normal + 15 complete trisomy 21 (inferential scale) |
| H5AD | ~1.57 GB (not in Git) |

## Visible modes

1. **simulation** — synthetic wiring only (default safe)
2. **metadata_census** — live catalog; no H5AD download
3. **real_analysis** — full public H5AD schema/QC, resources, donor-held-out models, interventions, validation

The implementation needed to run this notebook is embedded file-by-file in the first code cell. H5AD and fragment files are never embedded.

Professor approval is an external attestation (`P22_PROFESSOR_APPROVED=1`). No approval date is invented here.

Gates **G0–G9**. Data-size stages **R1–R6**. Capped models ≠ full dataset. Synthetic ≠ disease evidence.
"""

CELL1 = r'''from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

EMBEDDED_PROJECT_FILES = __P22_EMBEDDED_SOURCE_FILES__


def materialize_embedded_project(root: Path) -> Path:
    """Write embedded runtime source; no repository or network is required."""
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for relative_name, text in EMBEDDED_PROJECT_FILES.items():
        destination = (root / relative_name).resolve()
        if root not in destination.parents:
            raise RuntimeError(f"embedded path escapes project root: {relative_name}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")
    return root


def has_project_source(root: Path) -> bool:
    return (Path(root) / "src" / "p22" / "__init__.py").is_file()

# ---------------------------------------------------------------------------
# Visible mode controls (edit these; env flags also work)
# ---------------------------------------------------------------------------
NOTEBOOK_MODE = os.getenv("P22_NOTEBOOK_MODE", "simulation")  # simulation | metadata_census | real_analysis
RUN_REAL_DATA = os.getenv("P22_RUN_REAL_DATA", "0") == "1"
RUN_MODEL = os.getenv("P22_RUN_MODEL", "0") == "1"
# External approval attestation (do not invent a date; do not rewrite plan/approvals.json)
PROFESSOR_APPROVED_ENV = os.getenv("P22_PROFESSOR_APPROVED", "0") == "1"
# Optional Colab overrides:
# NOTEBOOK_MODE = "metadata_census"
# NOTEBOOK_MODE = "real_analysis"; RUN_REAL_DATA = True; RUN_MODEL = True; PROFESSOR_APPROVED_ENV = True

import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.preprocessing import StandardScaler

IN_COLAB = False
try:
    import google.colab  # noqa: F401
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

if IN_COLAB:
    import importlib
    need = []
    for pkg, mod in [("anndata", "anndata"), ("torch", "torch"), ("scikit-learn", "sklearn"), ("h5py", "h5py")]:
        try:
            importlib.import_module(mod)
        except ImportError:
            need.append(pkg)
    if need:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *need])
    PROJECT_ROOT = Path("/content/p22")
    PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
    DATA_ROOT = Path(os.getenv("P22_DATA_ROOT", "/content/p22_data"))
    OUTPUT_BASE = Path(os.getenv("P22_OUTPUT_ROOT", "/content/p22_output"))
    for candidate in (Path("/content/P22"), Path("/content/niw-eb1a/P22"), Path.cwd()):
        if has_project_source(candidate):
            PROJECT_ROOT = candidate
            break
    if not has_project_source(PROJECT_ROOT):
        PROJECT_ROOT = materialize_embedded_project(Path("/content/p22_standalone"))
        print("Using embedded P22 implementation; no GitHub checkout required.")
else:
    CWD = Path.cwd().resolve()
    PROJECT_ROOT = CWD
    for candidate in (CWD, *CWD.parents):
        if (candidate / "pyproject.toml").is_file() and has_project_source(candidate):
            PROJECT_ROOT = candidate
            break
    DATA_ROOT = Path(os.getenv("P22_DATA_ROOT", PROJECT_ROOT / "data" / "real"))
    OUTPUT_BASE = Path(os.getenv("P22_OUTPUT_ROOT", PROJECT_ROOT / "reports" / "generated" / "verification" / "down_syndrome"))

    if not has_project_source(PROJECT_ROOT):
        PROJECT_ROOT = materialize_embedded_project(Path.cwd() / ".p22_standalone")
        DATA_ROOT = Path(os.getenv("P22_DATA_ROOT", PROJECT_ROOT / "data" / "real"))
        OUTPUT_BASE = Path(os.getenv("P22_OUTPUT_ROOT", PROJECT_ROOT / "reports" / "generated" / "verification" / "down_syndrome"))
        print("Using embedded P22 implementation; no GitHub checkout required.")

if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Colab can preload an unrelated namespace package named p22. Remove it so
# imports resolve from this checkout rather than stale interpreter state.
for module_name in list(sys.modules):
    if module_name == "p22" or module_name.startswith("p22."):
        del sys.modules[module_name]

from p22 import load_approvals
from p22.data.adequacy import catalog_donor_frame, evaluate_donor_adequacy
from p22.data.catalog import (
    DEFAULT_COLLECTION_ID,
    DEFAULT_DATASET_ID,
    EXPECTED_CELLS,
    EXPECTED_DONORS,
    EXPECTED_H5AD_BYTES,
    run_catalog_preflight,
)
from p22.data.census import (
    census_blocked_placeholder,
    data_scale_section,
    download_h5ad,
    estimate_download_gb,
    planned_acquisition_from_catalog,
    run_backed_census,
    verify_local_h5ad,
)
from p22.data.group_splits import (
    aggregate_donor_probabilities,
    build_repeated_group_split_report,
)
from p22.data.resources import (
    PRIMARY_CAP,
    SENSITIVITY_CAPS,
    ResourceMeasurement,
    build_resource_report,
    decide_atac_branch,
    disk_free_gb,
)
from p22.eval.data_scale import empty_scale_board, make_scale
from p22.eval.estimand import freeze_estimand
from p22.eval.faithfulness import INTERVENTIONS, intervention_table, run_all_interventions
from p22.eval.gates import ONE_NOTEBOOK_CONTRACT, empty_board, make_gate
from p22.eval.marker_validation import CHR21_DOSAGE_PANEL_NAME
from p22.eval.modes import (
    MODE_METADATA_CENSUS,
    MODE_REAL_ANALYSIS,
    MODE_SIMULATION,
    resolve_mode,
)
from p22.eval.real_pipeline import (
    RealAnalysisState,
    freeze_real_estimand,
    run_real_interventions,
    run_real_model_comparison,
    run_real_validation,
    run_resource_and_atac,
    run_schema_qc_census,
)
from p22.eval.runtime import collect_runtime_report
from p22.eval.validation import build_validation_report
from p22.models.fusion import GatedFusionModel
from p22.models.named_baselines import (
    BaselineResult,
    baseline_table,
    blocked_baseline,
    chr21_dosage_baseline,
    covariate_logistic_baseline,
    majority_class_baseline,
    not_applicable_baseline,
    pseudobulk_rna_logistic,
)
from p22.reports.evidence_package import EvidencePackage
from p22.reports.handoff import copy_executed_notebook, write_human_summary
from p22.testing.synthetic import make_synthetic_multimodal

SEED = 20260728
MODEL_INIT_SEED = 0
DATASET_ID = DEFAULT_DATASET_ID
COLLECTION_ID = DEFAULT_COLLECTION_ID
UPLOADED_NOTEBOOK = Path.cwd() / "P22_down_syndrome_all_in_one.ipynb"
SOURCE_NOTEBOOK = UPLOADED_NOTEBOOK if UPLOADED_NOTEBOOK.is_file() else PROJECT_ROOT / "P22_down_syndrome_all_in_one.ipynb"

approvals = load_approvals(PROJECT_ROOT / "plan" / "approvals.json") if (PROJECT_ROOT / "plan" / "approvals.json").is_file() else load_approvals()
PROFESSOR_APPROVED = PROFESSOR_APPROVED_ENV or (
    bool(approvals.get("approval_recorded")) and approvals.get("approval_state") == "approved"
)
mode = resolve_mode(
    NOTEBOOK_MODE,
    professor_approved=PROFESSOR_APPROVED,
    run_real_data=RUN_REAL_DATA,
    run_model=RUN_MODEL,
)
if RUN_MODEL and not PROFESSOR_APPROVED:
    raise RuntimeError(
        "Approval attestation required for model fitting: set P22_PROFESSOR_APPROVED=1 "
        "(external attestation; no date invented here)."
    )

RUN_STAMP = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
OUTPUT_ROOT = OUTPUT_BASE / f"run_{RUN_STAMP}"
DATA_ROOT.mkdir(parents=True, exist_ok=True)
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

def safe_write_text(path: Path, text: str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path

def notebook_hash() -> str:
    if not SOURCE_NOTEBOOK.is_file():
        return "unknown"
    return hashlib.sha256(SOURCE_NOTEBOOK.read_bytes()).hexdigest()

board = empty_board()
scale_board = empty_scale_board()
EVIDENCE_BUCKETS = {"verified_real": [], "synthetic": [], "metadata_only": [], "blocked_or_unknown": []}
real_state = RealAnalysisState()
REAL_MODE_ACTIVE = mode.mode == MODE_REAL_ANALYSIS and mode.allow_h5ad_download
paired_deltas = []
validation_rows = []
baseline_rows = []
intervention_rows = []

print(ONE_NOTEBOOK_CONTRACT)
print({
    "in_colab": IN_COLAB,
    "mode": mode.to_dict(),
    "python": sys.version.split()[0],
    "project_root": str(PROJECT_ROOT),
    "data_root": str(DATA_ROOT),
    "output_root": str(OUTPUT_ROOT),
    "estimated_h5ad_gb": estimate_download_gb(),
    "professor_approved": PROFESSOR_APPROVED,
    "disk_free_gb": disk_free_gb(DATA_ROOT),
})
'''

CELL4 = """## G1 / R1 — Live catalog identity + acquisition contract

Estimated H5AD download shown before any download. Download only in `real_analysis` mode with `P22_RUN_REAL_DATA=1`.
"""

CELL6 = """## G2 / R2 / R3 — Schema, QC, donor census

Full-cohort schema/QC uses every retained cell before any 256-cell cap. Real mode runs derived QC and stop rules. Simulation/metadata modes stay catalog-only.
"""

CELL7 = r"""donor_ids = list(summary.get("donor_ids") or [])
donor_frame = catalog_donor_frame(donor_ids) if donor_ids else pd.DataFrame(columns=["donor_id", "condition"])
adequacy = evaluate_donor_adequacy(donor_frame, pairing_known=False)

h5ad_path = DATA_ROOT / f"{DATASET_ID}.h5ad"
census = census_blocked_placeholder("H5AD not loaded in current mode")
local_verify = None
schema_report = None
qc_report = None

if mode.allow_h5ad_download:
    print("Dataset ID:", DATASET_ID)
    print("Expected download bytes:", acquisition.expected_bytes)
    print("Free disk GB:", disk_free_gb(DATA_ROOT))
    print("Downloading/reusing full H5AD (~%.2f GB). Not a tiny subset." % estimate_download_gb(acquisition.expected_bytes))
    h5ad_path = download_h5ad(h5ad_path, url=acquisition.h5ad_url, expected_bytes=acquisition.expected_bytes, allow=True)
    local_verify = verify_local_h5ad(h5ad_path, expected_bytes=acquisition.expected_bytes)
    print(json.dumps(local_verify, indent=2))
    acquisition = replace(
        acquisition,
        status="PASS" if local_verify["ok"] else "BLOCKED",
        observed_bytes=local_verify.get("observed_bytes"),
        sha256=local_verify.get("sha256"),
        downloaded_at=datetime.now(UTC).isoformat(),
        path=str(h5ad_path),
        blocking_problems=() if local_verify["ok"] else (local_verify.get("reason") or "H5AD verification failed",),
        open_questions=() if local_verify["ok"] else ("H5AD checksum/size verification failed",),
    )
    scale_board.set(make_scale("R1", acquisition.status, evidence=acquisition.to_dict(),
                               unknowns=acquisition.open_questions,
                               notes="full H5AD acquisition verified before census"))
    if local_verify["ok"]:
        EVIDENCE_BUCKETS["verified_real"].append("R1 full H5AD size and SHA256 verified")
        census = run_backed_census(h5ad_path)
        # C24 full schema + derived QC + exclusions
        run_schema_qc_census(h5ad_path, real_state)
        schema_report = real_state.schema
        qc_report = real_state.qc
        from p22.data.adequacy import AdequacyReport
        adequacy = AdequacyReport(
            status=real_state.adequacy["status"],
            thresholds=real_state.adequacy["thresholds"],
            donor_table=real_state.adequacy["donor_table"],
            checks=real_state.adequacy["checks"],
            blocking_problems=tuple(real_state.adequacy["blocking_problems"]),
            open_questions=tuple(real_state.adequacy["open_questions"]),
            selected_off_ramp=real_state.adequacy.get("selected_off_ramp"),
            off_ramp_options=real_state.adequacy.get("off_ramp_options") or {},
        )
        print("Schema status:", schema_report.get("status"))
        print("QC status:", qc_report.get("status"),
              "pre/post cells:", qc_report.get("n_cells_pre_qc"), qc_report.get("n_cells_post_qc"),
              "donors:", qc_report.get("n_donors_post_qc"))
        print("Condition donors:", qc_report.get("condition_donors_post_qc"))
        print("Chr21:", (schema_report.get("chr21_mapping") or {}).get("status"),
              (schema_report.get("chr21_mapping") or {}).get("n_chr21_genes"))
        print("Exclusions:", json.dumps(qc_report.get("exclusions"), indent=2)[:1200])
        for key, values in real_state.evidence_buckets.items():
            for item in values:
                if item not in EVIDENCE_BUCKETS[key]:
                    EVIDENCE_BUCKETS[key].append(item)
    else:
        census = census_blocked_placeholder(local_verify["reason"] or "H5AD verify failed")
else:
    print("Census skipped: mode does not allow H5AD download.")
    print("Catalog donors (all identities):")
    print(donor_frame.to_string(index=False) if len(donor_frame) else "(none)")

board.set(make_gate("G2", adequacy.status, evidence=adequacy.to_dict() if hasattr(adequacy, "to_dict") else real_state.adequacy,
                    unknowns=getattr(adequacy, "open_questions", ()),
                    notes="post-QC donor adequacy when H5AD loaded; else catalog"))
r2_status = "PASS" if (qc_report and qc_report.get("status") == "PASS") else census.status
scale_board.set(make_scale("R2", r2_status, evidence={"census": census.to_dict(), "schema": schema_report, "qc": qc_report},
                           unknowns=census.open_questions, notes="full-cohort schema/QC before model cap"))
r3_status = adequacy.status if r2_status != "BLOCKED" else "BLOCKED"
scale_board.set(make_scale("R3", r3_status, evidence={"adequacy": adequacy.to_dict() if hasattr(adequacy, "to_dict") else real_state.adequacy, "qc": qc_report},
                           notes="post-QC adequacy uses retained values when H5AD present"))
print("G2:", adequacy.status, "R2:", r2_status, "R3:", r3_status)
EVIDENCE_BUCKETS["metadata_only"].append("G2 catalog donor adequacy")
if qc_report is None:
    EVIDENCE_BUCKETS["blocked_or_unknown"].append("R2/R3 full-cohort QC not run")
else:
    EVIDENCE_BUCKETS["verified_real"].append("R2/R3 full-cohort schema and QC")
"""

CELL8 = """## G3 / R4 — Resources, caps, ATAC B1/B2

Layers: **full-cohort** (census/pseudobulk all retained) vs **cell-level model** (256 primary; 64/128 sensitivity). Fragment build is B2a only when explicitly approved and budgeted; otherwise B2b RNA-only.
"""

CELL9 = r"""fragment_asset = summary.get("atac_fragment_asset") or {}
fragment_present = bool(fragment_asset.get("present"))
peak_present = None
if real_state.schema:
    peak_present = bool((real_state.schema.get("atac") or {}).get("peak_block_present"))
elif hasattr(census, "peak_block_present"):
    peak_present = census.peak_block_present

if REAL_MODE_ACTIVE and local_verify and local_verify.get("ok") and real_state.keep_mask is not None:
    # Probe fragment size when catalog omits it (for B2a budget only; no download).
    if fragment_present and fragment_asset.get("file_size") is None and fragment_asset.get("url"):
        from p22.data.catalog import remote_content_length
        size = remote_content_length(fragment_asset["url"])
        if size is not None:
            fragment_asset = dict(fragment_asset)
            fragment_asset["file_size"] = size
            print("Fragment Content-Length bytes:", size)
    run_resource_and_atac(
        h5ad_path,
        real_state,
        fragment_asset=fragment_asset,
        fragment_build_approved=False,  # explicit opt-in required for B2a
    )
    atac_branch_dict = real_state.atac_branch
    from p22.data.resources import AtacBranchDecision
    atac_branch = AtacBranchDecision(
        branch=atac_branch_dict["branch"],
        peak_block_present=atac_branch_dict.get("peak_block_present"),
        fragment_asset_present=atac_branch_dict.get("fragment_asset_present"),
        fragment_build_approved=atac_branch_dict.get("fragment_build_approved", False),
        multimodal_claim_allowed=atac_branch_dict.get("multimodal_claim_allowed", False),
        rationale=atac_branch_dict.get("rationale", ""),
        not_applicable_models=tuple(atac_branch_dict.get("not_applicable_models") or ()),
    )
    from p22.data.resources import ResourceMeasurement as RM, ResourceReport
    measurements = [RM(**{k: m[k] for k in m if k in RM.__dataclass_fields__}) for m in real_state.resource.get("measurements") or []]
    resource = ResourceReport(
        status=str(real_state.resource.get("status") or "INCONCLUSIVE"),
        measurements=measurements,
        atac_branch=atac_branch,
        blocking_problems=tuple(real_state.resource.get("blocking_problems") or ()),
        open_questions=tuple(real_state.resource.get("open_questions") or ()),
        environment=dict(real_state.resource.get("environment") or {}),
        fragment_feasibility=dict(real_state.resource.get("fragment_feasibility") or {}),
        storage=dict(real_state.resource.get("storage") or {}),
    )
    print(json.dumps({
        "atac_branch": atac_branch.branch,
        "multimodal_claim_allowed": atac_branch.multimodal_claim_allowed,
        "measurements": real_state.resource.get("measurements"),
        "fragment_feasibility": real_state.resource.get("fragment_feasibility"),
        "storage": real_state.resource.get("storage"),
        "environment": {k: real_state.resource.get("environment", {}).get(k) for k in ("python", "platform", "ram_total_gb", "cpu_count")},
    }, indent=2, default=str))
    for key, values in real_state.evidence_buckets.items():
        for item in values:
            if item not in EVIDENCE_BUCKETS[key]:
                EVIDENCE_BUCKETS[key].append(item)
else:
    atac_branch = decide_atac_branch(
        peak_block_present=peak_present,
        fragment_asset_present=fragment_present,
        fragment_build_approved=False,
        resource_budget_ok=False,
    )
    measurements = [
        ResourceMeasurement(name="catalog_h5ad_size", cells_per_donor_cap=None,
                            input_bytes=acquisition.expected_bytes, disk_free_gb=runtime.disk_free_gb,
                            notes="catalog/planned size"),
        ResourceMeasurement(name="planned_primary_cap", cells_per_donor_cap=PRIMARY_CAP,
                            notes="cell-level model layer primary cap; not full dataset"),
        ResourceMeasurement(name="planned_sensitivity_caps", cells_per_donor_cap=None,
                            notes=f"sensitivity caps {SENSITIVITY_CAPS}"),
    ]
    resource = build_resource_report(
        measurements=measurements,
        atac_branch=atac_branch,
        h5ad_available=bool(local_verify and local_verify.get("ok")),
        approval_present=PROFESSOR_APPROVED,
    )
    print("ATAC branch (planned):", atac_branch.branch, "| multimodal allowed:", atac_branch.multimodal_claim_allowed)

board.set(make_gate("G3", resource.status if hasattr(resource, "status") else real_state.resource.get("status"),
                    evidence=resource.to_dict() if hasattr(resource, "to_dict") else real_state.resource,
                    unknowns=getattr(resource, "open_questions", tuple(real_state.resource.get("open_questions") or ())),
                    notes="measured caps in real mode; planned otherwise"))
r4_status = resource.status if hasattr(resource, "status") else real_state.resource.get("status")
scale_board.set(make_scale("R4", r4_status, evidence=resource.to_dict() if hasattr(resource, "to_dict") else real_state.resource,
                           notes="resource + ATAC branch"))
print("G3:", r4_status, "R4:", r4_status, "branch:", atac_branch.branch)
"""

CELL1 = CELL1.replace("__P22_EMBEDDED_SOURCE_FILES__", EMBEDDED_SOURCE_LITERAL)

CELL10 = """## G4 — Frozen estimand (before predictions)

Donor unit, StratifiedGroupKFold, mean-probability aggregation, threshold 0.5, donor balanced accuracy, resolution-derived margin (≥0.07 with 15/class).
"""

CELL11 = r"""if REAL_MODE_ACTIVE and real_state.keep_mask is not None and PROFESSOR_APPROVED and mode.allow_model_fit:
    freeze_real_estimand(real_state, seed=SEED)
    estimand_report = type("E", (), {
        "status": real_state.estimand.get("status"),
        "to_dict": lambda self=None: real_state.estimand,
        "open_questions": tuple(real_state.estimand.get("open_questions") or ()),
        "estimand": type("F", (), real_state.estimand.get("estimand") or {})(),
    })()
    # Rebuild a proper FrozenEstimand-like access for margin printing
    est = real_state.estimand.get("estimand") or {}
    print(json.dumps({
        "status": real_state.estimand.get("status"),
        "margin": est.get("practical_margin"),
        "resolution": est.get("score_resolution"),
        "n_control": est.get("n_control_donors"),
        "n_ds": est.get("n_ds_donors"),
        "marker_set": (est.get("validation_plan") or {}).get("marker_set"),
        "split_overlap": real_state.split.get("donor_overlap_count"),
    }, indent=2))
    for key, values in real_state.evidence_buckets.items():
        for item in values:
            if item not in EVIDENCE_BUCKETS[key]:
                EVIDENCE_BUCKETS[key].append(item)
else:
    n_control = int((adequacy.checks or {}).get("n_control_donors") or 15)
    n_ds = int((adequacy.checks or {}).get("n_ds_donors") or 15)
    estimand_report = freeze_estimand(
        n_control_donors=n_control,
        n_ds_donors=n_ds,
        marker_set=CHR21_DOSAGE_PANEL_NAME,
        already_predicted=False,
    )
    print(json.dumps(estimand_report.to_dict(), indent=2)[:1500])

board.set(make_gate("G4", estimand_report.status if hasattr(estimand_report, "status") else real_state.estimand.get("status"),
                    evidence=estimand_report.to_dict() if hasattr(estimand_report, "to_dict") else real_state.estimand,
                    unknowns=getattr(estimand_report, "open_questions", tuple(real_state.estimand.get("open_questions") or ())),
                    notes="frozen before predictions"))
print("G4:", getattr(estimand_report, "status", real_state.estimand.get("status")))
"""

CELL12 = """## G5 — Donor-held-out leakage control

Real mode: repeated StratifiedGroupKFold on post-QC donors. Simulation: synthetic wiring only.
"""

CELL13 = r"""synth = make_synthetic_multimodal(n_donors=30, cells_per_donor=24, n_features_a=32, n_features_b=32, n_classes=2, seed=SEED)
# Donor-pure labels from donor id (synthetic view labels intentionally carry donor nuisance).
synth_labels = np.asarray([0 if int(str(d).split("_")[1]) < 15 else 1 for d in synth.donor_ids])
split_report = build_repeated_group_split_report(
    synth.donor_ids, synth_labels, n_repeats=5, n_folds=5, base_seed=SEED,
)

if REAL_MODE_ACTIVE and real_state.split and mode.allow_model_fit and PROFESSOR_APPROVED:
    g5_status = "PASS" if real_state.split.get("donor_overlap_count", 1) == 0 else "BLOCKED"
    board.set(make_gate("G5", g5_status, evidence=real_state.split,
                        notes="real donor StratifiedGroupKFold; zero overlap required"))
    print("G5:", g5_status, "real_overlap=", real_state.split.get("donor_overlap_count"))
    EVIDENCE_BUCKETS["verified_real"].append("G5 real donor-held-out splits")
else:
    assert split_report.donor_overlap_count == 0
    g5_status = split_report.status if mode.mode == MODE_SIMULATION else (
        "BLOCKED" if REAL_MODE_ACTIVE and not mode.allow_model_fit else split_report.status
    )
    board.set(make_gate("G5", g5_status, evidence={
        "synthetic_split_status": split_report.status,
        "n_folds": len(split_report.folds),
        "donor_overlap_count": split_report.donor_overlap_count,
        "real_data": "pending" if REAL_MODE_ACTIVE else "not_requested",
    }, notes="synthetic wiring proof; real matrix evaluation uses model flag"))
    print("G5:", g5_status, "synthetic_overlap=", split_report.donor_overlap_count)
    EVIDENCE_BUCKETS["synthetic"].append("G5 StratifiedGroupKFold zero-overlap wiring")
"""

CELL14 = """## G6 — Named baselines + real donor-held-out comparison

Order fixed: majority → chr21 dosage → QC/covariate → pseudobulk RNA → RNA-only → ATAC/concat/gated (NA under B2b).
"""

CELL15 = r"""fold0 = split_report.folds[0]
train_donors, test_donors = fold0.train_donors, fold0.test_donors
y, donors = synth_labels, np.asarray(synth.donor_ids, dtype=object)
rna, atac = synth.view_a, synth.view_b
train_idx, test_idx = fold0.train_index, fold0.test_index

baseline_rows = []
paired_deltas = []

if REAL_MODE_ACTIVE and mode.allow_model_fit and PROFESSOR_APPROVED and real_state.keep_mask is not None:
    print("Running real donor-held-out baselines/models (this can take several minutes)...")
    print("Data layer: full cohort for census/pseudobulk; capped", PRIMARY_CAP, "cells/donor for RNA cell model")
    print("ATAC branch:", real_state.atac_branch_label)
    run_real_model_comparison(h5ad_path, real_state, primary_cap=PRIMARY_CAP, n_features=2000)
    baseline_rows = real_state.metrics_rows
    paired_deltas = real_state.paired_deltas
    g6_status = "PASS" if any(row.get("status") == "measured" for row in baseline_rows) else "BLOCKED"
    if real_state.split.get("donor_level_overlap", 0) != 0 or real_state.split.get("cell_level_overlap", 0) != 0:
        g6_status = "BLOCKED"
    board.set(make_gate("G6", g6_status, evidence={"metrics": baseline_rows, "paired_deltas": paired_deltas,
                                                    "atac_branch": real_state.atac_branch},
                        notes="real donor-held-out comparison; cheap baselines before gated fusion"))
    print(pd.DataFrame(baseline_rows)[["model", "layer", "status", "donor_balanced_accuracy", "not_applicable"]].to_string(index=False))
    if paired_deltas:
        print("Paired deltas (rna_only vs baselines):")
        print(pd.DataFrame(paired_deltas).to_string(index=False))
    for key, values in real_state.evidence_buckets.items():
        for item in values:
            if item not in EVIDENCE_BUCKETS[key]:
                EVIDENCE_BUCKETS[key].append(item)
    print("G6:", g6_status)
else:
    results = [
        majority_class_baseline(y, donors),
        chr21_dosage_baseline(None, y, donors, train_donors, test_donors),
        covariate_logistic_baseline(None, y, donors, train_donors, test_donors),
        pseudobulk_rna_logistic(rna, y, donors, train_donors, test_donors, n_features=16),
    ]

    def donor_bal_acc(matrix, name):
        scaler = StandardScaler()
        x_train = scaler.fit_transform(matrix[train_idx])
        x_test = scaler.transform(matrix[test_idx])
        model = LogisticRegression(max_iter=400, class_weight="balanced", random_state=MODEL_INIT_SEED)
        model.fit(x_train, y[train_idx])
        proba = model.predict_proba(x_test)[:, 1]
        agg = aggregate_donor_probabilities(proba, donors[test_idx], threshold=0.5)
        truth = (pd.DataFrame({"donor_id": donors[test_idx], "label": y[test_idx]})
                 .groupby("donor_id")["label"].agg(lambda s: int(s.mode().iloc[0])))
        merged = agg.merge(truth.rename("label"), on="donor_id")
        score = float(balanced_accuracy_score(merged["label"], merged["prediction"]))
        return BaselineResult(name=name, status="measured", donor_balanced_accuracy=score,
                              n_donors=int(merged.shape[0]), n_cells=int(test_idx.size),
                              detail={"layer": "synthetic_wiring", "cap_note": "not disease evidence"})

    results.append(donor_bal_acc(rna, "rna_only"))
    if atac_branch.multimodal_claim_allowed:
        results.append(donor_bal_acc(atac, "atac_only"))
        results.append(donor_bal_acc(np.hstack([rna, atac]), "rna_atac_concat"))
        results.append(blocked_baseline("gated_fusion", "gated fusion blocked without approved real model run"))
    else:
        reason = f"ATAC branch {atac_branch.branch}; multimodal claim not allowed"
        results.extend([
            not_applicable_baseline("atac_only", reason),
            not_applicable_baseline("rna_atac_concat", reason),
            not_applicable_baseline("gated_fusion", reason),
        ])
    baseline_rows = baseline_table(results)
    g6_status = "PASS" if mode.mode == MODE_SIMULATION else "BLOCKED"
    board.set(make_gate("G6", g6_status, evidence={"baselines": baseline_rows, "atac_branch": atac_branch.branch},
                        unknowns=("real-data baselines not run",) if REAL_MODE_ACTIVE else (),
                        notes="synthetic baseline wiring; not disease evidence"))
    print(pd.DataFrame(baseline_rows)[["name", "status", "donor_balanced_accuracy", "not_applicable"]].to_string(index=False))
    print("G6:", g6_status)
    EVIDENCE_BUCKETS["synthetic"].append("G6 named baseline wiring")
"""

CELL16 = """## G7 — Routing faithfulness (held-out only)

Real B2b path: RNA ablations/clamps/permutations. ATAC/gate interventions marked NOT_APPLICABLE. Gate values are routing signals, not explanations.
"""

CELL17 = r"""intervention_rows = []

if REAL_MODE_ACTIVE and mode.allow_model_fit and PROFESSOR_APPROVED and real_state.keep_mask is not None:
    run_real_interventions(h5ad_path, real_state, primary_cap=PRIMARY_CAP, n_features=64)
    intervention_rows = real_state.intervention_rows
    g7_status = "PASS" if any(row.get("status") == "measured" for row in intervention_rows) else "INCONCLUSIVE"
    board.set(make_gate("G7", g7_status, evidence={"interventions": intervention_rows},
                        notes="RNA-only held-out interventions; multimodal routing NA under B2b"))
    print(pd.DataFrame(intervention_rows).to_string(index=False)[:2000])
    for key, values in real_state.evidence_buckets.items():
        for item in values:
            if item not in EVIDENCE_BUCKETS[key]:
                EVIDENCE_BUCKETS[key].append(item)
    print("G7:", g7_status)
else:
    n_features = 16
    rna_scaler = StandardScaler().fit(rna[train_idx][:, :n_features])
    atac_scaler = StandardScaler().fit(atac[train_idx][:, :n_features])
    train_rna = rna_scaler.transform(rna[train_idx][:, :n_features])
    test_rna = rna_scaler.transform(rna[test_idx][:, :n_features])
    train_atac = atac_scaler.transform(atac[train_idx][:, :n_features])
    test_atac = atac_scaler.transform(atac[test_idx][:, :n_features])
    torch.manual_seed(MODEL_INIT_SEED)
    gated = GatedFusionModel(n_features_a=n_features, n_features_b=n_features, n_classes=2, embed_dim=16, hidden_dim=32)
    opt = torch.optim.Adam(gated.parameters(), lr=1e-2)
    xa = torch.tensor(train_rna, dtype=torch.float32)
    xb = torch.tensor(train_atac, dtype=torch.float32)
    yt = torch.tensor(y[train_idx], dtype=torch.int64)
    for _ in range(20):
        opt.zero_grad()
        out = gated(xa, xb)
        torch.nn.functional.cross_entropy(out.logits, yt).backward()
        opt.step()
    effects = run_all_interventions(
        gated,
        views={"view_a": test_rna, "view_b": test_atac},
        labels=y[test_idx],
        donor_ids=donors[test_idx],
        train_views={"view_a": train_rna, "view_b": train_atac},
        metric_name="balanced_accuracy",
        seed=SEED,
    )
    intervention_rows = intervention_table(effects)
    g7_status = "PASS" if mode.mode == MODE_SIMULATION else "BLOCKED"
    board.set(make_gate("G7", g7_status, evidence={"interventions": intervention_rows},
                        notes="synthetic intervention plumbing; routing signals only"))
    print(pd.DataFrame(intervention_rows).to_string(index=False))
    print("G7:", g7_status, "n_interventions=", len(INTERVENTIONS))
    EVIDENCE_BUCKETS["synthetic"].append("G7 routing interventions")
"""

CELL18 = """## G8 / R5 — External validation + donor-limited scale

Frozen marker panels tested on held-out donors (internal evidence). GSE280175 is RNA-only validation candidate; matrix not auto-ingested. Independent multimodal validation remains UNKNOWN.
"""

CELL19 = r"""if REAL_MODE_ACTIVE and mode.allow_model_fit and PROFESSOR_APPROVED and real_state.keep_mask is not None:
    run_real_validation(h5ad_path, real_state)
    validation = type("V", (), {
        "status": real_state.validation.get("status"),
        "to_dict": lambda self=None: real_state.validation,
        "open_questions": tuple(real_state.validation.get("open_questions") or ()),
        "claim_boundary": real_state.validation.get("claim_boundary"),
        "resources": [],
    })()
    validation_rows = real_state.validation_rows
    for key, values in real_state.evidence_buckets.items():
        for item in values:
            if item not in EVIDENCE_BUCKETS[key]:
                EVIDENCE_BUCKETS[key].append(item)
else:
    validation = build_validation_report(
        marker_set=CHR21_DOSAGE_PANEL_NAME,
        findings_available=False,
        approval_present=PROFESSOR_APPROVED,
    )
    validation_rows = [item.to_dict() | {"gate_status": validation.status} for item in validation.resources]

board.set(make_gate("G8", validation.status if hasattr(validation, "status") else real_state.validation.get("status"),
                    evidence=validation.to_dict() if hasattr(validation, "to_dict") else real_state.validation,
                    unknowns=getattr(validation, "open_questions", tuple(real_state.validation.get("open_questions") or ())),
                    notes=getattr(validation, "claim_boundary", "bounded validation claims")))
scale_board.set(make_scale(
    "R5",
    "INCONCLUSIVE",
    evidence={
        "cell_level_scale": EXPECTED_CELLS,
        "inferential_scale_donors": EXPECTED_DONORS,
        "statement_cells": f"Real full cohort target contains {EXPECTED_CELLS} cells and {EXPECTED_DONORS} donors.",
        "statement_donors": "Inferential uncertainty is donor-limited; donor resampling and external cohort evidence required.",
        "off_ramps": getattr(adequacy, "off_ramp_options", {}),
        "validation": validation.to_dict() if hasattr(validation, "to_dict") else real_state.validation,
        "panels": getattr(real_state, "panel_rows", []),
    },
    notes="30 donors moderate; do not inflate via cell count",
))
print("G8:", getattr(validation, "status", real_state.validation.get("status")))
if REAL_MODE_ACTIVE and real_state.panel_rows:
    print(pd.DataFrame(real_state.panel_rows).to_string(index=False)[:1500])
else:
    EVIDENCE_BUCKETS["blocked_or_unknown"].append("G8 external validation not run in this mode")
"""

CELL20 = """## G9 / R6 — Evidence package + handoff

Writes `manifest.json`, `metrics.csv`, `interventions.csv`, `validation.csv`, `figures/`, `SUMMARY.md`. Never overwrites source notebook.
"""

CELL21 = r"""def git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"

data_scale = data_scale_section(
    acquisition, census,
    primary_cap=PRIMARY_CAP,
    sensitivity_caps=SENSITIVITY_CAPS,
)
scale_board.set(make_scale("R6", "PASS", evidence=data_scale, notes="numeric data-scale section written"))

exact_command = (
    f"P22_NOTEBOOK_MODE={mode.mode} P22_RUN_REAL_DATA={int(RUN_REAL_DATA)} "
    f"P22_RUN_MODEL={int(RUN_MODEL)} P22_PROFESSOR_APPROVED={int(PROFESSOR_APPROVED)} "
    f"{sys.executable} -m jupyter nbconvert --to notebook --execute "
    f"{SOURCE_NOTEBOOK.name} --output-dir reports/generated/notebooks "
    f"--output P22_down_syndrome_all_in_one.executed.ipynb"
)

# Prefer real metrics when present
metrics_for_package = baseline_rows
interventions_for_package = intervention_rows
validation_for_package = validation_rows or [
    item.to_dict() | {"gate_status": getattr(validation, "status", None)}
    for item in getattr(validation, "resources", [])
]

package = EvidencePackage(
    run_dir=OUTPUT_ROOT / "runs" / f"{mode.mode}_{SEED}",
    manifest={
        "run_id": f"{mode.mode}_{SEED}",
        "commit": git_head(),
        "notebook_hash": notebook_hash(),
        "mode": mode.to_dict(),
        "dataset_id": DATASET_ID,
        "exact_command": exact_command,
        "flags": {"run_real_data": RUN_REAL_DATA, "run_model": RUN_MODEL, "in_colab": IN_COLAB,
                  "professor_approved_attestation": PROFESSOR_APPROVED},
        "catalog": catalog.to_dict(),
        "acquisition": acquisition.to_dict(),
        "census": census.to_dict(),
        "schema": real_state.schema or None,
        "qc": real_state.qc or None,
        "adequacy": adequacy.to_dict() if hasattr(adequacy, "to_dict") else real_state.adequacy,
        "resource": resource.to_dict() if hasattr(resource, "to_dict") else real_state.resource,
        "estimand": estimand_report.to_dict() if hasattr(estimand_report, "to_dict") else real_state.estimand,
        "split": real_state.split or split_report.to_dict(),
        "paired_deltas": paired_deltas if "paired_deltas" in dir() else [],
        "gates": board.to_dict(),
        "data_size_stages": scale_board.to_dict(),
        "data_scale": data_scale,
        "approval_state": approvals.get("approval_state"),
        "approval_attestation": "P22_PROFESSOR_APPROVED env; date not recorded locally",
        "primary_cap": PRIMARY_CAP,
        "sensitivity_caps": list(SENSITIVITY_CAPS),
        "split_seeds_note": "split seed = base_seed + repeat; model_init_seed=0",
        "model_init_seed": MODEL_INIT_SEED,
        "data_layer_label": real_state.data_layer_label if real_state.data_layer_label != "unknown" else (
            "full_cohort_post_qc" if real_state.qc else "simulation_or_catalog"
        ),
        "atac_branch_label": real_state.atac_branch_label if real_state.atac_branch_label != "unknown" else atac_branch.branch,
        "headline": real_state.headline,
        "metric_rows": metrics_for_package,
        "evidence_buckets": EVIDENCE_BUCKETS,
        "limitations": [
            "Default/safe run is simulation or metadata; not disease evidence.",
            "ATAC peak block absent in H5AD; B2b RNA-only unless fragment build approved.",
            "Capped cell-level models are not the full dataset.",
            "Inferential unit is donor (n≈30), not cell (n≈248998).",
            "GSE280175 is RNA-only validation, not multimodal; matrix not auto-ingested.",
            "Routing weights/gate values are signals, not explanations.",
            "No approval date invented; attestation via P22_PROFESSOR_APPROVED.",
        ],
        "decision": (
            "continue" if REAL_MODE_ACTIVE and mode.allow_model_fit else
            ("revise" if real_state.headline else "stop")
        ),
        "next_decision_owner": "researcher",
        "next_decision": (
            "review real metrics and claim boundary"
            if REAL_MODE_ACTIVE and mode.allow_model_fit
            else "set real_analysis + P22_RUN_REAL_DATA=1 + P22_RUN_MODEL=1 + P22_PROFESSOR_APPROVED=1"
        ),
        "selected_off_ramp": None,
    },
    metrics_rows=metrics_for_package,
    intervention_rows=interventions_for_package,
    validation_rows=validation_for_package,
)
board.set(make_gate("G9", "PASS", evidence={"run_dir": str(package.run_dir)}, notes="lean package path prepared"))
package.manifest["gates"] = board.to_dict()
paths = package.write()
summary_path = write_human_summary(package.run_dir, package.manifest)
# Executed notebook copy is filled by the outer nbconvert runner when present.
executed_candidate = OUTPUT_BASE.parent / "notebooks" / "P22_down_syndrome_all_in_one.executed.ipynb"
copied = copy_executed_notebook(executed_candidate, package.run_dir)

# Simple figure: donor BA bar chart when real metrics exist
figures_dir = Path(paths["figures"])
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    frame = pd.DataFrame(metrics_for_package)
    if not frame.empty and "donor_balanced_accuracy" in frame.columns:
        measured = frame[frame["status"] == "measured"].copy()
        if not measured.empty:
            label_col = "model" if "model" in measured.columns else "name"
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.bar(measured[label_col].astype(str), measured["donor_balanced_accuracy"].astype(float), color="#2F4F4F")
            ax.set_ylim(0, 1.05)
            ax.set_ylabel("Donor balanced accuracy")
            ax.set_title("Donor-held-out comparison")
            ax.tick_params(axis="x", rotation=30)
            fig.tight_layout()
            fig.savefig(figures_dir / "donor_balanced_accuracy.png", dpi=120)
            plt.close(fig)
except Exception as exc:  # noqa: BLE001 — figure is optional
    safe_write_text(figures_dir / "figure_error.txt", str(exc))

gate_df = pd.DataFrame(board.as_rows())
scale_df = pd.DataFrame(scale_board.as_rows())
final_summary = {
    "mode": mode.mode,
    "gates": board.status_map(),
    "data_size_stages": scale_board.status_map(),
    "catalog_cells": (catalog.summary or {}).get("cell_count"),
    "catalog_donors": (catalog.summary or {}).get("donor_count"),
    "raw_cells": census.n_cells_raw,
    "post_qc_cells": (real_state.qc or {}).get("n_cells_post_qc"),
    "post_qc_donors": (real_state.qc or {}).get("n_donors_post_qc"),
    "atac_branch": getattr(atac_branch, "branch", real_state.atac_branch_label),
    "approval_attestation": PROFESSOR_APPROVED,
    "decision": package.manifest["decision"],
    "artifact_paths": {**paths, "summary": str(summary_path), "executed_copy": None if copied is None else str(copied)},
    "evidence_buckets": EVIDENCE_BUCKETS,
    "headline": real_state.headline,
    "claim_boundary": "Separate verified-real / synthetic / metadata-only / blocked.",
}
safe_write_text(OUTPUT_ROOT / "notebook_summary.json", json.dumps(final_summary, indent=2) + "\n")
safe_write_text(OUTPUT_ROOT / "gate_board.json", json.dumps(board.to_dict(), indent=2) + "\n")
safe_write_text(OUTPUT_ROOT / "scale_board.json", json.dumps(scale_board.to_dict(), indent=2) + "\n")
print("=== G0-G9 ===")
print(gate_df.to_string(index=False))
print("=== R1-R6 ===")
print(scale_df.to_string(index=False))
print(json.dumps(final_summary, indent=2))
assert board.get("G0") is not None and board.get("G9").status == "PASS"
assert len(scale_board.status_map()) == 6
"""


def set_source(cell, text: str) -> None:
    # nbformat wants list of lines ending with \n except possibly last
    lines = text.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    cell["source"] = lines
    if cell["cell_type"] == "code":
        cell["outputs"] = []
        cell["execution_count"] = None


def main() -> None:
    nb = json.loads(NB_PATH.read_text())
    assert len(nb["cells"]) == 22, len(nb["cells"])
    updates = {
        0: CELL0,
        1: CELL1,
        4: CELL4,
        6: CELL6,
        7: CELL7,
        8: CELL8,
        9: CELL9,
        10: CELL10,
        11: CELL11,
        12: CELL12,
        13: CELL13,
        14: CELL14,
        15: CELL15,
        16: CELL16,
        17: CELL17,
        18: CELL18,
        19: CELL19,
        20: CELL20,
        21: CELL21,
    }
    for index, text in updates.items():
        set_source(nb["cells"][index], text)
    # Prefer p22 kernel
    nb.setdefault("metadata", {}).setdefault("kernelspec", {})
    nb["metadata"]["kernelspec"] = {
        "display_name": "P22 (Python 3.11)",
        "language": "python",
        "name": "p22",
    }
    NB_PATH.write_text(json.dumps(nb, indent=1) + "\n")
    print(f"updated {NB_PATH} cells {sorted(updates)}")


if __name__ == "__main__":
    main()

"""Full-cohort acquisition, checksum, and backed census helpers.

Real H5AD download and matrix inspection stay behind dated approval. Functions
here implement the workflow completely so approved mode can run without new code;
safe mode only builds planned contracts and blocked reports.
"""

from __future__ import annotations

import hashlib
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from p22.data.catalog import EXPECTED_CELLS, EXPECTED_DONORS, EXPECTED_H5AD_BYTES

DEFAULT_H5AD_URL = (
    "https://datasets.cellxgene.cziscience.com/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad"
)

DONOR_CANDIDATES = ("donor_id", "donor", "sample_id", "sample")
CONDITION_CANDIDATES = ("disease", "condition", "group")
STAGE_CANDIDATES = ("development_stage", "stage", "gestational_week")
SEX_CANDIDATES = ("sex",)
BATCH_CANDIDATES = ("batch", "library_id", "sample_id")
QC_CANDIDATES = ("n_genes_by_counts", "n_genes", "pct_counts_mt", "percent_mito", "total_counts")


@dataclass(frozen=True)
class AcquisitionRecord:
    """R1 immutable acquisition facts."""

    status: str
    dataset_id: str
    collection_id: str
    geo_accession: str
    catalog_cells: int | None
    catalog_donors: int | None
    h5ad_url: str
    expected_bytes: int
    observed_bytes: int | None = None
    sha256: str | None = None
    downloaded_at: str | None = None
    path: str | None = None
    fragment_asset_present: bool | None = None
    blocking_problems: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "dataset_id": self.dataset_id,
            "collection_id": self.collection_id,
            "geo_accession": self.geo_accession,
            "catalog_cells": self.catalog_cells,
            "catalog_donors": self.catalog_donors,
            "h5ad_url": self.h5ad_url,
            "expected_bytes": self.expected_bytes,
            "observed_bytes": self.observed_bytes,
            "sha256": self.sha256,
            "downloaded_at": self.downloaded_at,
            "path": self.path,
            "fragment_asset_present": self.fragment_asset_present,
            "blocking_problems": list(self.blocking_problems),
            "open_questions": list(self.open_questions),
        }


@dataclass(frozen=True)
class CensusReport:
    """R2/R3 full-cohort census before model caps."""

    status: str
    n_cells_raw: int | None = None
    n_donors: int | None = None
    condition_counts: dict[str, int] = field(default_factory=dict)
    donor_table: list[dict[str, Any]] = field(default_factory=list)
    cells_per_donor: dict[str, Any] = field(default_factory=dict)
    pairing: dict[str, Any] = field(default_factory=dict)
    fields: dict[str, Any] = field(default_factory=dict)
    exclusions: list[dict[str, Any]] = field(default_factory=list)
    peak_block_present: bool | None = None
    chr21_annotation_available: bool | None = None
    storage: dict[str, Any] = field(default_factory=dict)
    blocking_problems: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "n_cells_raw": self.n_cells_raw,
            "n_donors": self.n_donors,
            "condition_counts": dict(self.condition_counts),
            "donor_table": list(self.donor_table),
            "cells_per_donor": dict(self.cells_per_donor),
            "pairing": dict(self.pairing),
            "fields": dict(self.fields),
            "exclusions": list(self.exclusions),
            "peak_block_present": self.peak_block_present,
            "chr21_annotation_available": self.chr21_annotation_available,
            "storage": dict(self.storage),
            "blocking_problems": list(self.blocking_problems),
            "open_questions": list(self.open_questions),
            "layer": "full_cohort",
            "not_a_model_cap": True,
        }


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def estimate_download_gb(expected_bytes: int = EXPECTED_H5AD_BYTES) -> float:
    return round(expected_bytes / 1e9, 3)


def planned_acquisition_from_catalog(
    catalog_summary: dict[str, Any],
    *,
    collection_id: str,
    dataset_id: str,
    geo_accession: str = "GSE305153",
    allow_download: bool = False,
) -> AcquisitionRecord:
    """Build R1 record from catalog metadata without downloading."""
    h5ad = catalog_summary.get("h5ad_asset") or {}
    fragment = catalog_summary.get("atac_fragment_asset") or {}
    unknowns = [
        "H5AD not downloaded; checksum pending",
        "byte verification pending local file",
    ]
    blocking: list[str] = []
    if not allow_download:
        blocking.append("download blocked until approved_real_analysis mode and dated approval")
    status = "BLOCKED" if blocking else "INCONCLUSIVE"
    return AcquisitionRecord(
        status=status,
        dataset_id=dataset_id,
        collection_id=collection_id,
        geo_accession=geo_accession,
        catalog_cells=catalog_summary.get("cell_count"),
        catalog_donors=catalog_summary.get("donor_count"),
        h5ad_url=h5ad.get("url") or DEFAULT_H5AD_URL,
        expected_bytes=int(h5ad.get("file_size") or EXPECTED_H5AD_BYTES),
        fragment_asset_present=bool(fragment.get("present")),
        blocking_problems=tuple(blocking),
        open_questions=tuple(unknowns),
    )


def download_h5ad(
    destination: Path,
    url: str = DEFAULT_H5AD_URL,
    expected_bytes: int = EXPECTED_H5AD_BYTES,
    *,
    allow: bool = False,
) -> Path:
    """Download full public H5AD only when ``allow`` is True."""
    if not allow:
        raise PermissionError("H5AD download refused: approved real mode + dated approval required")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and destination.stat().st_size == expected_bytes:
        return destination
    temporary = destination.with_suffix(destination.suffix + ".partial")
    with urllib.request.urlopen(url, timeout=120) as response, temporary.open("wb") as handle:
        while True:
            chunk = response.read(8 * 1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    if temporary.stat().st_size != expected_bytes:
        size = temporary.stat().st_size
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded H5AD size {size} != expected {expected_bytes}")
    temporary.replace(destination)
    return destination


def verify_local_h5ad(
    path: Path,
    expected_bytes: int = EXPECTED_H5AD_BYTES,
) -> dict[str, Any]:
    """Verify local file size and compute SHA256."""
    target = Path(path)
    if not target.is_file():
        return {"ok": False, "reason": f"missing file {target}"}
    size = target.stat().st_size
    digest = sha256_file(target)
    ok = size == expected_bytes
    return {
        "ok": ok,
        "path": str(target),
        "observed_bytes": size,
        "expected_bytes": expected_bytes,
        "sha256": digest,
        "reason": None if ok else f"size mismatch {size} != {expected_bytes}",
    }


def _resolve_column(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    lower = {name.lower(): name for name in columns}
    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    return None


def census_blocked_placeholder(reason: str) -> CensusReport:
    return CensusReport(
        status="BLOCKED",
        blocking_problems=(reason,),
        open_questions=("full-cohort census requires local approved H5AD",),
    )


def run_backed_census(path: Path) -> CensusReport:
    """Open H5AD backed and census every row before any model cap."""
    import anndata as ad

    target = Path(path)
    if not target.is_file():
        return census_blocked_placeholder(f"no H5AD at {target}")

    started = time.perf_counter()
    backed = ad.read_h5ad(target, backed="r")
    obs = backed.obs
    columns = list(obs.columns)
    donor_col = _resolve_column(columns, DONOR_CANDIDATES)
    condition_col = _resolve_column(columns, CONDITION_CANDIDATES)
    stage_col = _resolve_column(columns, STAGE_CANDIDATES)
    sex_col = _resolve_column(columns, SEX_CANDIDATES)
    batch_col = _resolve_column(columns, BATCH_CANDIDATES)
    qc_present = {
        name: _resolve_column(columns, (name,)) is not None or name in columns
        for name in QC_CANDIDATES
    }

    blocking: list[str] = []
    unknowns: list[str] = []
    if donor_col is None:
        blocking.append("donor column absent")
    if condition_col is None:
        blocking.append("condition/disease column absent")

    n_cells = int(backed.n_obs)
    donor_table: list[dict[str, Any]] = []
    condition_counts: dict[str, int] = {}
    cells_per_donor: dict[str, Any] = {}
    if donor_col and condition_col:
        frame = pd.DataFrame(
            {
                "donor_id": obs[donor_col].astype(str).to_numpy(),
                "condition": obs[condition_col].astype(str).to_numpy(),
            }
        )
        purity = frame.groupby("donor_id")["condition"].nunique()
        impure = purity[purity > 1]
        if len(impure):
            blocking.append(f"{len(impure)} donors have mixed condition labels")
        grouped = frame.groupby(["donor_id", "condition"]).size().reset_index(name="n_cells")
        donor_table = grouped.to_dict(orient="records")
        condition_counts = frame["condition"].value_counts().astype(int).to_dict()
        per_donor = frame.groupby("donor_id").size()
        cells_per_donor = {
            "min": int(per_donor.min()),
            "median": float(per_donor.median()),
            "max": int(per_donor.max()),
            "n_donors": int(per_donor.size),
        }

    peak_block = None
    if "feature_types" in backed.var.columns:
        types = backed.var["feature_types"].astype(str).str.lower()
        peak_block = bool(types.str.contains("peak|atac").any())
    elif any(key.lower().startswith("atac") for key in getattr(backed, "obsm", {})):
        peak_block = True
    else:
        peak_block = False
        unknowns.append("ATAC peak block not found in var.feature_types or obsm")

    chr21_available = None
    for column in ("chromosome", "chrom", "seqname", "gene_chrom"):
        if column in backed.var.columns:
            values = backed.var[column].astype(str)
            chr21_available = bool(values.isin(["21", "chr21", "Chr21"]).any())
            break
    if chr21_available is None:
        unknowns.append("chr21 gene annotation column not found")

    pairing = {
        "status": (
            "unknown"
            if peak_block is None
            else ("paired_candidate" if peak_block else "no_peak_block")
        ),
        "same_nucleus_evidence": "same obs rows for RNA/ATAC candidate" if peak_block else "absent",
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    status = "BLOCKED" if blocking else ("INCONCLUSIVE" if unknowns else "PASS")
    if n_cells != EXPECTED_CELLS and not blocking:
        unknowns.append(f"live cell count {n_cells} != expected {EXPECTED_CELLS}")
        status = "INCONCLUSIVE"

    return CensusReport(
        status=status,
        n_cells_raw=n_cells,
        n_donors=cells_per_donor.get("n_donors"),
        condition_counts={str(k): int(v) for k, v in condition_counts.items()},
        donor_table=donor_table,
        cells_per_donor=cells_per_donor,
        pairing=pairing,
        fields={
            "donor": donor_col,
            "condition": condition_col,
            "stage": stage_col,
            "sex": sex_col,
            "batch": batch_col,
            "qc_fields": qc_present,
        },
        exclusions=[],
        peak_block_present=peak_block,
        chr21_annotation_available=chr21_available,
        storage={
            "backed": True,
            "n_vars": int(backed.n_vars),
            "X_type": type(backed.X).__name__,
        },
        blocking_problems=tuple(blocking),
        open_questions=tuple(unknowns),
    )


def data_scale_section(
    acquisition: AcquisitionRecord,
    census: CensusReport,
    *,
    primary_cap: int = 256,
    sensitivity_caps: tuple[int, ...] = (64, 128),
    second_cohort_status: str = "GSE280175 RNA-only planned; multimodal UNKNOWN",
) -> dict[str, Any]:
    """R6 numeric data-scale package section."""
    return {
        "cell_level_scale": {
            "catalog_cells_expected": EXPECTED_CELLS,
            "catalog_cells_observed": acquisition.catalog_cells,
            "raw_cells": census.n_cells_raw,
            "note": "cells are not independent inferential units",
        },
        "inferential_scale": {
            "donors_expected": EXPECTED_DONORS,
            "donors_observed": census.n_donors or acquisition.catalog_donors,
            "unit": "donor",
        },
        "caps": {
            "primary": primary_cap,
            "sensitivity": list(sensitivity_caps),
            "optional_when_resources_permit": [512, "all_retained"],
            "capped_output_is_not_full_dataset": True,
        },
        "layers": {
            "full_cohort": "QC census, donor summaries, pseudobulk over all retained cells",
            "cell_level_model": "primary 256 cells/donor with 64/128 sensitivity",
        },
        "pairing": census.pairing,
        "exclusions": census.exclusions,
        "second_cohort_status": second_cohort_status,
        "acquisition": acquisition.to_dict(),
        "census": census.to_dict(),
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }

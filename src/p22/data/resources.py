"""Resource feasibility and ATAC B1/B2 branch decisions (G3)."""

from __future__ import annotations

import platform
import resource
import shutil
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

PRIMARY_CAP = 256
SENSITIVITY_CAPS = (64, 128)
ATAC_BRANCH_B1 = "B1"
ATAC_BRANCH_B2A = "B2a"
ATAC_BRANCH_B2B = "B2b"
ATAC_BRANCH_UNKNOWN = "unknown"

# A fragment-to-peak build needs room for the compressed fragments, the index,
# and the peak matrix it writes. Two times the download is the floor, not a target.
FRAGMENT_DISK_HEADROOM_FACTOR = 2.0

_T = TypeVar("_T")


@dataclass(frozen=True)
class ResourceMeasurement:
    """Measured or estimated resource facts for one analysis tier."""

    name: str
    cells_per_donor_cap: int | None
    elapsed_seconds: float | None = None
    peak_rss_gb: float | None = None
    disk_free_gb: float | None = None
    input_bytes: int | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "cells_per_donor_cap": self.cells_per_donor_cap,
            "elapsed_seconds": self.elapsed_seconds,
            "peak_rss_gb": self.peak_rss_gb,
            "disk_free_gb": self.disk_free_gb,
            "input_bytes": self.input_bytes,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class AtacBranchDecision:
    """Explicit ATAC availability branch."""

    branch: str
    peak_block_present: bool | None
    fragment_asset_present: bool | None
    fragment_build_approved: bool
    multimodal_claim_allowed: bool
    rationale: str
    not_applicable_models: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch": self.branch,
            "peak_block_present": self.peak_block_present,
            "fragment_asset_present": self.fragment_asset_present,
            "fragment_build_approved": self.fragment_build_approved,
            "multimodal_claim_allowed": self.multimodal_claim_allowed,
            "rationale": self.rationale,
            "not_applicable_models": list(self.not_applicable_models),
        }


@dataclass(frozen=True)
class ResourceReport:
    """G3 resource and modality branch report."""

    status: str
    primary_cap: int = PRIMARY_CAP
    sensitivity_caps: tuple[int, ...] = SENSITIVITY_CAPS
    measurements: list[ResourceMeasurement] = field(default_factory=list)
    atac_branch: AtacBranchDecision | None = None
    blocking_problems: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    environment: dict[str, Any] = field(default_factory=dict)
    fragment_feasibility: dict[str, Any] = field(default_factory=dict)
    storage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "primary_cap": self.primary_cap,
            "sensitivity_caps": list(self.sensitivity_caps),
            "measurements": [item.to_dict() for item in self.measurements],
            "atac_branch": None if self.atac_branch is None else self.atac_branch.to_dict(),
            "blocking_problems": list(self.blocking_problems),
            "open_questions": list(self.open_questions),
            "environment": dict(self.environment),
            "fragment_feasibility": dict(self.fragment_feasibility),
            "storage": dict(self.storage),
        }


def peak_rss_gb() -> float | None:
    """Peak resident set size of this process, in GB."""
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except (AttributeError, OSError, ValueError):
        return None
    # macOS reports bytes; Linux reports kilobytes.
    scale = 1e9 if sys.platform == "darwin" else 1e6
    return round(usage / scale, 4)


def disk_free_gb(path: str | Path) -> float | None:
    try:
        return round(shutil.disk_usage(Path(path)).free / 1e9, 3)
    except OSError:
        return None


def environment_record() -> dict[str, Any]:
    """Hardware and package versions that a resource number only means alongside."""
    from importlib import metadata

    versions: dict[str, str] = {}
    distributions = {
        "numpy": "numpy",
        "pandas": "pandas",
        "scipy": "scipy",
        "sklearn": "scikit-learn",
        "torch": "torch",
        "anndata": "anndata",
        "h5py": "h5py",
    }
    for module_name, distribution in distributions.items():
        try:
            versions[module_name] = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            continue
    try:
        import os

        cpu_count = os.cpu_count()
        page = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        ram_gb: float | None = round(page / 1e9, 3)
    except (AttributeError, OSError, ValueError):
        cpu_count, ram_gb = None, None
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": cpu_count,
        "ram_total_gb": ram_gb,
        "packages": versions,
    }


def measure_stage(
    name: str,
    call: Callable[[], _T],
    *,
    cells_per_donor_cap: int | None = None,
    disk_path: str | Path | None = None,
    input_bytes: int | None = None,
    notes: str = "",
) -> tuple[_T, ResourceMeasurement]:
    """Run ``call`` and record wall time, peak RSS, and free disk around it."""
    started = time.perf_counter()
    result = call()
    elapsed = time.perf_counter() - started
    return result, ResourceMeasurement(
        name=name,
        cells_per_donor_cap=cells_per_donor_cap,
        elapsed_seconds=round(elapsed, 3),
        peak_rss_gb=peak_rss_gb(),
        disk_free_gb=None if disk_path is None else disk_free_gb(disk_path),
        input_bytes=input_bytes,
        notes=notes,
    )


@dataclass(frozen=True)
class FragmentBuildFeasibility:
    """Whether a fragment-to-peak build fits on this machine."""

    feasible: bool
    fragment_bytes: int | None
    required_gb: float | None
    disk_free_gb: float | None
    headroom_factor: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "feasible": self.feasible,
            "fragment_bytes": self.fragment_bytes,
            "required_gb": self.required_gb,
            "disk_free_gb": self.disk_free_gb,
            "headroom_factor": self.headroom_factor,
            "reason": self.reason,
        }


def assess_fragment_build(
    fragment_bytes: int | None,
    free_gb: float | None,
    headroom_factor: float = FRAGMENT_DISK_HEADROOM_FACTOR,
) -> FragmentBuildFeasibility:
    """Decide whether a peak matrix can be built from the fragment asset here."""
    if fragment_bytes is None:
        return FragmentBuildFeasibility(
            feasible=False,
            fragment_bytes=None,
            required_gb=None,
            disk_free_gb=free_gb,
            headroom_factor=headroom_factor,
            reason="fragment asset size unknown; build cost cannot be budgeted",
        )
    required = round(fragment_bytes / 1e9 * headroom_factor, 3)
    if free_gb is None:
        return FragmentBuildFeasibility(
            feasible=False,
            fragment_bytes=int(fragment_bytes),
            required_gb=required,
            disk_free_gb=None,
            headroom_factor=headroom_factor,
            reason="free disk unknown; refusing an unbudgeted multi-gigabyte build",
        )
    if free_gb < required:
        return FragmentBuildFeasibility(
            feasible=False,
            fragment_bytes=int(fragment_bytes),
            required_gb=required,
            disk_free_gb=free_gb,
            headroom_factor=headroom_factor,
            reason=(
                f"fragment build needs about {required} GB "
                f"({round(fragment_bytes / 1e9, 3)} GB download times {headroom_factor}) "
                f"but only {free_gb} GB is free"
            ),
        )
    return FragmentBuildFeasibility(
        feasible=True,
        fragment_bytes=int(fragment_bytes),
        required_gb=required,
        disk_free_gb=free_gb,
        headroom_factor=headroom_factor,
        reason=f"{free_gb} GB free covers the estimated {required} GB build",
    )


def decide_atac_branch(
    peak_block_present: bool | None,
    fragment_asset_present: bool | None,
    fragment_build_approved: bool = False,
    resource_budget_ok: bool = False,
) -> AtacBranchDecision:
    """Choose B1, B2a, or B2b without silent multimodal wording."""
    multimodal_na = ("atac_only", "rna_atac_concat", "gated_fusion")
    if peak_block_present is True:
        return AtacBranchDecision(
            branch=ATAC_BRANCH_B1,
            peak_block_present=True,
            fragment_asset_present=fragment_asset_present,
            fragment_build_approved=False,
            multimodal_claim_allowed=True,
            rationale="same-nucleus peak block present in H5AD; continue multimodal pilot",
        )
    if peak_block_present is False and fragment_asset_present is True:
        if fragment_build_approved and resource_budget_ok:
            return AtacBranchDecision(
                branch=ATAC_BRANCH_B2A,
                peak_block_present=False,
                fragment_asset_present=True,
                fragment_build_approved=True,
                multimodal_claim_allowed=True,
                rationale="peak block absent; fragment build approved under resource budget",
            )
        return AtacBranchDecision(
            branch=ATAC_BRANCH_B2B,
            peak_block_present=False,
            fragment_asset_present=True,
            fragment_build_approved=fragment_build_approved,
            multimodal_claim_allowed=False,
            rationale=(
                "peak block absent; fragment build not approved or budget insufficient; "
                "reframe as RNA-only"
            ),
            not_applicable_models=multimodal_na,
        )
    if peak_block_present is False:
        return AtacBranchDecision(
            branch=ATAC_BRANCH_B2B,
            peak_block_present=False,
            fragment_asset_present=bool(fragment_asset_present),
            fragment_build_approved=False,
            multimodal_claim_allowed=False,
            rationale="no usable ATAC peak block or fragment asset; RNA-only reframe",
            not_applicable_models=multimodal_na,
        )
    return AtacBranchDecision(
        branch=ATAC_BRANCH_UNKNOWN,
        peak_block_present=None,
        fragment_asset_present=fragment_asset_present,
        fragment_build_approved=False,
        multimodal_claim_allowed=False,
        rationale="ATAC peak-block status unknown until H5AD inspection",
        not_applicable_models=multimodal_na,
    )


def build_resource_report(
    measurements: list[ResourceMeasurement] | None = None,
    atac_branch: AtacBranchDecision | None = None,
    h5ad_available: bool = False,
    approval_present: bool = False,
    environment: dict[str, Any] | None = None,
    fragment_feasibility: FragmentBuildFeasibility | None = None,
    storage: dict[str, Any] | None = None,
) -> ResourceReport:
    """Assemble G3 status from measurements and ATAC branch."""
    measurements = list(measurements or [])
    blocking: list[str] = []
    unknowns: list[str] = []

    if not approval_present:
        unknowns.append("approval attestation absent; real matrix load blocked")
    if storage and storage.get("dense_full_matrix_conversion"):
        blocking.append("dense full-matrix conversion detected; backed/chunked reads required")
    if not h5ad_available:
        unknowns.append("local H5AD not loaded; resource measurements are catalog/planned only")
    if atac_branch is None or atac_branch.branch == ATAC_BRANCH_UNKNOWN:
        unknowns.append("ATAC branch unresolved until file-level peak-block inspection")
    if (
        atac_branch is not None
        and atac_branch.branch == ATAC_BRANCH_B2A
        and not any(item.name == "fragment_build" for item in measurements)
    ):
        blocking.append("B2a selected without fragment-build resource measurement")

    primary = next((item for item in measurements if item.cells_per_donor_cap == PRIMARY_CAP), None)
    if h5ad_available and primary is None:
        unknowns.append("primary 256-cell cap measurement missing")

    # Without approval or local H5AD, G3 cannot PASS; report BLOCKED honestly.
    if blocking or not approval_present or not h5ad_available:
        status = "BLOCKED"
    elif unknowns:
        status = "INCONCLUSIVE"
    else:
        status = "PASS"

    return ResourceReport(
        status=status,
        measurements=measurements,
        atac_branch=atac_branch,
        blocking_problems=tuple(blocking),
        open_questions=tuple(unknowns),
        environment=dict(environment or {}),
        fragment_feasibility={} if fragment_feasibility is None else fragment_feasibility.to_dict(),
        storage=dict(storage or {}),
    )

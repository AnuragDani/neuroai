"""Resource feasibility and ATAC B1/B2 branch decisions (G3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PRIMARY_CAP = 256
SENSITIVITY_CAPS = (64, 128)
ATAC_BRANCH_B1 = "B1"
ATAC_BRANCH_B2A = "B2a"
ATAC_BRANCH_B2B = "B2b"
ATAC_BRANCH_UNKNOWN = "unknown"


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "primary_cap": self.primary_cap,
            "sensitivity_caps": list(self.sensitivity_caps),
            "measurements": [item.to_dict() for item in self.measurements],
            "atac_branch": None if self.atac_branch is None else self.atac_branch.to_dict(),
            "blocking_problems": list(self.blocking_problems),
            "open_questions": list(self.open_questions),
        }


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
) -> ResourceReport:
    """Assemble G3 status from measurements and ATAC branch."""
    measurements = list(measurements or [])
    blocking: list[str] = []
    unknowns: list[str] = []

    if not approval_present:
        unknowns.append("dated Professor Fang approval absent; real matrix load blocked")
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
    )

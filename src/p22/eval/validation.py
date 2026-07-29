"""Independent biological validation planning and status (G8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PRIMARY_RNA_VALIDATION = "GSE280175"
SCALE_POOL_CANDIDATE = "GSE305153"


@dataclass(frozen=True)
class ValidationResource:
    """Named external validation resource."""

    accession: str
    modality: str
    role: str
    n_control: int | None = None
    n_case: int | None = None
    available: bool | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "modality": self.modality,
            "role": self.role,
            "n_control": self.n_control,
            "n_case": self.n_case,
            "available": self.available,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ValidationReport:
    """G8 validation gate outcome."""

    status: str
    resources: list[ValidationResource] = field(default_factory=list)
    marker_set: str | None = None
    blocking_problems: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    claim_boundary: str = "RNA-only external validation is not independent multimodal validation"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "resources": [item.to_dict() for item in self.resources],
            "marker_set": self.marker_set,
            "blocking_problems": list(self.blocking_problems),
            "open_questions": list(self.open_questions),
            "claim_boundary": self.claim_boundary,
        }


def default_validation_resources() -> list[ValidationResource]:
    return [
        ValidationResource(
            accession=PRIMARY_RNA_VALIDATION,
            modality="RNA-only",
            role="independent_rna_validation",
            n_control=3,
            n_case=3,
            available=None,
            notes="mid-gestational prenatal human DS brain; too small for multimodal pooling",
        ),
        ValidationResource(
            accession=SCALE_POOL_CANDIDATE,
            modality="multiome_same_study",
            role="scale_pool_candidate_not_independent",
            available=None,
            notes="same-study scale expansion only after disjointness audit",
        ),
        ValidationResource(
            accession="UNKNOWN",
            modality="paired_RNA_ATAC",
            role="independent_multimodal_validation",
            available=False,
            notes="no approved independent paired RNA/ATAC validation accession",
        ),
    ]


def build_validation_report(
    marker_set: str | None = None,
    findings_available: bool = False,
    resources: list[ValidationResource] | None = None,
    approval_present: bool = False,
) -> ValidationReport:
    """Report G8 honestly when validation cannot run."""
    resources = list(resources or default_validation_resources())
    blocking: list[str] = []
    unknowns: list[str] = []

    if not approval_present:
        blocking.append("dated approval absent; real validation run blocked")
    if marker_set is None:
        unknowns.append("marker/enhancer/pathway set unnamed; gate cannot PASS")
    if not findings_available:
        unknowns.append("held-out biological findings unavailable")
    rna = next((item for item in resources if item.accession == PRIMARY_RNA_VALIDATION), None)
    if rna is None:
        blocking.append(f"{PRIMARY_RNA_VALIDATION} missing from validation plan")
    elif rna.available is False:
        blocking.append(f"{PRIMARY_RNA_VALIDATION} unavailable")
    elif rna.available is None:
        unknowns.append(f"{PRIMARY_RNA_VALIDATION} availability not verified locally")

    if blocking:
        status = "BLOCKED"
    elif unknowns or marker_set is None or not findings_available:
        status = "INCONCLUSIVE" if not blocking else "BLOCKED"
        # Without findings or marker set, do not PASS.
        status = "BLOCKED" if not findings_available else "INCONCLUSIVE"
        if marker_set is None:
            status = "BLOCKED"
    else:
        status = "PASS"

    # Default pre-approval posture: BLOCKED.
    if not approval_present or not findings_available or marker_set is None:
        status = "BLOCKED"

    return ValidationReport(
        status=status,
        resources=resources,
        marker_set=marker_set,
        blocking_problems=tuple(blocking),
        open_questions=tuple(unknowns),
    )

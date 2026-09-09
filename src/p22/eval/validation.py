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
            n_control=5,
            n_case=5,
            available=None,
            notes=(
                "5+5 prenatal human snRNA-seq donors; not paired RNA/ATAC validation. "
                "https://www.nature.com/articles/s41467-025-63752-0"
            ),
        ),
        ValidationResource(
            accession=SCALE_POOL_CANDIDATE,
            modality="multiome_same_study",
            role="scale_pool_candidate_not_independent",
            available=None,
            notes="same-study scale expansion only after disjointness audit",
        ),
        ValidationResource(
            accession="nemo:col-umstjg0",
            modality="paired_RNA_ATAC",
            role="independent_multimodal_validation",
            n_control=13,
            n_case=13,
            available=None,
            notes=(
                "Open processed candidate; release/QC, specimen independence and common "
                "ATAC counts pending. Metadata has 117532 cells, published 113801. "
                "https://assets.nemoarchive.org/col-umstjg0"
            ),
        ),
    ]


def build_validation_report(
    marker_set: str | None = None,
    findings_available: bool = False,
    resources: list[ValidationResource] | None = None,
    approval_present: bool = False,
    external_matrix_ingested: bool = False,
    internal_holdout_measured: bool = False,
) -> ValidationReport:
    """Report G8 honestly when validation cannot run.

    ``PASS`` needs an external matrix that was actually harmonised and tested.
    A frozen marker panel measured on held-out donors inside this cohort is
    internal evidence and yields ``INCONCLUSIVE``, never ``PASS``.
    """
    resources = list(resources or default_validation_resources())
    blocking: list[str] = []
    unknowns: list[str] = []

    if not approval_present:
        blocking.append("approval attestation absent; real validation run blocked")
    if marker_set is None:
        unknowns.append("marker/enhancer/pathway set unnamed; gate cannot PASS")
    if not findings_available:
        unknowns.append("held-out biological findings unavailable")
    if not external_matrix_ingested:
        unknowns.append(
            "no external expression matrix was downloaded or harmonised; external "
            "predictive validation is UNKNOWN"
        )
    if internal_holdout_measured:
        unknowns.append(
            "internal held-out marker association is in-cohort evidence, not independent validation"
        )
    rna = next((item for item in resources if item.accession == PRIMARY_RNA_VALIDATION), None)
    if rna is None:
        blocking.append(f"{PRIMARY_RNA_VALIDATION} missing from validation plan")
    elif rna.available is False:
        blocking.append(f"{PRIMARY_RNA_VALIDATION} unavailable")
    elif rna.available is None:
        unknowns.append(
            f"{PRIMARY_RNA_VALIDATION} raw expression-matrix availability not verified locally"
        )

    if blocking or marker_set is None or not findings_available:
        status = "BLOCKED"
    elif not external_matrix_ingested:
        status = "INCONCLUSIVE"
    else:
        status = "PASS"

    return ValidationReport(
        status=status,
        resources=resources,
        marker_set=marker_set,
        blocking_problems=tuple(blocking),
        open_questions=tuple(unknowns),
    )

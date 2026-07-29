"""Frozen estimand, aggregation, margin, and validation plan (G4)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

POSITIVE_CONDITION = "complete trisomy 21"
DONOR_AGGREGATION = "mean_predicted_probability"
DONOR_THRESHOLD = 0.5
PRIMARY_METRIC = "donor_balanced_accuracy"
SPLIT_REPEATS = 5
FOLDS_PER_REPEAT = 5
MODEL_INIT_SEED = 0
PRIMARY_CAP = 256
SENSITIVITY_CAPS = (64, 128)
VALIDATION_RNA_ACCESSION = "GSE280175"
VALIDATION_SCALE_POOL_ACCESSION = "GSE305153"
NAMED_BASELINES = (
    "majority_class",
    "chr21_dosage",
    "qc_covariate_logistic",
    "pseudobulk_rna_logistic",
    "rna_only",
    "atac_only",
    "rna_atac_concat",
    "gated_fusion",
)


def score_resolution(n_control: int, n_ds: int) -> float:
    """Donor-level score resolution from class counts."""
    if n_control < 1 or n_ds < 1:
        raise ValueError("n_control and n_ds must be positive")
    return max(1.0 / (2.0 * n_control), 1.0 / (2.0 * n_ds))


def practical_margin(n_control: int, n_ds: int) -> float:
    """Next two-resolution step, rounded upward to two decimals.

    With 15 donors per class this yields 0.07, not 0.05.
    """
    resolution = score_resolution(n_control, n_ds)
    return math.ceil(2.0 * resolution * 100.0) / 100.0


@dataclass(frozen=True)
class FrozenEstimand:
    """Protocol choices that must not change after predictions."""

    label_rule: str = f"condition == {POSITIVE_CONDITION!r}"
    donor_suffix_role: str = "audit_only"
    donor_aggregation: str = DONOR_AGGREGATION
    donor_threshold: float = DONOR_THRESHOLD
    primary_metric: str = PRIMARY_METRIC
    split_repeats: int = SPLIT_REPEATS
    folds_per_repeat: int = FOLDS_PER_REPEAT
    split_unit: str = "donor"
    split_method: str = "StratifiedGroupKFold"
    model_init_seed: int = MODEL_INIT_SEED
    primary_cap: int = PRIMARY_CAP
    sensitivity_caps: tuple[int, ...] = SENSITIVITY_CAPS
    n_control_donors: int = 15
    n_ds_donors: int = 15
    baselines: tuple[str, ...] = NAMED_BASELINES
    validation_rna_accession: str = VALIDATION_RNA_ACCESSION
    validation_scale_pool_accession: str = VALIDATION_SCALE_POOL_ACCESSION
    validation_multimodal_accession: str | None = None
    marker_set: str | None = None
    frozen: bool = True
    notes: tuple[str, ...] = ()

    @property
    def resolution(self) -> float:
        return score_resolution(self.n_control_donors, self.n_ds_donors)

    @property
    def margin(self) -> float:
        return practical_margin(self.n_control_donors, self.n_ds_donors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label_rule": self.label_rule,
            "donor_suffix_role": self.donor_suffix_role,
            "donor_aggregation": self.donor_aggregation,
            "donor_threshold": self.donor_threshold,
            "primary_metric": self.primary_metric,
            "split_repeats": self.split_repeats,
            "folds_per_repeat": self.folds_per_repeat,
            "split_unit": self.split_unit,
            "split_method": self.split_method,
            "model_init_seed": self.model_init_seed,
            "primary_cap": self.primary_cap,
            "sensitivity_caps": list(self.sensitivity_caps),
            "n_control_donors": self.n_control_donors,
            "n_ds_donors": self.n_ds_donors,
            "score_resolution": self.resolution,
            "practical_margin": self.margin,
            "baselines": list(self.baselines),
            "validation_plan": {
                "rna_only_accession": self.validation_rna_accession,
                "scale_pool_accession": self.validation_scale_pool_accession,
                "independent_multimodal_accession": self.validation_multimodal_accession,
                "marker_set": self.marker_set,
                "rna_only_not_multimodal": True,
            },
            "frozen": self.frozen,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class EstimandGateReport:
    """G4 gate outcome."""

    status: str
    estimand: FrozenEstimand
    blocking_problems: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "estimand": self.estimand.to_dict(),
            "blocking_problems": list(self.blocking_problems),
            "open_questions": list(self.open_questions),
        }


def freeze_estimand(
    n_control_donors: int = 15,
    n_ds_donors: int = 15,
    marker_set: str | None = None,
    multimodal_validation_accession: str | None = None,
    already_predicted: bool = False,
) -> EstimandGateReport:
    """Freeze the estimand before final predictions."""
    estimand = FrozenEstimand(
        n_control_donors=n_control_donors,
        n_ds_donors=n_ds_donors,
        marker_set=marker_set,
        validation_multimodal_accession=multimodal_validation_accession,
        notes=(
            "split seed controls donor assignment; model init seed fixed at 0",
            "donor suffix is audit-only and must agree with condition labels",
        ),
    )
    blocking: list[str] = []
    unknowns: list[str] = []
    if already_predicted:
        blocking.append("estimand cannot be frozen after predictions are visible")
    if estimand.margin < 0.07 and n_control_donors == 15 and n_ds_donors == 15:
        blocking.append("margin rule failed for 15 donors/class; expected >= 0.07")
    if marker_set is None:
        unknowns.append("marker/enhancer/pathway set not named in approval record")
    if multimodal_validation_accession is None:
        unknowns.append("independent multimodal validation accession is UNKNOWN")

    # Protocol freeze can PASS while validation resources remain incomplete;
    # unknowns stay visible so G8 cannot be overclaimed.
    status = "BLOCKED" if blocking else "PASS"
    return EstimandGateReport(
        status=status,
        estimand=estimand,
        blocking_problems=tuple(blocking),
        open_questions=tuple(unknowns),
    )

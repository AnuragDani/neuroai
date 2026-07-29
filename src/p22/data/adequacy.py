"""Donor-level adequacy thresholds and off-ramps (G2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

MIN_DONORS_PER_CONDITION = 15
MIN_PAIRED_CELLS_PER_DONOR = 64
MAX_DONOR_CLASS_RATIO = 1.5
MAX_CELL_CLASS_RATIO = 2.0
MIN_DONOR_GROUPS_FOR_FOLDS = 5
CONDITION_POSITIVE = "complete trisomy 21"
CONDITION_CONTROL = "normal"

OFF_RAMPS = {
    "O1": "scale-pool candidate GSE305153 after disjointness audit",
    "O2": "independent RNA-only validation candidate GSE280175",
    "O3": "reframe as donor-aware cell-state/regulatory description",
}


@dataclass(frozen=True)
class AdequacyThresholds:
    """Numeric thresholds frozen before H5AD matrix inspection."""

    min_donors_per_condition: int = MIN_DONORS_PER_CONDITION
    min_paired_cells_per_donor: int = MIN_PAIRED_CELLS_PER_DONOR
    max_donor_class_ratio: float = MAX_DONOR_CLASS_RATIO
    max_cell_class_ratio: float = MAX_CELL_CLASS_RATIO
    min_donor_groups_for_folds: int = MIN_DONOR_GROUPS_FOR_FOLDS
    positive_label: str = CONDITION_POSITIVE
    control_label: str = CONDITION_CONTROL


@dataclass(frozen=True)
class AdequacyReport:
    """G2 adequacy outcome."""

    status: str
    thresholds: dict[str, Any]
    donor_table: list[dict[str, Any]] = field(default_factory=list)
    checks: dict[str, Any] = field(default_factory=dict)
    blocking_problems: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    selected_off_ramp: str | None = None
    off_ramp_options: dict[str, str] = field(default_factory=lambda: dict(OFF_RAMPS))

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "thresholds": dict(self.thresholds),
            "donor_table": list(self.donor_table),
            "checks": dict(self.checks),
            "blocking_problems": list(self.blocking_problems),
            "open_questions": list(self.open_questions),
            "selected_off_ramp": self.selected_off_ramp,
            "off_ramp_options": dict(self.off_ramp_options),
        }


def _ratio(a: int, b: int) -> float:
    if a <= 0 or b <= 0:
        return float("inf")
    return max(a, b) / min(a, b)


def audit_label_suffix_agreement(
    donor_ids: list[str],
    conditions: list[str],
) -> list[str]:
    """Return problems when donor suffix and condition labels disagree."""
    problems: list[str] = []
    for donor, condition in zip(donor_ids, conditions, strict=True):
        has_ds = "_DS_" in donor
        has_con = "_CON_" in donor
        if has_ds and has_con:
            problems.append(f"donor {donor} has both _DS_ and _CON_ markers")
        if has_ds and condition != CONDITION_POSITIVE:
            problems.append(f"donor {donor} suffix implies DS but condition is {condition!r}")
        if has_con and condition != CONDITION_CONTROL:
            problems.append(f"donor {donor} suffix implies control but condition is {condition!r}")
    return problems


def evaluate_donor_adequacy(
    donor_frame: pd.DataFrame,
    thresholds: AdequacyThresholds | None = None,
    pairing_known: bool = False,
    selected_off_ramp: str | None = None,
) -> AdequacyReport:
    """Evaluate donor-level adequacy against frozen thresholds.

    Expected columns: ``donor_id``, ``condition``, ``n_cells``. Optional
    ``n_paired_cells``. Catalog-only frames without cell counts are reported as
    ``INCONCLUSIVE`` rather than fabricated PASS.
    """
    thresholds = thresholds or AdequacyThresholds()
    threshold_dict = {
        "min_donors_per_condition": thresholds.min_donors_per_condition,
        "min_paired_cells_per_donor": thresholds.min_paired_cells_per_donor,
        "max_donor_class_ratio": thresholds.max_donor_class_ratio,
        "max_cell_class_ratio": thresholds.max_cell_class_ratio,
        "min_donor_groups_for_folds": thresholds.min_donor_groups_for_folds,
    }
    required = {"donor_id", "condition"}
    missing = sorted(required - set(donor_frame.columns))
    if missing:
        return AdequacyReport(
            status="BLOCKED",
            thresholds=threshold_dict,
            blocking_problems=(f"donor frame missing columns: {missing}",),
        )

    frame = donor_frame.copy()
    frame["donor_id"] = frame["donor_id"].astype(str)
    frame["condition"] = frame["condition"].astype(str)
    if frame["donor_id"].duplicated().any():
        return AdequacyReport(
            status="BLOCKED",
            thresholds=threshold_dict,
            blocking_problems=("donor_id is not unique in adequacy table",),
        )

    purity_problems = []
    for donor, group in frame.groupby("donor_id", sort=True):
        conditions = sorted(set(group["condition"]))
        if len(conditions) != 1:
            purity_problems.append(f"donor {donor} maps to conditions {conditions}")

    suffix_problems = audit_label_suffix_agreement(
        frame["donor_id"].tolist(),
        frame["condition"].tolist(),
    )

    donor_counts = frame["condition"].value_counts().to_dict()
    n_control = int(donor_counts.get(thresholds.control_label, 0))
    n_ds = int(donor_counts.get(thresholds.positive_label, 0))
    donor_ratio = _ratio(n_control, n_ds)

    cell_checks: dict[str, Any] = {"available": "n_cells" in frame.columns}
    cell_ratio = None
    min_cells = None
    if "n_cells" in frame.columns:
        cell_totals = frame.groupby("condition")["n_cells"].sum().to_dict()
        cell_ratio = _ratio(
            int(cell_totals.get(thresholds.control_label, 0)),
            int(cell_totals.get(thresholds.positive_label, 0)),
        )
        paired_col = "n_paired_cells" if "n_paired_cells" in frame.columns else "n_cells"
        min_cells = int(frame[paired_col].min()) if len(frame) else 0
        cell_checks.update(
            {
                "cell_totals": {str(k): int(v) for k, v in cell_totals.items()},
                "cell_class_ratio": cell_ratio,
                "min_cells_per_donor": min_cells,
                "paired_column": paired_col,
            }
        )

    blocking: list[str] = []
    unknowns: list[str] = []
    blocking.extend(purity_problems)
    blocking.extend(suffix_problems)

    if n_control < thresholds.min_donors_per_condition:
        blocking.append(f"control donors {n_control} < {thresholds.min_donors_per_condition}")
    if n_ds < thresholds.min_donors_per_condition:
        blocking.append(f"DS donors {n_ds} < {thresholds.min_donors_per_condition}")
    if donor_ratio > thresholds.max_donor_class_ratio:
        blocking.append(f"donor class ratio {donor_ratio:.3f} > {thresholds.max_donor_class_ratio}")
    if n_control + n_ds < thresholds.min_donor_groups_for_folds:
        blocking.append(
            f"total donors {n_control + n_ds} < {thresholds.min_donor_groups_for_folds}"
        )

    if not cell_checks["available"]:
        unknowns.append("post-QC cell counts unavailable; catalog donor counts only")
    else:
        assert min_cells is not None and cell_ratio is not None
        if min_cells < thresholds.min_paired_cells_per_donor:
            blocking.append(
                f"min cells/donor {min_cells} < {thresholds.min_paired_cells_per_donor}"
            )
        if cell_ratio > thresholds.max_cell_class_ratio:
            blocking.append(
                f"cell class ratio {cell_ratio:.3f} > {thresholds.max_cell_class_ratio}"
            )
        if not pairing_known:
            unknowns.append("same-nucleus pairing not yet confirmed from H5AD")

    if selected_off_ramp is not None and selected_off_ramp not in OFF_RAMPS:
        blocking.append(f"unknown off-ramp {selected_off_ramp!r}")

    checks = {
        "n_control_donors": n_control,
        "n_ds_donors": n_ds,
        "donor_class_ratio": donor_ratio,
        "label_purity_ok": not purity_problems,
        "suffix_agreement_ok": not suffix_problems,
        "cells": cell_checks,
        "pairing_known": pairing_known,
    }
    donor_table = frame.to_dict(orient="records")

    if blocking:
        status = "BLOCKED"
    elif unknowns:
        status = "INCONCLUSIVE"
    else:
        status = "PASS"

    return AdequacyReport(
        status=status,
        thresholds=threshold_dict,
        donor_table=donor_table,
        checks=checks,
        blocking_problems=tuple(blocking),
        open_questions=tuple(unknowns),
        selected_off_ramp=selected_off_ramp if status == "BLOCKED" else None,
    )


def catalog_donor_frame(donor_ids: list[str]) -> pd.DataFrame:
    """Build a catalog-only donor table from CELLxGENE donor ID suffixes."""
    rows = []
    for donor in donor_ids:
        if "_DS_" in donor:
            condition = CONDITION_POSITIVE
        elif "_CON_" in donor:
            condition = CONDITION_CONTROL
        else:
            condition = "unknown"
        rows.append({"donor_id": donor, "condition": condition})
    return pd.DataFrame(rows)

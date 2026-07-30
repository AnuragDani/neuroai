"""Held-out interventions for the real-data RNA-only path.

The routing interventions in :mod:`p22.eval.faithfulness` need two modalities and
a gate. When the ATAC branch resolves to B2b there is no second view and no gate,
so those interventions are reported as ``NOT_APPLICABLE`` with the branch reason
rather than quietly skipped.

What can still be tested is whether the prediction depends on the RNA input at
all. These interventions change the held-out RNA block and record what happened
to the cell predictions and to the donor-level metric.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from p22.eval.faithfulness import clamp_to_train_mean, permute_within_donor
from p22.eval.metrics import balanced_accuracy

RNA_PERMUTE = "permute_rna_within_donor"
RNA_CLAMP = "clamp_rna_to_train_mean"
RNA_ZERO = "ablate_rna_input"

RNA_ONLY_INTERVENTIONS = (RNA_PERMUTE, RNA_CLAMP, RNA_ZERO)

ROUTING_INTERVENTIONS_REQUIRING_TWO_VIEWS = (
    "ablate_atac_branch",
    "clamp_atac_to_train_mean",
    "permute_atac_within_donor",
    "branch_clamp",
    "fixed_uniform_route",
)

EVIDENCE_STATEMENT = (
    "held-out intervention evidence under the stated manipulation on real cells; "
    "a routing signal is not an explanation and this is not a causal biological claim"
)


@dataclass(frozen=True)
class RealInterventionEffect:
    """What one intervention did to real held-out predictions."""

    name: str
    target: str | None
    status: str
    cell_flip_rate: float | None = None
    donor_agreement: float | None = None
    donor_metric_before: float | None = None
    donor_metric_after: float | None = None
    donor_metric_drop: float | None = None
    n_cells: int | None = None
    n_donors: int | None = None
    not_applicable: str | None = None
    evidence: str = EVIDENCE_STATEMENT
    detail: dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> dict[str, Any]:
        return {
            "intervention": self.name,
            "target": self.target or "-",
            "status": self.status,
            "cell_flip_rate": self.cell_flip_rate,
            "donor_prediction_agreement": self.donor_agreement,
            "donor_balanced_accuracy_before": self.donor_metric_before,
            "donor_balanced_accuracy_after": self.donor_metric_after,
            "donor_balanced_accuracy_drop": self.donor_metric_drop,
            "n_cells": self.n_cells,
            "n_donors": self.n_donors,
            "not_applicable": self.not_applicable,
            "evidence": self.evidence,
        }


def routing_not_applicable(reason: str) -> list[RealInterventionEffect]:
    """Mark every gate/second-modality intervention as not applicable."""
    return [
        RealInterventionEffect(
            name=name,
            target=None,
            status="NOT_APPLICABLE",
            not_applicable=reason,
        )
        for name in ROUTING_INTERVENTIONS_REQUIRING_TWO_VIEWS
    ]


def _donor_scores(
    probability: np.ndarray,
    donors: np.ndarray,
    labels: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    frame = pd.DataFrame({"donor_id": donors, "p": probability, "y": labels})
    grouped = frame.groupby("donor_id", sort=True).agg(
        p=("p", "mean"), y=("y", lambda values: int(values.mode().iloc[0]))
    )
    return (
        grouped.index.to_numpy(dtype=object),
        (grouped["p"].to_numpy() >= 0.5).astype(int),
        grouped["y"].to_numpy(dtype=int),
    )


def run_rna_only_interventions(
    train_matrix: np.ndarray,
    train_labels: np.ndarray,
    test_matrix: np.ndarray,
    test_labels: np.ndarray,
    test_donors: Sequence[str],
    branch_reason: str,
    seed: int = 0,
) -> list[RealInterventionEffect]:
    """Fit on training cells, then intervene on the held-out RNA block only.

    The model is fitted once on the training fold. Every intervention changes the
    held-out matrix, never the fitted model, so the comparison isolates input
    dependence rather than retraining noise.
    """
    x_train = np.asarray(train_matrix, dtype=np.float64)
    x_test = np.asarray(test_matrix, dtype=np.float64)
    y_train = np.asarray(train_labels, dtype=int)
    y_test = np.asarray(test_labels, dtype=int)
    donors = np.asarray([str(value) for value in test_donors], dtype=object)

    scaler = StandardScaler().fit(x_train)
    scaled_train = scaler.transform(x_train)
    scaled_test = scaler.transform(x_test)
    model = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=0)
    model.fit(scaled_train, y_train)

    base_probability = model.predict_proba(scaled_test)[:, 1]
    base_cell_labels = (base_probability >= 0.5).astype(int)
    _, base_donor_prediction, donor_truth = _donor_scores(base_probability, donors, y_test)
    before = balanced_accuracy(donor_truth, base_donor_prediction)

    effects: list[RealInterventionEffect] = []
    for name in RNA_ONLY_INTERVENTIONS:
        if name == RNA_PERMUTE:
            changed = permute_within_donor(scaled_test, donors, seed=seed)
        elif name == RNA_CLAMP:
            changed = clamp_to_train_mean(scaled_test, scaled_train)
        else:
            changed = np.zeros_like(scaled_test)
        probability = model.predict_proba(changed)[:, 1]
        cell_labels = (probability >= 0.5).astype(int)
        _, donor_prediction, _ = _donor_scores(probability, donors, y_test)
        after = balanced_accuracy(donor_truth, donor_prediction)
        drop = (
            None
            if not (before.applicable and after.applicable)
            else float(before.value - after.value)
        )
        effects.append(
            RealInterventionEffect(
                name=name,
                target="rna",
                status="measured",
                cell_flip_rate=float((cell_labels != base_cell_labels).mean()),
                donor_agreement=float((donor_prediction == base_donor_prediction).mean()),
                donor_metric_before=before.value,
                donor_metric_after=after.value,
                donor_metric_drop=drop,
                n_cells=int(y_test.size),
                n_donors=int(donor_truth.size),
                detail={"seed": seed},
            )
        )
    effects.extend(routing_not_applicable(branch_reason))
    return effects


def intervention_rows(effects: Sequence[RealInterventionEffect]) -> list[dict[str, Any]]:
    return [effect.to_row() for effect in effects]

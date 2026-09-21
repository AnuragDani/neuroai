"""Held-out faithfulness interventions and initialization sensitivity for the real paired path.

The generic routing interventions in :mod:`p22.eval.faithfulness` report cell-level
effects. The paired study's endpoint is donor-level, so this module reuses the same
held-out manipulations but scores the donor-aggregated balanced accuracy before and
after each intervention. That keeps an intervention result comparable with the
primary cross-attention vs matched token-concat donor contrast.

The vocabulary stays descriptive: an effect here is intervention evidence under a
stated manipulation on held-out cells, not a causal statement about biology, and a
routing weight is not an explanation.

Only two-view fusion models are eligible. A model without a gate has no route to
fix, so ``fixed_uniform_route`` is reported as ``NOT_APPLICABLE`` rather than
silently skipped.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

from p22.data.group_splits import aggregate_donor_probabilities
from p22.eval.faithfulness import (
    ABLATE_VIEW_A,
    ABLATE_VIEW_B,
    CLAMP_VIEW_A,
    CLAMP_VIEW_B,
    INTERVENTIONS,
    PERMUTE_VIEW_A,
    PERMUTE_VIEW_B,
    UNIFORM_ROUTE,
    clamp_to_train_mean,
    permute_within_donor,
    predict_with,
)
from p22.eval.metrics import balanced_accuracy
from p22.models.fusion import VIEW_A, VIEW_B, VIEW_NAMES

EVIDENCE_STATEMENT = (
    "held-out donor-level intervention evidence under the stated manipulation; "
    "a routing weight is not an explanation and this is not a causal biological claim"
)


def donor_balanced_accuracy(
    probability: np.ndarray,
    donors: Sequence[Any] | np.ndarray,
    labels: Sequence[int] | np.ndarray,
) -> dict[str, Any]:
    """Aggregate cell probabilities to donors, then score donor balanced accuracy.

    Uses the same mean-probability aggregation and 0.5 donor threshold as the
    paired estimand so an intervention can be judged against the primary endpoint.
    """
    probs = np.asarray(probability, dtype=float)
    donor_ids = np.asarray([str(value) for value in np.asarray(donors)], dtype=object)
    truth = np.asarray(labels, dtype=int)
    if probs.ndim != 1 or donor_ids.size != truth.size or probs.size != truth.size:
        raise ValueError("probability, donor_ids and labels must be equal-length vectors")
    table = aggregate_donor_probabilities(probs, donor_ids)
    donor_truth = pd.Series(truth, index=donor_ids).groupby(level=0).first()
    table["label"] = table.donor_id.map(donor_truth).astype(int)
    metric = balanced_accuracy(table.label, table.prediction)
    return {
        "value": metric.value,
        "applicable": bool(metric.applicable),
        "n_donors": int(len(table)),
        "n_control": int((table.label == 0).sum()),
        "n_positive": int((table.label == 1).sum()),
    }


def _changed_inputs(name, test_views, train_views, donors, seed):
    changed = dict(test_views)
    ablate: tuple[str, ...] = ()
    override: list[float] | None = None
    if name in (CLAMP_VIEW_A, CLAMP_VIEW_B):
        target = VIEW_A if name == CLAMP_VIEW_A else VIEW_B
        changed[target] = clamp_to_train_mean(test_views[target], train_views[target])
    elif name in (PERMUTE_VIEW_A, PERMUTE_VIEW_B):
        target = VIEW_A if name == PERMUTE_VIEW_A else VIEW_B
        changed[target] = permute_within_donor(test_views[target], donors, seed=seed)
    elif name in (ABLATE_VIEW_A, ABLATE_VIEW_B):
        ablate = (VIEW_A if name == ABLATE_VIEW_A else VIEW_B,)
    elif name == UNIFORM_ROUTE:
        override = [0.5, 0.5]
    else:
        raise ValueError(f"unknown intervention {name!r}")
    return changed, ablate, override


def run_donor_interventions(
    model: Any,
    test_views: Mapping[str, np.ndarray],
    train_views: Mapping[str, np.ndarray],
    labels: Sequence[int] | np.ndarray,
    donors: Sequence[Any] | np.ndarray,
    *,
    seed: int = 0,
) -> list[dict[str, Any]]:
    """Run all seven held-out interventions and score the donor-level metric.

    The model is fitted once by the caller and never retrained here, so the
    comparison isolates input dependence from retraining noise. The clamp value
    comes from the training views, never the held-out cells.

    Raises:
        ValueError: if the views are not the two expected fusion views.
    """
    if set(test_views) != set(VIEW_NAMES) or set(train_views) != set(VIEW_NAMES):
        raise ValueError(f"paired interventions need views {sorted(VIEW_NAMES)}")
    has_gate = bool(getattr(model, "has_gate", False))
    baseline = predict_with(model, test_views)
    base_donor = donor_balanced_accuracy(baseline.probabilities[:, 1], donors, labels)
    rows: list[dict[str, Any]] = []
    for name in INTERVENTIONS:
        target = _target_view(name)
        if name == UNIFORM_ROUTE and not has_gate:
            rows.append(
                {
                    "intervention": name,
                    "target": None,
                    "status": "NOT_APPLICABLE",
                    "cell_flip_rate": None,
                    "mean_confidence_drop": None,
                    "donor_balanced_accuracy_before": base_donor["value"],
                    "donor_balanced_accuracy_after": None,
                    "donor_balanced_accuracy_drop": None,
                    "routing_shift": None,
                    "n_cells": int(np.asarray(labels).size),
                    "n_donors": base_donor["n_donors"],
                    "not_applicable": "this model has no gate, so there is no route to fix",
                    "evidence": EVIDENCE_STATEMENT,
                }
            )
            continue
        changed, ablate, override = _changed_inputs(name, test_views, train_views, donors, seed)
        after = predict_with(model, changed, ablate_views=ablate, route_override=override)
        after_donor = donor_balanced_accuracy(after.probabilities[:, 1], donors, labels)
        flipped = baseline.labels != after.labels
        drop = None
        if base_donor["applicable"] and after_donor["applicable"]:
            drop = float(base_donor["value"] - after_donor["value"])
        routing_shift = None
        if has_gate and baseline.routing_weights is not None and after.routing_weights is not None:
            routing_shift = float(
                np.abs(baseline.routing_weights[:, 0] - after.routing_weights[:, 0]).mean()
            )
        rows.append(
            {
                "intervention": name,
                "target": target,
                "status": "measured",
                "cell_flip_rate": float(flipped.mean()),
                "mean_confidence_drop": float((baseline.confidence - after.confidence).mean()),
                "donor_balanced_accuracy_before": base_donor["value"],
                "donor_balanced_accuracy_after": after_donor["value"],
                "donor_balanced_accuracy_drop": drop,
                "routing_shift": routing_shift,
                "n_cells": int(np.asarray(labels).size),
                "n_donors": base_donor["n_donors"],
                "not_applicable": None,
                "evidence": EVIDENCE_STATEMENT,
            }
        )
    return rows


def initialization_seed_spread(records: Mapping[int, float]) -> dict[str, Any]:
    """Summarise donor-level scores across initialization seeds.

    This is initialization sensitivity, not split-seed variability: the donor
    split is held fixed and only the model initialization/optimization seed
    changes. A zero spread means the score did not move; it is not a stability
    guarantee beyond the seeds actually run.
    """
    if not records:
        raise ValueError("at least one seed record is required")
    values = np.asarray([records[seed] for seed in sorted(records)], dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("seed scores must be finite")
    return {
        "seeds": sorted(records),
        "scores": {int(seed): float(records[seed]) for seed in sorted(records)},
        "min": float(values.min()),
        "max": float(values.max()),
        "mean": float(values.mean()),
        "spread": float(values.max() - values.min()),
        "n_seeds": int(values.size),
        "evidence": "initialization-seed sensitivity with the donor split held fixed",
    }


def _target_view(name: str) -> str | None:
    if name in (CLAMP_VIEW_A, PERMUTE_VIEW_A, ABLATE_VIEW_A):
        return VIEW_A
    if name in (CLAMP_VIEW_B, PERMUTE_VIEW_B, ABLATE_VIEW_B):
        return VIEW_B
    return None

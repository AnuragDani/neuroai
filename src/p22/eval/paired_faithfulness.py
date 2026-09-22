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


def _mean_or_none(values: Sequence[float]) -> float | None:
    usable = [float(value) for value in values if value is not None and np.isfinite(value)]
    return float(np.mean(usable)) if usable else None


def aggregate_interventions(
    fold_tables: Mapping[str, Sequence[Sequence[dict[str, Any]]]],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Aggregate per-fold intervention rows across folds for every family.

    ``fold_tables`` maps a model family to a sequence of per-fold intervention
    tables, each produced by :func:`run_donor_interventions`. The result keeps one
    entry per (family, intervention) and reports how many folds measured it versus
    refused it as not applicable, the mean donor balanced accuracy before and after
    over measured folds, the mean and range of the drop, and the mean routing shift
    where a gate exists. Means never treat a refusal as a zero effect.
    """
    if not fold_tables:
        raise ValueError("at least one family is required")
    aggregated: dict[str, dict[str, dict[str, Any]]] = {}
    for family, tables in fold_tables.items():
        if not tables:
            raise ValueError(f"family {family!r} has no fold tables")
        by_intervention: dict[str, list[dict[str, Any]]] = {}
        for rows in tables:
            for row in rows:
                by_intervention.setdefault(str(row["intervention"]), []).append(row)
        summary: dict[str, dict[str, Any]] = {}
        for name in INTERVENTIONS:
            rows = by_intervention.get(name)
            if not rows:
                raise ValueError(f"family {family!r} is missing intervention {name!r}")
            measured = [row for row in rows if row.get("status") == "measured"]
            not_applicable = [row for row in rows if row.get("status") == "NOT_APPLICABLE"]
            if len(measured) + len(not_applicable) != len(rows):
                raise ValueError(f"family {family!r} intervention {name!r} has an unknown status")
            drops = [row.get("donor_balanced_accuracy_drop") for row in measured]
            finite_drops = [
                float(value) for value in drops if value is not None and np.isfinite(value)
            ]
            summary[name] = {
                "intervention": name,
                "n_folds": len(rows),
                "n_folds_measured": len(measured),
                "n_folds_not_applicable": len(not_applicable),
                "donor_balanced_accuracy_before_mean": _mean_or_none(
                    [row.get("donor_balanced_accuracy_before") for row in measured]
                ),
                "donor_balanced_accuracy_after_mean": _mean_or_none(
                    [row.get("donor_balanced_accuracy_after") for row in measured]
                ),
                "donor_balanced_accuracy_drop_mean": _mean_or_none(drops),
                "donor_balanced_accuracy_drop_min": (
                    float(min(finite_drops)) if finite_drops else None
                ),
                "donor_balanced_accuracy_drop_max": (
                    float(max(finite_drops)) if finite_drops else None
                ),
                "cell_flip_rate_mean": _mean_or_none(
                    [row.get("cell_flip_rate") for row in measured]
                ),
                "mean_confidence_drop_mean": _mean_or_none(
                    [row.get("mean_confidence_drop") for row in measured]
                ),
                "routing_shift_mean": _mean_or_none([row.get("routing_shift") for row in measured]),
                "evidence": EVIDENCE_STATEMENT,
            }
        aggregated[str(family)] = summary
    return aggregated


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

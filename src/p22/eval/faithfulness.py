"""Held-out interventions that test whether a prediction depends on a routed view.

A high routing weight says the gate scaled a branch. It does not say the prediction would
change if that branch carried different values. These interventions change one view on
held-out cells and record what happened to the predictions.

Two constraints matter. Permutations shuffle values *within* a donor, so a donor's own
distribution is preserved and the effect cannot be explained by moving cells between
donors. And the vocabulary stays descriptive: an effect here is intervention evidence
under a stated manipulation on synthetic data, not a causal statement about biology.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import torch

from p22.eval.metrics import MetricValue, accuracy, balanced_accuracy
from p22.models.fusion import VIEW_A, VIEW_B, VIEW_NAMES, FusionOutput

CLAMP_VIEW_A = "clamp_view_a"
CLAMP_VIEW_B = "clamp_view_b"
PERMUTE_VIEW_A = "permute_view_a_within_donor"
PERMUTE_VIEW_B = "permute_view_b_within_donor"
ABLATE_VIEW_A = "ablate_view_a_embedding"
ABLATE_VIEW_B = "ablate_view_b_embedding"
UNIFORM_ROUTE = "fixed_uniform_route"

INTERVENTIONS = (
    CLAMP_VIEW_A,
    CLAMP_VIEW_B,
    PERMUTE_VIEW_A,
    PERMUTE_VIEW_B,
    ABLATE_VIEW_A,
    ABLATE_VIEW_B,
    UNIFORM_ROUTE,
)

EVIDENCE_STATEMENT = (
    "intervention evidence under the stated manipulation on held-out synthetic cells; "
    "not a causal claim about biology"
)


@dataclass(frozen=True)
class Prediction:
    """One prediction pass over held-out cells."""

    labels: np.ndarray
    probabilities: np.ndarray
    routing_weights: np.ndarray | None

    @property
    def confidence(self) -> np.ndarray:
        return self.probabilities.max(axis=1)


@dataclass(frozen=True)
class InterventionEffect:
    """What one intervention did to the predictions.

    Attributes:
        name: intervention name.
        target_view: the view manipulated, or ``None`` for a route-level change.
        flip_rate: share of held-out cells whose predicted label changed.
        mean_confidence_drop: mean drop in top-label probability, positive when the
            intervention made the model less confident.
        metric_name: metric compared before and after.
        metric_before: metric on the untouched held-out cells.
        metric_after: metric after the intervention.
        metric_drop: ``metric_before - metric_after``; negative means it improved.
        routing_shift: mean absolute change in routing weight on view A, or ``None``
            when the model has no gate.
        per_donor: flip rate and metric drop for each donor.
        per_label: flip rate and metric drop for each true label.
        n_cells: held-out cells used.
        not_applicable: reason the intervention does not apply to this model.
        evidence: the sentence describing what this number is.
    """

    name: str
    target_view: str | None
    flip_rate: float | None
    mean_confidence_drop: float | None
    metric_name: str
    metric_before: float | None
    metric_after: float | None
    metric_drop: float | None
    routing_shift: float | None
    per_donor: dict[str, dict[str, float | None]] = field(default_factory=dict)
    per_label: dict[str, dict[str, float | None]] = field(default_factory=dict)
    n_cells: int = 0
    not_applicable: str | None = None
    evidence: str = EVIDENCE_STATEMENT

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "target_view": self.target_view,
            "flip_rate": self.flip_rate,
            "mean_confidence_drop": self.mean_confidence_drop,
            "metric_name": self.metric_name,
            "metric_before": self.metric_before,
            "metric_after": self.metric_after,
            "metric_drop": self.metric_drop,
            "routing_shift": self.routing_shift,
            "per_donor": self.per_donor,
            "per_label": self.per_label,
            "n_cells": self.n_cells,
            "not_applicable": self.not_applicable,
            "evidence": self.evidence,
        }


def permute_within_donor(
    matrix: np.ndarray,
    donor_ids: Sequence[Any] | np.ndarray,
    seed: int = 0,
) -> np.ndarray:
    """Shuffle rows within each donor, never across donors.

    Args:
        matrix: ``(n_cells, n_features)`` matrix.
        donor_ids: donor identifier per cell.
        seed: seed for the shuffle.

    Returns:
        A copy whose rows have been permuted inside each donor block.

    Raises:
        ValueError: if the shapes disagree or the matrix is not two-dimensional.
    """
    array = np.asarray(matrix)
    if array.ndim != 2:
        raise ValueError(f"matrix must be two-dimensional, got shape {array.shape}")
    donors = np.asarray([str(value) for value in np.asarray(donor_ids)], dtype=object)
    if donors.size != array.shape[0]:
        raise ValueError(
            f"donor_ids covers {donors.size} cells but matrix has {array.shape[0]} rows"
        )
    rng = np.random.default_rng(seed)
    permuted = array.copy()
    for donor in np.unique(donors):
        rows = np.flatnonzero(donors == donor)
        if rows.size < 2:
            continue
        permuted[rows] = array[rng.permutation(rows)]
    return permuted


def clamp_to_train_mean(
    matrix: np.ndarray,
    train_matrix: np.ndarray,
) -> np.ndarray:
    """Replace every value with the training-set feature mean.

    Using the training mean, rather than zero or a held-out mean, keeps the
    intervention inside the distribution the model was fitted on and avoids reading
    held-out values.

    Raises:
        ValueError: if feature counts disagree.
    """
    array = np.asarray(matrix, dtype=np.float64)
    reference = np.asarray(train_matrix, dtype=np.float64)
    if array.ndim != 2 or reference.ndim != 2:
        raise ValueError("clamp_to_train_mean needs two-dimensional matrices")
    if array.shape[1] != reference.shape[1]:
        raise ValueError(
            f"matrix has {array.shape[1]} features but the training matrix has {reference.shape[1]}"
        )
    return np.tile(reference.mean(axis=0), (array.shape[0], 1))


def predict_with(
    model: Any,
    views: Mapping[str, np.ndarray],
    ablate_views: Sequence[str] = (),
    route_override: Sequence[float] | None = None,
) -> Prediction:
    """Run a fusion model and return labels, probabilities, and routing weights.

    Args:
        model: a two-view fusion model.
        views: both views for the cells to predict.
        ablate_views: view names whose embedding is replaced by zeros.
        route_override: fixed routing vector, for gated models only.

    Returns:
        A :class:`Prediction`.

    Raises:
        ValueError: if a view is missing, or a route override is asked of a model
            without a gate.
    """
    missing = [name for name in VIEW_NAMES if name not in views]
    if missing:
        raise ValueError(f"intervention needs view(s) {missing}")
    if route_override is not None and not getattr(model, "has_gate", False):
        raise ValueError("a route override needs a gated model; this model has no gate to override")
    tensors = {
        name: torch.as_tensor(np.asarray(views[name], dtype=np.float32)) for name in VIEW_NAMES
    }
    kwargs: dict[str, Any] = {}
    if ablate_views:
        kwargs["ablate_views"] = tuple(ablate_views)
    if route_override is not None:
        kwargs["route_override"] = list(route_override)
    model.eval()
    with torch.no_grad():
        output = model(tensors[VIEW_A], tensors[VIEW_B], **kwargs)
    if not isinstance(output, FusionOutput):
        raise ValueError("interventions expect a fusion model returning a FusionOutput")
    probabilities = torch.softmax(output.logits, dim=1).cpu().numpy()
    return Prediction(
        labels=probabilities.argmax(axis=1),
        probabilities=probabilities,
        routing_weights=output.routing_weights.cpu().numpy(),
    )


def run_intervention(
    name: str,
    model: Any,
    views: Mapping[str, np.ndarray],
    labels: np.ndarray,
    donor_ids: Sequence[Any] | np.ndarray,
    train_views: Mapping[str, np.ndarray] | None = None,
    metric_name: str = "balanced_accuracy",
    seed: int = 0,
    baseline: Prediction | None = None,
) -> InterventionEffect:
    """Apply one intervention to held-out cells and describe what changed.

    Args:
        name: one of :data:`INTERVENTIONS`.
        model: a two-view fusion model.
        views: held-out views.
        labels: held-out true labels.
        donor_ids: held-out donor identifier per cell.
        train_views: training views, required for the clamp interventions because the
            clamp value comes from training data.
        metric_name: ``accuracy`` or ``balanced_accuracy``.
        seed: seed for permutation interventions.
        baseline: optional untouched prediction, to avoid recomputing it.

    Returns:
        An :class:`InterventionEffect`. For a model without a gate, the uniform-route
        intervention returns a ``not_applicable`` reason instead of a number.

    Raises:
        ValueError: on an unknown intervention or metric, mismatched shapes, or a
            clamp intervention without training views.
    """
    if name not in INTERVENTIONS:
        raise ValueError(f"unknown intervention {name!r}; expected one of {INTERVENTIONS}")
    metric_fn = {"accuracy": accuracy, "balanced_accuracy": balanced_accuracy}.get(metric_name)
    if metric_fn is None:
        raise ValueError(
            f"metric_name must be 'accuracy' or 'balanced_accuracy', got {metric_name!r}"
        )
    truth = np.asarray(labels)
    donors = np.asarray([str(value) for value in np.asarray(donor_ids)], dtype=object)
    if donors.size != truth.size:
        raise ValueError(f"donor_ids covers {donors.size} cells but labels cover {truth.size}")
    for view_name in VIEW_NAMES:
        if view_name not in views:
            raise ValueError(f"intervention needs view {view_name!r}")
        if np.asarray(views[view_name]).shape[0] != truth.size:
            raise ValueError(
                f"view {view_name!r} has {np.asarray(views[view_name]).shape[0]} cells but "
                f"labels cover {truth.size}"
            )

    target_view = _target_view(name)
    if name in (CLAMP_VIEW_A, CLAMP_VIEW_B) and (
        train_views is None or target_view not in train_views
    ):
        raise ValueError(
            f"{name} needs train_views[{target_view!r}] so the clamp value comes from "
            "training data rather than held-out cells"
        )

    before = baseline if baseline is not None else predict_with(model, views)
    metric_before = metric_fn(truth, before.labels)

    has_gate = bool(getattr(model, "has_gate", False))
    if name == UNIFORM_ROUTE and not has_gate:
        return InterventionEffect(
            name=name,
            target_view=None,
            flip_rate=None,
            mean_confidence_drop=None,
            metric_name=metric_name,
            metric_before=metric_before.value,
            metric_after=None,
            metric_drop=None,
            routing_shift=None,
            n_cells=int(truth.size),
            not_applicable="this model has no gate, so there is no route to fix",
        )

    changed_views = dict(views)
    ablate: tuple[str, ...] = ()
    override: list[float] | None = None
    if name in (CLAMP_VIEW_A, CLAMP_VIEW_B):
        changed_views[target_view] = clamp_to_train_mean(
            views[target_view], train_views[target_view]
        )
    elif name in (PERMUTE_VIEW_A, PERMUTE_VIEW_B):
        changed_views[target_view] = permute_within_donor(views[target_view], donors, seed=seed)
    elif name in (ABLATE_VIEW_A, ABLATE_VIEW_B):
        ablate = (target_view,)
    else:
        override = [0.5, 0.5]

    after = predict_with(model, changed_views, ablate_views=ablate, route_override=override)
    metric_after = metric_fn(truth, after.labels)

    flipped = before.labels != after.labels
    confidence_drop = before.confidence - after.confidence
    routing_shift = None
    if before.routing_weights is not None and after.routing_weights is not None and has_gate:
        routing_shift = float(
            np.abs(before.routing_weights[:, 0] - after.routing_weights[:, 0]).mean()
        )

    return InterventionEffect(
        name=name,
        target_view=target_view,
        flip_rate=float(flipped.mean()),
        mean_confidence_drop=float(confidence_drop.mean()),
        metric_name=metric_name,
        metric_before=metric_before.value,
        metric_after=metric_after.value,
        metric_drop=_difference(metric_before, metric_after),
        routing_shift=routing_shift,
        per_donor=_grouped(donors, flipped, truth, before.labels, after.labels, metric_fn),
        per_label=_grouped(
            np.asarray([f"class_{value}" for value in truth], dtype=object),
            flipped,
            truth,
            before.labels,
            after.labels,
            metric_fn,
        ),
        n_cells=int(truth.size),
    )


def run_all_interventions(
    model: Any,
    views: Mapping[str, np.ndarray],
    labels: np.ndarray,
    donor_ids: Sequence[Any] | np.ndarray,
    train_views: Mapping[str, np.ndarray] | None = None,
    metric_name: str = "balanced_accuracy",
    seed: int = 0,
) -> dict[str, InterventionEffect]:
    """Run all seven interventions on one model, sharing the untouched prediction."""
    baseline = predict_with(model, views)
    return {
        name: run_intervention(
            name,
            model,
            views,
            labels,
            donor_ids,
            train_views=train_views,
            metric_name=metric_name,
            seed=seed,
            baseline=baseline,
        )
        for name in INTERVENTIONS
    }


def intervention_table(effects: Mapping[str, InterventionEffect]) -> list[dict[str, Any]]:
    """Flatten intervention effects into rows for a report or a notebook table."""
    rows = []
    for name in INTERVENTIONS:
        if name not in effects:
            continue
        effect = effects[name]
        rows.append(
            {
                "intervention": name,
                "target_view": effect.target_view or "-",
                "flip_rate": effect.flip_rate,
                "confidence_drop": effect.mean_confidence_drop,
                f"{effect.metric_name}_before": effect.metric_before,
                f"{effect.metric_name}_after": effect.metric_after,
                "metric_drop": effect.metric_drop,
                "routing_shift": effect.routing_shift,
                "status": effect.not_applicable or "measured",
            }
        )
    return rows


def _target_view(name: str) -> str | None:
    if name in (CLAMP_VIEW_A, PERMUTE_VIEW_A, ABLATE_VIEW_A):
        return VIEW_A
    if name in (CLAMP_VIEW_B, PERMUTE_VIEW_B, ABLATE_VIEW_B):
        return VIEW_B
    return None


def _difference(before: MetricValue, after: MetricValue) -> float | None:
    if before.value is None or after.value is None:
        return None
    return float(before.value - after.value)


def _grouped(
    keys: np.ndarray,
    flipped: np.ndarray,
    truth: np.ndarray,
    before_labels: np.ndarray,
    after_labels: np.ndarray,
    metric_fn: Any,
) -> dict[str, dict[str, float | None]]:
    """Summarise flip rate and metric drop for each group of cells."""
    summary: dict[str, dict[str, float | None]] = {}
    for key in np.unique(keys):
        mask = keys == key
        before = metric_fn(truth[mask], before_labels[mask])
        after = metric_fn(truth[mask], after_labels[mask])
        summary[str(key)] = {
            "n_cells": int(mask.sum()),
            "flip_rate": float(flipped[mask].mean()),
            "metric_before": before.value,
            "metric_after": after.value,
            "metric_drop": _difference(before, after),
            "not_applicable": before.not_applicable or after.not_applicable,
        }
    return summary

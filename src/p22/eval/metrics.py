"""Classification metrics that refuse to hide their own failures.

Every metric returns a :class:`MetricValue`. When an assumption does not hold, the
value is ``None`` and ``not_applicable`` says why. A silent NaN would travel into
a report and look like a measurement.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    roc_auc_score,
)

PROBABILITY_TOLERANCE = 1e-3


@dataclass(frozen=True)
class MetricValue:
    """One metric outcome.

    Attributes:
        name: metric name.
        value: the estimate, or ``None`` when the metric does not apply.
        not_applicable: reason the metric does not apply, or ``None``.
        detail: supporting counts used to compute the value.
    """

    name: str
    value: float | None
    not_applicable: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def applicable(self) -> bool:
        return self.value is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "not_applicable": self.not_applicable,
            "detail": self.detail,
        }


def _as_labels(values: Sequence[Any] | np.ndarray, name: str) -> np.ndarray:
    array = np.asarray(values)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional, got shape {array.shape}")
    if array.size == 0:
        raise ValueError(f"{name} is empty")
    return array


def _check_pair(y_true: np.ndarray, y_pred: np.ndarray) -> None:
    if y_true.shape != y_pred.shape:
        raise ValueError(f"y_true has shape {y_true.shape}, y_pred has shape {y_pred.shape}")


def _as_probabilities(y_prob: Sequence[Any] | np.ndarray) -> np.ndarray:
    array = np.asarray(y_prob, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError(f"y_prob must be two-dimensional, got shape {array.shape}")
    if not np.isfinite(array).all():
        raise ValueError("y_prob contains non-finite values")
    if (array < 0).any() or (array > 1).any():
        raise ValueError("y_prob values must lie in [0, 1]")
    sums = array.sum(axis=1)
    if np.abs(sums - 1.0).max() > PROBABILITY_TOLERANCE:
        raise ValueError("each y_prob row must sum to one")
    return array


def accuracy(y_true: Sequence[Any], y_pred: Sequence[Any]) -> MetricValue:
    """Fraction of cells predicted correctly."""
    true_labels = _as_labels(y_true, "y_true")
    pred_labels = _as_labels(y_pred, "y_pred")
    _check_pair(true_labels, pred_labels)
    return MetricValue(
        name="accuracy",
        value=float(accuracy_score(true_labels, pred_labels)),
        detail={"n_cells": int(true_labels.size)},
    )


def balanced_accuracy(y_true: Sequence[Any], y_pred: Sequence[Any]) -> MetricValue:
    """Mean per-class recall. Useful when class counts are uneven."""
    true_labels = _as_labels(y_true, "y_true")
    pred_labels = _as_labels(y_pred, "y_pred")
    _check_pair(true_labels, pred_labels)
    classes = np.unique(true_labels)
    if classes.size < 2:
        return MetricValue(
            name="balanced_accuracy",
            value=None,
            not_applicable=f"only {classes.size} class present in y_true",
            detail={"classes_present": classes.tolist()},
        )
    return MetricValue(
        name="balanced_accuracy",
        value=float(balanced_accuracy_score(true_labels, pred_labels)),
        detail={"n_classes_present": int(classes.size)},
    )


def macro_f1(y_true: Sequence[Any], y_pred: Sequence[Any]) -> MetricValue:
    """Unweighted mean F1 over classes present in either array."""
    return _f1(y_true, y_pred, average="macro", name="macro_f1")


def weighted_f1(y_true: Sequence[Any], y_pred: Sequence[Any]) -> MetricValue:
    """Support-weighted mean F1."""
    return _f1(y_true, y_pred, average="weighted", name="weighted_f1")


def _f1(y_true: Sequence[Any], y_pred: Sequence[Any], average: str, name: str) -> MetricValue:
    true_labels = _as_labels(y_true, "y_true")
    pred_labels = _as_labels(y_pred, "y_pred")
    _check_pair(true_labels, pred_labels)
    return MetricValue(
        name=name,
        value=float(f1_score(true_labels, pred_labels, average=average, zero_division=0)),
        detail={"average": average, "n_cells": int(true_labels.size)},
    )


def macro_ovr_auroc(
    y_true: Sequence[Any],
    y_prob: Sequence[Any] | np.ndarray,
    n_classes: int | None = None,
) -> MetricValue:
    """One-versus-rest macro AUROC, computed only when it is defined.

    Returns a ``not_applicable`` result when a class is absent from ``y_true`` or
    when the probability matrix does not match the class count, rather than
    returning NaN.
    """
    true_labels = _as_labels(y_true, "y_true")
    probabilities = _as_probabilities(y_prob)
    if probabilities.shape[0] != true_labels.size:
        raise ValueError(
            f"y_prob has {probabilities.shape[0]} rows but y_true has {true_labels.size}"
        )
    expected = int(n_classes) if n_classes is not None else int(probabilities.shape[1])
    present = np.unique(true_labels)
    detail = {
        "n_classes_expected": expected,
        "n_classes_present": int(present.size),
        "classes_present": present.tolist(),
    }
    if probabilities.shape[1] != expected:
        return MetricValue(
            name="macro_ovr_auroc",
            value=None,
            not_applicable=(
                f"probability matrix has {probabilities.shape[1]} columns, expected {expected}"
            ),
            detail=detail,
        )
    if present.size < expected:
        missing = sorted(set(range(expected)) - set(present.tolist()))
        return MetricValue(
            name="macro_ovr_auroc",
            value=None,
            not_applicable=(
                f"class(es) {missing} absent from y_true, so one-versus-rest is undefined"
            ),
            detail=detail,
        )
    if present.size < 2:
        return MetricValue(
            name="macro_ovr_auroc",
            value=None,
            not_applicable="fewer than two classes present in y_true",
            detail=detail,
        )
    try:
        value = float(
            roc_auc_score(
                true_labels,
                probabilities if expected > 2 else probabilities[:, 1],
                multi_class="ovr",
                average="macro",
                labels=list(range(expected)) if expected > 2 else None,
            )
        )
    except ValueError as error:
        return MetricValue(
            name="macro_ovr_auroc", value=None, not_applicable=str(error), detail=detail
        )
    return MetricValue(name="macro_ovr_auroc", value=value, detail=detail)


def multiclass_ece(
    y_true: Sequence[Any],
    y_prob: Sequence[Any] | np.ndarray,
    n_bins: int = 10,
) -> MetricValue:
    """Expected calibration error of the top-label prediction.

    Args:
        y_true: true labels.
        y_prob: per-class probabilities.
        n_bins: number of equal-width confidence bins.

    Returns:
        A :class:`MetricValue` whose detail lists per-bin counts, confidence, and
        accuracy.
    """
    true_labels = _as_labels(y_true, "y_true")
    probabilities = _as_probabilities(y_prob)
    if probabilities.shape[0] != true_labels.size:
        raise ValueError(
            f"y_prob has {probabilities.shape[0]} rows but y_true has {true_labels.size}"
        )
    if n_bins < 1:
        raise ValueError(f"n_bins must be >= 1, got {n_bins}")

    confidence = probabilities.max(axis=1)
    predicted = probabilities.argmax(axis=1)
    correct = (predicted == true_labels.astype(predicted.dtype)).astype(np.float64)

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_index = np.clip(np.digitize(confidence, edges[1:-1], right=True), 0, n_bins - 1)
    error = 0.0
    bins = []
    for index in range(n_bins):
        mask = bin_index == index
        count = int(mask.sum())
        if count == 0:
            continue
        bin_confidence = float(confidence[mask].mean())
        bin_accuracy = float(correct[mask].mean())
        error += (count / true_labels.size) * abs(bin_accuracy - bin_confidence)
        bins.append(
            {
                "bin": index,
                "cells": count,
                "confidence": round(bin_confidence, 6),
                "accuracy": round(bin_accuracy, 6),
            }
        )
    return MetricValue(
        name="multiclass_ece",
        value=float(error),
        detail={"n_bins": n_bins, "occupied_bins": len(bins), "bins": bins},
    )


def compute_metrics(
    y_true: Sequence[Any],
    y_pred: Sequence[Any],
    y_prob: Sequence[Any] | np.ndarray | None = None,
    n_classes: int | None = None,
) -> dict[str, MetricValue]:
    """Compute the standard metric set, marking anything undefined as not applicable."""
    results = {
        "accuracy": accuracy(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy(y_true, y_pred),
        "macro_f1": macro_f1(y_true, y_pred),
        "weighted_f1": weighted_f1(y_true, y_pred),
    }
    if y_prob is None:
        reason = "probabilities were not supplied"
        results["macro_ovr_auroc"] = MetricValue("macro_ovr_auroc", None, reason)
        results["multiclass_ece"] = MetricValue("multiclass_ece", None, reason)
    else:
        results["macro_ovr_auroc"] = macro_ovr_auroc(y_true, y_prob, n_classes=n_classes)
        results["multiclass_ece"] = multiclass_ece(y_true, y_prob)
    return results

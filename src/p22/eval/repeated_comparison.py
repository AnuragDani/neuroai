"""Repeated donor-split primary contrast for the paired RNA+ATAC study.

The pilot contrast in :func:`p22.eval.multiome_protocol.paired_comparison` scores one
outer fold (a handful of test donors), so its donor bootstrap is degenerate. The
frozen internal comparison instead repeats the donor-isolated split and, within each
repeat, tests every donor exactly once. This module aggregates those per-repeat
predictions into the same estimand: the cross-attention minus matched
token-concatenation donor-level balanced-accuracy difference.

Uncertainty resamples whole donors and recomputes the across-repeat mean, so the
interval reflects donor sampling rather than cells or initialization. Replicates that
land on a single-class donor draw are counted as failed, never silently redrawn.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd

from p22.eval.estimand import practical_margin
from p22.eval.metrics import balanced_accuracy

PRIMARY_MODEL = "cross_attention"
PRIMARY_REFERENCE = "token_concat"


def _aligned(table: pd.DataFrame, name: str) -> pd.DataFrame:
    if not {"donor_id", "label", "probability"}.issubset(table.columns):
        raise ValueError(f"{name} predictions require donor_id, label, probability")
    frame = table.copy()
    frame["donor_id"] = frame["donor_id"].astype(str)
    if frame["donor_id"].duplicated().any():
        raise ValueError(f"{name} has duplicate donor predictions")
    if not frame["label"].isin([0, 1]).all() or set(frame["label"]) != {0, 1}:
        raise ValueError(f"{name} requires both binary classes")
    probability = frame["probability"].to_numpy(dtype=float)
    if not np.isfinite(probability).all() or ((probability < 0) | (probability > 1)).any():
        raise ValueError(f"{name} probabilities must be finite and within [0, 1]")
    return frame.sort_values("donor_id").reset_index(drop=True)


def _prepare_repeats(
    repeats: Sequence[dict],
    model: str,
    reference: str,
) -> tuple[list[tuple[np.ndarray, np.ndarray]], np.ndarray, np.ndarray]:
    if not repeats:
        raise ValueError("at least one repeat is required")
    prepared: list[tuple[np.ndarray, np.ndarray]] = []
    donors: np.ndarray | None = None
    labels: np.ndarray | None = None
    for entry in repeats:
        if model not in entry or reference not in entry:
            raise ValueError(f"each repeat needs {model!r} and {reference!r} predictions")
        left = _aligned(entry[model], model)
        right = _aligned(entry[reference], reference)
        if not left["donor_id"].equals(right["donor_id"]):
            raise ValueError("models must have identical donor sets")
        if not np.array_equal(left["label"], right["label"]):
            raise ValueError("models have inconsistent donor labels")
        repeat_donors = left["donor_id"].to_numpy(dtype=object)
        repeat_labels = left["label"].to_numpy(dtype=int)
        if donors is None:
            donors, labels = repeat_donors, repeat_labels
        elif not (np.array_equal(repeat_donors, donors) and np.array_equal(repeat_labels, labels)):
            raise ValueError("donor sets must be identical across repeats")
        prepared.append(
            (
                (left["probability"].to_numpy(dtype=float) >= 0.5).astype(int),
                (right["probability"].to_numpy(dtype=float) >= 0.5).astype(int),
            )
        )
    assert donors is not None and labels is not None
    return prepared, donors, labels


def _delta_per_repeat(prepared, labels, index=None) -> float | None:
    truth = labels if index is None else labels[index]
    deltas = []
    for left, right in prepared:
        left_pred = left if index is None else left[index]
        right_pred = right if index is None else right[index]
        first = balanced_accuracy(truth, left_pred)
        second = balanced_accuracy(truth, right_pred)
        if not (first.applicable and second.applicable):
            return None
        deltas.append(first.value - second.value)
    return float(np.mean(deltas))


def repeated_primary_contrast(
    repeats: Sequence[dict],
    *,
    model: str = PRIMARY_MODEL,
    reference: str = PRIMARY_REFERENCE,
    n_replicates: int = 1000,
    level: float = 0.95,
    seed: int = 22,
) -> dict[str, Any]:
    """Cross-attention minus matched token-concat donor balanced accuracy, repeated.

    The estimate is the mean across repeats of each repeat's donor-level delta; every
    repeat must test the same donor set exactly once. A positive advantage requires
    ``estimate >= count-derived margin`` and a strictly positive lower interval bound.
    """
    if type(n_replicates) is not int or n_replicates < 1:
        raise ValueError("n_replicates must be a positive integer")
    if not 0.0 < level < 1.0:
        raise ValueError("level must be in (0, 1)")
    prepared, donors, labels = _prepare_repeats(repeats, model, reference)
    n_donors = int(donors.size)

    per_repeat = {}
    for entry, (left, right) in zip(repeats, prepared, strict=True):
        first = balanced_accuracy(labels, left)
        second = balanced_accuracy(labels, right)
        per_repeat[int(entry["repeat"])] = float(first.value - second.value)
    deltas = np.asarray([per_repeat[key] for key in sorted(per_repeat)], dtype=float)
    estimate = float(deltas.mean())

    n_control = int((labels == 0).sum())
    n_positive = int((labels == 1).sum())
    margin = practical_margin(n_control, n_positive)
    common = {
        "metric": "repeated_paired_donor_balanced_accuracy_delta",
        "model": model,
        "reference": reference,
        "unit": "donor",
        "level": level,
        "n_repeats": len(per_repeat),
        "n_replicates_requested": n_replicates,
        "n_donors": n_donors,
        "n_control": n_control,
        "n_positive": n_positive,
        "practical_margin": margin,
        "per_repeat_delta": per_repeat,
        "seed": seed,
    }
    if n_donors < 2:
        return {
            **common,
            "estimate": estimate,
            "interval": [None, None],
            "n_valid": 0,
            "n_failed": 0,
            "failure_reasons": [],
            "advantage_demonstrated": False,
            "not_applicable": f"donor bootstrap needs at least two donors, got {n_donors}",
        }

    rng = np.random.default_rng(seed)
    values: list[float] = []
    reasons: list[str] = []
    for _ in range(n_replicates):
        index = rng.choice(n_donors, size=n_donors, replace=True)
        value = _delta_per_repeat(prepared, labels, index)
        if value is None:
            reasons.append("single-class donor resample")
        else:
            values.append(value)

    if not values:
        lower = upper = None
        not_applicable = "every replicate failed, so no interval exists"
    else:
        tail = (1.0 - level) / 2.0
        bounds = np.percentile(values, [100 * tail, 100 * (1 - tail)])
        lower, upper = (float(bound) for bound in bounds)
        not_applicable = None
    return {
        **common,
        "estimate": estimate,
        "interval": [lower, upper],
        "n_valid": len(values),
        "n_failed": len(reasons),
        "failure_reasons": sorted(set(reasons)),
        "advantage_demonstrated": bool(estimate >= margin and lower is not None and lower > 0),
        "not_applicable": not_applicable,
    }


def repeated_model_accuracy(
    repeats: Sequence[dict],
    model: str,
) -> dict[str, Any]:
    """Donor balanced accuracy for one family across repeats (descriptive)."""
    if not repeats:
        raise ValueError("at least one repeat is required")
    scores: dict[int, float | None] = {}
    for entry in repeats:
        if model not in entry:
            raise ValueError(f"repeat is missing {model!r} predictions")
        frame = _aligned(entry[model], model)
        metric = balanced_accuracy(frame["label"], (frame["probability"] >= 0.5).astype(int))
        scores[int(entry["repeat"])] = metric.value if metric.applicable else None
    usable = [value for value in scores.values() if value is not None]
    return {
        "model": model,
        "per_repeat": scores,
        "mean": float(np.mean(usable)) if usable else None,
        "n_usable": len(usable),
    }

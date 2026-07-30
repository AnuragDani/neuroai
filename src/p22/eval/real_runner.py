"""Donor-held-out evaluation of real-data baselines and models.

Every model here is scored the same way: repeated ``StratifiedGroupKFold`` over
donors, one out-of-fold prediction per donor per repeat, donor probabilities
averaged across repeats, then thresholded at 0.5. Feature selection and scaling
are fitted on training donors only, inside each fold.

Nothing in this module chooses a model. It reports what each model scored,
including when a cheap baseline wins.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from p22.data.group_splits import GroupFold
from p22.eval.metrics import balanced_accuracy, macro_f1
from p22.eval.statistics import donor_bootstrap

DONOR_THRESHOLD = 0.5
FULL_COHORT_LAYER = "full_cohort_all_retained_cells"
CAPPED_LAYER = "cell_level_capped"


@dataclass(frozen=True)
class ModelRun:
    """One model scored under the frozen donor-resampling protocol."""

    name: str
    layer: str
    status: str
    donor_ids: tuple[str, ...] = ()
    labels: np.ndarray | None = None
    donor_probability: np.ndarray | None = None
    donor_prediction: np.ndarray | None = None
    per_repeat_balanced_accuracy: tuple[float, ...] = ()
    balanced_accuracy: float | None = None
    macro_f1: float | None = None
    auroc: float | None = None
    auroc_not_applicable: str | None = None
    bootstrap: dict[str, Any] = field(default_factory=dict)
    n_donors: int | None = None
    n_cells: int | None = None
    donor_overlap_per_fold: tuple[int, ...] = ()
    detail: dict[str, Any] = field(default_factory=dict)
    not_applicable: str | None = None

    def to_row(self) -> dict[str, Any]:
        repeats = np.asarray(self.per_repeat_balanced_accuracy, dtype=float)
        return {
            "model": self.name,
            "layer": self.layer,
            "status": self.status,
            "donor_balanced_accuracy": self.balanced_accuracy,
            "donor_macro_f1": self.macro_f1,
            "donor_auroc": self.auroc,
            "auroc_not_applicable": self.auroc_not_applicable,
            "bootstrap_lower": self.bootstrap.get("lower"),
            "bootstrap_upper": self.bootstrap.get("upper"),
            "split_repeats_mean": float(repeats.mean()) if repeats.size else None,
            "split_repeats_std": float(repeats.std(ddof=1)) if repeats.size > 1 else None,
            "split_repeats_min": float(repeats.min()) if repeats.size else None,
            "split_repeats_max": float(repeats.max()) if repeats.size else None,
            "n_donors": self.n_donors,
            "n_cells": self.n_cells,
            "max_donor_overlap_per_fold": (
                max(self.donor_overlap_per_fold) if self.donor_overlap_per_fold else None
            ),
            "not_applicable": self.not_applicable,
            "detail": self.detail,
        }


def not_applicable_run(name: str, reason: str, layer: str = CAPPED_LAYER) -> ModelRun:
    return ModelRun(name=name, layer=layer, status="NOT_APPLICABLE", not_applicable=reason)


def _auroc(labels: np.ndarray, probability: np.ndarray) -> tuple[float | None, str | None]:
    from sklearn.metrics import roc_auc_score

    if np.unique(labels).size < 2:
        return None, "only one donor class present"
    return float(roc_auc_score(labels, probability)), None


def _summarize(
    name: str,
    layer: str,
    donor_ids: Sequence[str],
    labels: np.ndarray,
    probability_by_repeat: np.ndarray,
    n_cells: int | None,
    overlap: Sequence[int],
    detail: dict[str, Any],
) -> ModelRun:
    """Turn per-repeat out-of-fold donor probabilities into one scored run."""
    per_repeat: list[float] = []
    for column in range(probability_by_repeat.shape[1]):
        prediction = (probability_by_repeat[:, column] >= DONOR_THRESHOLD).astype(int)
        value = balanced_accuracy(labels, prediction)
        if value.applicable:
            per_repeat.append(float(value.value))
    mean_probability = probability_by_repeat.mean(axis=1)
    prediction = (mean_probability >= DONOR_THRESHOLD).astype(int)
    accuracy = balanced_accuracy(labels, prediction)
    f1 = macro_f1(labels, prediction)
    auroc, auroc_reason = _auroc(labels, mean_probability)
    bootstrap = donor_bootstrap(
        balanced_accuracy,
        labels,
        prediction,
        list(donor_ids),
        n_replicates=2000,
        seed=0,
    )
    return ModelRun(
        name=name,
        layer=layer,
        status="measured",
        donor_ids=tuple(str(value) for value in donor_ids),
        labels=labels,
        donor_probability=mean_probability,
        donor_prediction=prediction,
        per_repeat_balanced_accuracy=tuple(per_repeat),
        balanced_accuracy=accuracy.value,
        macro_f1=f1.value,
        auroc=auroc,
        auroc_not_applicable=auroc_reason,
        bootstrap=bootstrap.to_dict() | {"lower": bootstrap.lower, "upper": bootstrap.upper},
        n_donors=int(len(donor_ids)),
        n_cells=n_cells,
        donor_overlap_per_fold=tuple(int(value) for value in overlap),
        detail=detail,
    )


def _fold_groups(folds: Sequence[GroupFold]) -> dict[int, list[GroupFold]]:
    grouped: dict[int, list[GroupFold]] = {}
    for fold in folds:
        grouped.setdefault(fold.repeat, []).append(fold)
    return grouped


def run_donor_level_model(
    name: str,
    features: np.ndarray,
    labels: np.ndarray,
    donor_ids: Sequence[str],
    folds: Sequence[GroupFold],
    *,
    layer: str = FULL_COHORT_LAYER,
    n_features: int | None = None,
    detail: dict[str, Any] | None = None,
) -> ModelRun:
    """Score a donor-by-feature matrix with train-only selection and scaling."""
    matrix = np.asarray(features, dtype=np.float64)
    if matrix.ndim == 1:
        matrix = matrix[:, None]
    donors = np.asarray([str(value) for value in donor_ids], dtype=object)
    position = {donor: index for index, donor in enumerate(donors)}
    grouped = _fold_groups(folds)
    probability = np.full((donors.size, len(grouped)), np.nan)
    overlap: list[int] = []

    for column, repeat in enumerate(sorted(grouped)):
        for fold in grouped[repeat]:
            train = [position[donor] for donor in fold.train_donors if donor in position]
            test = [position[donor] for donor in fold.test_donors if donor in position]
            overlap.append(len(set(fold.train_donors) & set(fold.test_donors)))
            if not train or not test:
                continue
            selected = np.arange(matrix.shape[1])
            if n_features is not None and n_features < matrix.shape[1]:
                variance = matrix[train].var(axis=0)
                selected = np.argsort(variance)[::-1][:n_features]
            scaler = StandardScaler()
            x_train = scaler.fit_transform(matrix[np.ix_(train, selected)])
            x_test = scaler.transform(matrix[np.ix_(test, selected)])
            model = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=0)
            model.fit(x_train, labels[train])
            probability[test, column] = model.predict_proba(x_test)[:, 1]

    if np.isnan(probability).any():
        probability = np.where(np.isnan(probability), 0.5, probability)
    return _summarize(
        name,
        layer,
        donors.tolist(),
        np.asarray(labels, dtype=int),
        probability,
        None,
        overlap,
        (detail or {}) | {"n_input_features": int(matrix.shape[1]), "selected": n_features},
    )


def run_majority_baseline(
    labels: np.ndarray,
    donor_ids: Sequence[str],
    folds: Sequence[GroupFold],
) -> ModelRun:
    """Predict the training-fold majority donor class for every held-out donor."""
    donors = np.asarray([str(value) for value in donor_ids], dtype=object)
    position = {donor: index for index, donor in enumerate(donors)}
    grouped = _fold_groups(folds)
    probability = np.full((donors.size, len(grouped)), 0.5)
    overlap: list[int] = []
    for column, repeat in enumerate(sorted(grouped)):
        for fold in grouped[repeat]:
            train = [position[donor] for donor in fold.train_donors if donor in position]
            test = [position[donor] for donor in fold.test_donors if donor in position]
            overlap.append(len(set(fold.train_donors) & set(fold.test_donors)))
            if not train or not test:
                continue
            majority = int(np.bincount(labels[train], minlength=2).argmax())
            probability[test, column] = 1.0 if majority == 1 else 0.0
    return _summarize(
        "majority_class",
        "donor_level",
        donors.tolist(),
        np.asarray(labels, dtype=int),
        probability,
        None,
        overlap,
        {"rule": "training-fold majority donor class"},
    )


def run_cell_level_model(
    name: str,
    cell_matrix: Any,
    cell_labels: np.ndarray,
    cell_donors: Sequence[str],
    folds: Sequence[GroupFold],
    *,
    n_features: int = 2000,
    layer: str = CAPPED_LAYER,
    detail: dict[str, Any] | None = None,
) -> ModelRun:
    """Fit a cell-level classifier per fold and aggregate to donor probabilities.

    ``cell_matrix`` may be sparse. Only the training cells of a fold are used to
    pick features and fit the scaler, so held-out donors never enter preprocessing.
    """
    donors_per_cell = np.asarray([str(value) for value in cell_donors], dtype=object)
    y_cells = np.asarray(cell_labels, dtype=int)
    donor_frame = (
        pd.DataFrame({"donor_id": donors_per_cell, "label": y_cells})
        .groupby("donor_id", sort=True)["label"]
        .agg(lambda values: int(values.mode().iloc[0]))
    )
    donors = donor_frame.index.to_numpy(dtype=object)
    labels = donor_frame.to_numpy(dtype=int)
    position = {donor: index for index, donor in enumerate(donors)}
    grouped = _fold_groups(folds)
    probability = np.full((donors.size, len(grouped)), np.nan)
    overlap: list[int] = []

    is_sparse = hasattr(cell_matrix, "tocsr")
    for column, repeat in enumerate(sorted(grouped)):
        for fold in grouped[repeat]:
            train_cells = np.flatnonzero(np.isin(donors_per_cell, np.array(fold.train_donors)))
            test_cells = np.flatnonzero(np.isin(donors_per_cell, np.array(fold.test_donors)))
            overlap.append(len(set(fold.train_donors) & set(fold.test_donors)))
            if train_cells.size == 0 or test_cells.size == 0:
                continue
            train_block = cell_matrix[train_cells]
            if is_sparse:
                mean = np.asarray(train_block.mean(axis=0)).ravel()
                mean_square = np.asarray(train_block.multiply(train_block).mean(axis=0)).ravel()
                variance = np.maximum(mean_square - mean**2, 0.0)
            else:
                variance = np.asarray(train_block).var(axis=0)
            selected = np.argsort(variance)[::-1][: min(n_features, variance.size)]
            x_train = train_block[:, selected]
            x_test = cell_matrix[test_cells][:, selected]
            if is_sparse:
                x_train = np.asarray(x_train.todense())
                x_test = np.asarray(x_test.todense())
            scaler = StandardScaler()
            x_train = scaler.fit_transform(x_train)
            x_test = scaler.transform(x_test)
            model = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=0)
            model.fit(x_train, y_cells[train_cells])
            cell_probability = model.predict_proba(x_test)[:, 1]
            aggregated = (
                pd.DataFrame({"donor_id": donors_per_cell[test_cells], "p": cell_probability})
                .groupby("donor_id", sort=True)["p"]
                .mean()
            )
            for donor, value in aggregated.items():
                if donor in position:
                    probability[position[donor], column] = float(value)

    if np.isnan(probability).any():
        probability = np.where(np.isnan(probability), 0.5, probability)
    return _summarize(
        name,
        layer,
        donors.tolist(),
        labels,
        probability,
        int(y_cells.size),
        overlap,
        (detail or {}) | {"n_features_selected_per_fold": int(n_features)},
    )


@dataclass(frozen=True)
class PairedDelta:
    """Donor-level paired difference between two scored models."""

    model: str
    reference: str
    delta: float | None
    lower: float | None
    upper: float | None
    n_donors: int
    margin: float
    meets_margin: bool
    interval_excludes_zero: bool
    verdict: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "reference": self.reference,
            "donor_balanced_accuracy_delta": self.delta,
            "bootstrap_lower": self.lower,
            "bootstrap_upper": self.upper,
            "n_donors": self.n_donors,
            "practical_margin": self.margin,
            "meets_margin": self.meets_margin,
            "interval_excludes_zero": self.interval_excludes_zero,
            "verdict": self.verdict,
        }


def paired_donor_delta(
    model: ModelRun,
    reference: ModelRun,
    margin: float,
    n_replicates: int = 2000,
    seed: int = 0,
) -> PairedDelta:
    """Bootstrap the donor-level balanced-accuracy difference between two models."""
    if model.donor_prediction is None or reference.donor_prediction is None:
        return PairedDelta(
            model=model.name,
            reference=reference.name,
            delta=None,
            lower=None,
            upper=None,
            n_donors=0,
            margin=margin,
            meets_margin=False,
            interval_excludes_zero=False,
            verdict="not_applicable",
        )
    shared = [donor for donor in model.donor_ids if donor in set(reference.donor_ids)]
    model_index = {donor: index for index, donor in enumerate(model.donor_ids)}
    reference_index = {donor: index for index, donor in enumerate(reference.donor_ids)}
    labels = np.asarray([model.labels[model_index[donor]] for donor in shared], dtype=int)
    left = np.asarray([model.donor_prediction[model_index[donor]] for donor in shared], dtype=int)
    right = np.asarray(
        [reference.donor_prediction[reference_index[donor]] for donor in shared], dtype=int
    )

    def statistic(indices: np.ndarray) -> float | None:
        subset = labels[indices]
        if np.unique(subset).size < 2:
            return None
        first = balanced_accuracy(subset, left[indices])
        second = balanced_accuracy(subset, right[indices])
        if not (first.applicable and second.applicable):
            return None
        return float(first.value - second.value)

    point = statistic(np.arange(labels.size))
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(n_replicates):
        drawn = rng.integers(0, labels.size, size=labels.size)
        value = statistic(drawn)
        if value is not None:
            values.append(value)
    lower = upper = None
    if values:
        lower, upper = (float(value) for value in np.percentile(values, [2.5, 97.5]))
    excludes_zero = bool(lower is not None and lower > 0.0)
    meets = bool(point is not None and point >= margin)
    if point is None:
        verdict = "not_applicable"
    elif meets and excludes_zero:
        verdict = "success"
    else:
        verdict = "inconclusive"
    return PairedDelta(
        model=model.name,
        reference=reference.name,
        delta=point,
        lower=lower,
        upper=upper,
        n_donors=int(labels.size),
        margin=margin,
        meets_margin=meets,
        interval_excludes_zero=excludes_zero,
        verdict=verdict,
    )

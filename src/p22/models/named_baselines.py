"""Named predictive baselines for G6 comparison.

Cheap controls run before gated fusion. These helpers operate on donor- or
cell-level arrays already held in memory; they do not download disease matrices.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.preprocessing import StandardScaler

from p22.eval.estimand import NAMED_BASELINES

BASELINE_ORDER = NAMED_BASELINES


@dataclass(frozen=True)
class BaselineResult:
    """One baseline outcome under donor-held-out evaluation."""

    name: str
    status: str
    donor_balanced_accuracy: float | None = None
    n_donors: int | None = None
    n_cells: int | None = None
    not_applicable: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "donor_balanced_accuracy": self.donor_balanced_accuracy,
            "n_donors": self.n_donors,
            "n_cells": self.n_cells,
            "not_applicable": self.not_applicable,
            "detail": dict(self.detail),
        }


def _donor_truth(
    labels: np.ndarray,
    donor_ids: np.ndarray,
) -> pd.Series:
    frame = pd.DataFrame({"donor_id": donor_ids.astype(str), "label": labels})
    return frame.groupby("donor_id")["label"].agg(lambda values: int(values.mode().iloc[0]))


def majority_class_baseline(
    labels: Sequence[Any] | np.ndarray,
    donor_ids: Sequence[Any] | np.ndarray,
) -> BaselineResult:
    """Predict the majority donor class for every donor."""
    y = np.asarray(labels)
    donors = np.asarray([str(value) for value in np.asarray(donor_ids)], dtype=object)
    truth = _donor_truth(y, donors)
    majority = int(truth.value_counts().index[0])
    pred = np.full(truth.shape[0], majority, dtype=int)
    score = float(balanced_accuracy_score(truth.to_numpy(), pred))
    return BaselineResult(
        name="majority_class",
        status="measured",
        donor_balanced_accuracy=score,
        n_donors=int(truth.shape[0]),
        n_cells=int(y.size),
        detail={"majority_class": majority},
    )


def chr21_dosage_baseline(
    expression: np.ndarray | None,
    labels: Sequence[Any] | np.ndarray,
    donor_ids: Sequence[Any] | np.ndarray,
    train_donors: Sequence[str],
    test_donors: Sequence[str],
) -> BaselineResult:
    """Donor-mean chr21 expression logistic classifier."""
    if expression is None:
        return BaselineResult(
            name="chr21_dosage",
            status="unknown",
            not_applicable="chr21 gene annotation or expression block unavailable",
        )
    y = np.asarray(labels)
    donors = np.asarray([str(value) for value in np.asarray(donor_ids)], dtype=object)
    dosage = np.asarray(expression, dtype=np.float64)
    if dosage.ndim != 1 or dosage.size != y.size:
        raise ValueError("expression must be one score per cell")
    frame = pd.DataFrame({"donor_id": donors, "label": y, "dosage": dosage})
    donor_frame = frame.groupby("donor_id", sort=True).agg(
        label=("label", lambda values: int(values.mode().iloc[0])),
        dosage=("dosage", "mean"),
    )
    train_mask = donor_frame.index.isin(set(train_donors))
    test_mask = donor_frame.index.isin(set(test_donors))
    if train_mask.sum() < 2 or test_mask.sum() < 1:
        return BaselineResult(
            name="chr21_dosage",
            status="blocked",
            not_applicable="insufficient train/test donors for chr21 logistic",
        )
    model = LogisticRegression(max_iter=500, class_weight="balanced", random_state=0)
    x_train = donor_frame.loc[train_mask, ["dosage"]].to_numpy()
    y_train = donor_frame.loc[train_mask, "label"].to_numpy()
    x_test = donor_frame.loc[test_mask, ["dosage"]].to_numpy()
    y_test = donor_frame.loc[test_mask, "label"].to_numpy()
    model.fit(x_train, y_train)
    pred = model.predict(x_test)
    score = float(balanced_accuracy_score(y_test, pred))
    return BaselineResult(
        name="chr21_dosage",
        status="measured",
        donor_balanced_accuracy=score,
        n_donors=int(test_mask.sum()),
        n_cells=int(np.isin(donors, list(test_donors)).sum()),
    )


def covariate_logistic_baseline(
    covariates: pd.DataFrame | None,
    labels: Sequence[Any] | np.ndarray,
    donor_ids: Sequence[Any] | np.ndarray,
    train_donors: Sequence[str],
    test_donors: Sequence[str],
) -> BaselineResult:
    """QC/covariate-only logistic using only predeclared available fields."""
    if covariates is None or covariates.empty:
        return BaselineResult(
            name="qc_covariate_logistic",
            status="unknown",
            not_applicable="no predeclared covariates available",
        )
    y = np.asarray(labels)
    donors = np.asarray([str(value) for value in np.asarray(donor_ids)], dtype=object)
    frame = covariates.copy()
    frame["donor_id"] = donors
    frame["label"] = y
    numeric = frame.select_dtypes(include=[np.number]).drop(columns=["label"], errors="ignore")
    if numeric.empty:
        return BaselineResult(
            name="qc_covariate_logistic",
            status="unknown",
            not_applicable="covariate table has no numeric fields",
        )
    donor_x = numeric.groupby(frame["donor_id"]).mean()
    donor_y = frame.groupby("donor_id")["label"].agg(lambda values: int(values.mode().iloc[0]))
    train_mask = donor_x.index.isin(set(train_donors))
    test_mask = donor_x.index.isin(set(test_donors))
    scaler = StandardScaler()
    x_train = scaler.fit_transform(donor_x.loc[train_mask].to_numpy())
    x_test = scaler.transform(donor_x.loc[test_mask].to_numpy())
    model = LogisticRegression(max_iter=500, class_weight="balanced", random_state=0)
    model.fit(x_train, donor_y.loc[train_mask].to_numpy())
    pred = model.predict(x_test)
    score = float(balanced_accuracy_score(donor_y.loc[test_mask].to_numpy(), pred))
    return BaselineResult(
        name="qc_covariate_logistic",
        status="measured",
        donor_balanced_accuracy=score,
        n_donors=int(test_mask.sum()),
        n_cells=int(np.isin(donors, list(test_donors)).sum()),
        detail={"covariates": list(numeric.columns)},
    )


def pseudobulk_rna_logistic(
    rna: np.ndarray,
    labels: Sequence[Any] | np.ndarray,
    donor_ids: Sequence[Any] | np.ndarray,
    train_donors: Sequence[str],
    test_donors: Sequence[str],
    n_features: int = 32,
) -> BaselineResult:
    """Pseudobulk-per-donor RNA logistic with train-only feature selection."""
    matrix = np.asarray(rna, dtype=np.float64)
    y = np.asarray(labels)
    donors = np.asarray([str(value) for value in np.asarray(donor_ids)], dtype=object)
    train_cell = np.isin(donors, list(train_donors))
    variance = matrix[train_cell].var(axis=0)
    selected = np.argsort(variance)[::-1][: min(n_features, matrix.shape[1])]
    reduced = matrix[:, selected]
    frame = pd.DataFrame(reduced)
    frame["donor_id"] = donors
    frame["label"] = y
    feature_cols = [column for column in frame.columns if column not in {"donor_id", "label"}]
    donor_x = frame.groupby("donor_id")[feature_cols].mean()
    donor_y = frame.groupby("donor_id")["label"].agg(lambda values: int(values.mode().iloc[0]))
    train_mask = donor_x.index.isin(set(train_donors))
    test_mask = donor_x.index.isin(set(test_donors))
    scaler = StandardScaler()
    x_train = scaler.fit_transform(donor_x.loc[train_mask].to_numpy())
    x_test = scaler.transform(donor_x.loc[test_mask].to_numpy())
    model = LogisticRegression(max_iter=500, class_weight="balanced", random_state=0)
    model.fit(x_train, donor_y.loc[train_mask].to_numpy())
    pred = model.predict(x_test)
    score = float(balanced_accuracy_score(donor_y.loc[test_mask].to_numpy(), pred))
    return BaselineResult(
        name="pseudobulk_rna_logistic",
        status="measured",
        donor_balanced_accuracy=score,
        n_donors=int(test_mask.sum()),
        n_cells=int(np.isin(donors, list(test_donors)).sum()),
        detail={"n_features": int(selected.size)},
    )


def not_applicable_baseline(name: str, reason: str) -> BaselineResult:
    return BaselineResult(name=name, status="not_applicable", not_applicable=reason)


def blocked_baseline(name: str, reason: str) -> BaselineResult:
    return BaselineResult(name=name, status="blocked", not_applicable=reason)


def baseline_table(results: Sequence[BaselineResult]) -> list[dict[str, Any]]:
    """Order baseline rows by the frozen G6 list."""
    by_name = {result.name: result for result in results}
    rows = []
    for name in BASELINE_ORDER:
        if name not in by_name:
            rows.append(
                BaselineResult(
                    name=name,
                    status="missing",
                    not_applicable="baseline not evaluated",
                ).to_dict()
            )
        else:
            rows.append(by_name[name].to_dict())
    return rows

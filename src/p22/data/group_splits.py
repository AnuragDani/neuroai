"""Repeated donor-held-out StratifiedGroupKFold evaluation (G5)."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from p22.data.splits import _as_donor_array


@dataclass(frozen=True)
class GroupFold:
    """One train/test donor partition."""

    repeat: int
    fold: int
    split_seed: int
    train_donors: tuple[str, ...]
    test_donors: tuple[str, ...]
    train_index: np.ndarray
    test_index: np.ndarray

    def to_dict(self) -> dict[str, Any]:
        return {
            "repeat": self.repeat,
            "fold": self.fold,
            "split_seed": self.split_seed,
            "train_donors": list(self.train_donors),
            "test_donors": list(self.test_donors),
            "n_train_cells": int(self.train_index.size),
            "n_test_cells": int(self.test_index.size),
        }


@dataclass(frozen=True)
class RepeatedGroupSplitReport:
    """Leakage-control evidence for repeated group folds."""

    status: str
    n_repeats: int
    n_folds: int
    folds: list[GroupFold] = field(default_factory=list)
    donor_overlap_count: int = 0
    blocking_problems: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "n_repeats": self.n_repeats,
            "n_folds": self.n_folds,
            "n_folds_total": len(self.folds),
            "donor_overlap_count": self.donor_overlap_count,
            "folds": [fold.to_dict() for fold in self.folds],
            "blocking_problems": list(self.blocking_problems),
            "open_questions": list(self.open_questions),
        }


def _donor_labels_for_stratification(
    donor_ids: np.ndarray,
    labels: np.ndarray,
    *,
    allow_majority: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Return unique donors and one label per donor.

    Raises:
        ValueError: if a donor has mixed labels and ``allow_majority`` is False.
    """
    frame = pd.DataFrame({"donor": donor_ids.astype(str), "label": labels})
    purity = frame.groupby("donor")["label"].nunique()
    impure = purity[purity > 1]
    if len(impure) and not allow_majority:
        raise ValueError(f"donors with mixed labels: {sorted(impure.index)[:5]}")
    donor_label = (
        frame.groupby("donor")["label"]
        .agg(lambda values: int(values.mode().iloc[0]))
        .reset_index()
        .sort_values("donor")
    )
    return donor_label["donor"].to_numpy(dtype=object), donor_label["label"].to_numpy()


def iter_repeated_stratified_group_folds(
    donor_ids: Sequence[Any] | np.ndarray,
    labels: Sequence[Any] | np.ndarray,
    n_repeats: int = 5,
    n_folds: int = 5,
    base_seed: int = 0,
) -> Iterator[GroupFold]:
    """Yield donor-held-out folds; split seed controls donor assignment."""
    donors_per_cell = _as_donor_array(donor_ids)
    label_array = np.asarray(labels)
    if label_array.shape[0] != donors_per_cell.shape[0]:
        raise ValueError("labels length must match donor_ids")
    unique_donors, donor_y = _donor_labels_for_stratification(donors_per_cell, label_array)
    as_str = np.asarray([str(value) for value in donors_per_cell], dtype=object)

    for repeat in range(n_repeats):
        split_seed = int(base_seed + repeat)
        splitter = StratifiedGroupKFold(n_splits=n_folds, shuffle=True, random_state=split_seed)
        # StratifiedGroupKFold expects groups aligned to X rows; use one row per donor.
        dummy_x = np.zeros((unique_donors.size, 1))
        groups = unique_donors
        for fold_index, (train_donor_idx, test_donor_idx) in enumerate(
            splitter.split(dummy_x, donor_y, groups=groups)
        ):
            train_donors = tuple(sorted(str(value) for value in unique_donors[train_donor_idx]))
            test_donors = tuple(sorted(str(value) for value in unique_donors[test_donor_idx]))
            train_index = np.flatnonzero(np.isin(as_str, np.array(train_donors, dtype=object)))
            test_index = np.flatnonzero(np.isin(as_str, np.array(test_donors, dtype=object)))
            yield GroupFold(
                repeat=repeat,
                fold=fold_index,
                split_seed=split_seed,
                train_donors=train_donors,
                test_donors=test_donors,
                train_index=train_index,
                test_index=test_index,
            )


def validate_group_folds(folds: Sequence[GroupFold]) -> list[str]:
    """Return leakage problems across generated folds."""
    problems: list[str] = []
    for fold in folds:
        overlap = sorted(set(fold.train_donors) & set(fold.test_donors))
        if overlap:
            problems.append(f"repeat {fold.repeat} fold {fold.fold} donor overlap: {overlap[:5]}")
        if fold.train_index.size == 0 or fold.test_index.size == 0:
            problems.append(f"repeat {fold.repeat} fold {fold.fold} has an empty split")
        shared_cells = np.intersect1d(fold.train_index, fold.test_index)
        if shared_cells.size:
            problems.append(
                f"repeat {fold.repeat} fold {fold.fold} shares {shared_cells.size} cells"
            )
    return problems


def build_repeated_group_split_report(
    donor_ids: Sequence[Any] | np.ndarray,
    labels: Sequence[Any] | np.ndarray,
    n_repeats: int = 5,
    n_folds: int = 5,
    base_seed: int = 0,
) -> RepeatedGroupSplitReport:
    """Materialize and validate the G5 split plan."""
    folds = list(
        iter_repeated_stratified_group_folds(
            donor_ids,
            labels,
            n_repeats=n_repeats,
            n_folds=n_folds,
            base_seed=base_seed,
        )
    )
    problems = validate_group_folds(folds)
    overlap_count = sum(1 for fold in folds if set(fold.train_donors) & set(fold.test_donors))
    status = "BLOCKED" if problems else "PASS"
    return RepeatedGroupSplitReport(
        status=status,
        n_repeats=n_repeats,
        n_folds=n_folds,
        folds=folds,
        donor_overlap_count=overlap_count,
        blocking_problems=tuple(problems),
    )


def aggregate_donor_probabilities(
    probabilities: np.ndarray,
    donor_ids: Sequence[Any] | np.ndarray,
    threshold: float = 0.5,
) -> pd.DataFrame:
    """Mean probability per donor, then threshold at 0.5."""
    probs = np.asarray(probabilities, dtype=np.float64)
    donors = np.asarray([str(value) for value in np.asarray(donor_ids)], dtype=object)
    if probs.ndim != 1:
        raise ValueError("probabilities must be one-dimensional positive-class scores")
    if probs.size != donors.size:
        raise ValueError("probabilities and donor_ids length mismatch")
    frame = pd.DataFrame({"donor_id": donors, "probability": probs})
    grouped = frame.groupby("donor_id", sort=True)["probability"].mean().reset_index()
    grouped["prediction"] = (grouped["probability"] >= threshold).astype(int)
    return grouped

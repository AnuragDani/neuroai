"""Donor-held-out splitting.

Donors are split, never cells. A cell-level split lets the same donor appear in
train and test, which inflates every downstream number. The functions here refuse
to produce or accept a split that breaks that rule.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

SPLIT_NAMES = ("train", "val", "test")
FRACTION_TOLERANCE = 1e-6


@dataclass(frozen=True)
class DonorSplit:
    """A donor-held-out assignment of cells to train, validation, and test.

    Attributes:
        train_donors: donors used for fitting.
        val_donors: donors used for model selection.
        test_donors: donors used once, for the final estimate.
        train_index: positions of training cells in the input arrays.
        val_index: positions of validation cells.
        test_index: positions of test cells.
        summary: donor and cell counts, requested and realized fractions, and
            observed label distribution per split when labels were supplied.
    """

    train_donors: tuple[str, ...]
    val_donors: tuple[str, ...]
    test_donors: tuple[str, ...]
    train_index: np.ndarray
    val_index: np.ndarray
    test_index: np.ndarray
    summary: dict[str, Any]

    def donors(self, split: str) -> tuple[str, ...]:
        return {
            "train": self.train_donors,
            "val": self.val_donors,
            "test": self.test_donors,
        }[split]

    def index(self, split: str) -> np.ndarray:
        return {
            "train": self.train_index,
            "val": self.val_index,
            "test": self.test_index,
        }[split]

    @property
    def n_cells(self) -> int:
        return int(self.train_index.size + self.val_index.size + self.test_index.size)

    def as_frame(self) -> pd.DataFrame:
        """Return one row per split with donor and cell counts."""
        rows = []
        for name in SPLIT_NAMES:
            rows.append(
                {
                    "split": name,
                    "donors": len(self.donors(name)),
                    "cells": int(self.index(name).size),
                    "cell_fraction": round(float(self.index(name).size) / self.n_cells, 4),
                }
            )
        return pd.DataFrame(rows)


def _as_donor_array(donor_ids: Sequence[Any] | np.ndarray | pd.Series) -> np.ndarray:
    """Return donor identifiers as an object array, rejecting null or empty values.

    Raises:
        ValueError: if the input is empty or contains a null or blank identifier.
    """
    if isinstance(donor_ids, pd.Series):
        values = donor_ids.to_numpy(dtype=object)
    else:
        values = np.asarray(donor_ids, dtype=object)
    if values.ndim != 1:
        raise ValueError(f"donor_ids must be one-dimensional, got shape {values.shape}")
    if values.size == 0:
        raise ValueError("donor_ids is empty")
    for position, value in enumerate(values):
        if value is None or (isinstance(value, float) and np.isnan(value)):
            raise ValueError(f"donor_ids contains a null identifier at position {position}")
        if not str(value).strip():
            raise ValueError(f"donor_ids contains a blank identifier at position {position}")
    return values.astype(object)


def _validate_fractions(val_fraction: float, test_fraction: float, n_donors: int) -> None:
    if not (0.0 < val_fraction < 1.0):
        raise ValueError(f"val_fraction must be in (0, 1), got {val_fraction}")
    if not (0.0 < test_fraction < 1.0):
        raise ValueError(f"test_fraction must be in (0, 1), got {test_fraction}")
    if val_fraction + test_fraction >= 1.0 - FRACTION_TOLERANCE:
        raise ValueError(
            "val_fraction + test_fraction must leave a training share, got "
            f"{val_fraction} + {test_fraction}"
        )
    if n_donors < len(SPLIT_NAMES):
        raise ValueError(f"need at least {len(SPLIT_NAMES)} donors to split, got {n_donors}")


def _allocate_donor_counts(
    n_donors: int, val_fraction: float, test_fraction: float
) -> tuple[int, int, int]:
    """Give every split at least one donor, then distribute the rest by fraction."""
    n_val = max(1, int(round(n_donors * val_fraction)))
    n_test = max(1, int(round(n_donors * test_fraction)))
    while n_val + n_test > n_donors - 1:
        if n_val >= n_test and n_val > 1:
            n_val -= 1
        elif n_test > 1:
            n_test -= 1
        else:
            break
    n_train = n_donors - n_val - n_test
    if n_train < 1:
        raise ValueError(f"cannot leave a training donor with {n_donors} donors")
    return n_train, n_val, n_test


def _label_distribution(labels: np.ndarray | None, index: np.ndarray) -> dict[str, int] | None:
    if labels is None:
        return None
    values, counts = np.unique(labels[index], return_counts=True)
    return {f"class_{value}": int(count) for value, count in zip(values, counts, strict=True)}


def make_donor_split(
    donor_ids: Sequence[Any] | np.ndarray | pd.Series,
    labels: Sequence[Any] | np.ndarray | None = None,
    val_fraction: float = 0.2,
    test_fraction: float = 0.2,
    seed: int = 0,
) -> DonorSplit:
    """Split donors into train, validation, and test, then map cells to those donors.

    Args:
        donor_ids: donor identifier per cell.
        labels: optional label per cell, used only for reporting.
        val_fraction: share of donors held for model selection.
        test_fraction: share of donors held for the final estimate.
        seed: seed for the donor shuffle; the same seed gives the same split.

    Returns:
        A :class:`DonorSplit` where every cell is assigned exactly once and no
        donor appears in more than one split.

    Raises:
        ValueError: on null or blank identifiers, invalid fractions, too few
            donors, or a label array whose length does not match ``donor_ids``.
    """
    donors_per_cell = _as_donor_array(donor_ids)
    unique_donors = np.array(sorted({str(value) for value in donors_per_cell}), dtype=object)
    _validate_fractions(val_fraction, test_fraction, unique_donors.size)

    label_array: np.ndarray | None = None
    if labels is not None:
        label_array = np.asarray(labels)
        if label_array.shape[0] != donors_per_cell.shape[0]:
            raise ValueError(
                f"labels has {label_array.shape[0]} rows but donor_ids has "
                f"{donors_per_cell.shape[0]}"
            )

    rng = np.random.default_rng(seed)
    shuffled = unique_donors[rng.permutation(unique_donors.size)]
    n_train, n_val, n_test = _allocate_donor_counts(unique_donors.size, val_fraction, test_fraction)

    train_donors = tuple(sorted(str(value) for value in shuffled[:n_train]))
    val_donors = tuple(sorted(str(value) for value in shuffled[n_train : n_train + n_val]))
    test_donors = tuple(sorted(str(value) for value in shuffled[n_train + n_val :]))
    assert len(test_donors) == n_test

    as_str = np.array([str(value) for value in donors_per_cell], dtype=object)
    index = {
        "train": np.flatnonzero(np.isin(as_str, np.array(train_donors, dtype=object))),
        "val": np.flatnonzero(np.isin(as_str, np.array(val_donors, dtype=object))),
        "test": np.flatnonzero(np.isin(as_str, np.array(test_donors, dtype=object))),
    }

    summary: dict[str, Any] = {
        "seed": int(seed),
        "n_cells": int(donors_per_cell.size),
        "n_donors": int(unique_donors.size),
        "requested_fractions": {
            "train": round(1.0 - val_fraction - test_fraction, 6),
            "val": float(val_fraction),
            "test": float(test_fraction),
        },
        "realized_donor_counts": {"train": n_train, "val": n_val, "test": n_test},
        "realized_cell_counts": {name: int(index[name].size) for name in SPLIT_NAMES},
        "label_distribution": {
            name: _label_distribution(label_array, index[name]) for name in SPLIT_NAMES
        },
        "label_balance_note": "label balance is reported, not enforced by donor splitting",
        "split_unit": "donor",
    }

    split = DonorSplit(
        train_donors=train_donors,
        val_donors=val_donors,
        test_donors=test_donors,
        train_index=index["train"],
        val_index=index["val"],
        test_index=index["test"],
        summary=summary,
    )
    validate_donor_split(split, donors_per_cell, labels=label_array)
    return split


def donor_split_problems(
    split: DonorSplit,
    donor_ids: Sequence[Any] | np.ndarray | pd.Series,
    labels: Sequence[Any] | np.ndarray | None = None,
) -> list[str]:
    """Return one problem string per violation of the donor-split contract."""
    problems: list[str] = []
    try:
        donors_per_cell = _as_donor_array(donor_ids)
    except ValueError as error:
        return [str(error)]

    as_str = np.array([str(value) for value in donors_per_cell], dtype=object)
    donor_sets = {name: set(split.donors(name)) for name in SPLIT_NAMES}

    for first, second in (("train", "val"), ("train", "test"), ("val", "test")):
        shared = sorted(donor_sets[first] & donor_sets[second])
        if shared:
            problems.append(f"donors appear in both {first} and {second}: {shared}")

    for name in SPLIT_NAMES:
        if not donor_sets[name]:
            problems.append(f"{name} split has no donors")

    assigned = np.concatenate([split.index(name) for name in SPLIT_NAMES])
    if assigned.size != donors_per_cell.size:
        problems.append(
            f"split assigns {assigned.size} cells but donor_ids has {donors_per_cell.size}"
        )
    if np.unique(assigned).size != assigned.size:
        problems.append("a cell is assigned to more than one split")
    missing = np.setdiff1d(np.arange(donors_per_cell.size), assigned)
    if missing.size:
        problems.append(f"{missing.size} cells are not assigned to any split")

    for name in SPLIT_NAMES:
        positions = split.index(name)
        if positions.size == 0:
            problems.append(f"{name} split has no cells")
            continue
        if positions.min() < 0 or positions.max() >= donors_per_cell.size:
            problems.append(f"{name} split contains an out-of-range cell position")
            continue
        foreign = sorted(set(as_str[positions]) - donor_sets[name])
        if foreign:
            problems.append(
                f"{name} cells belong to donors outside the {name} donor list: {foreign}"
            )

    if labels is not None:
        label_array = np.asarray(labels)
        if label_array.shape[0] != donors_per_cell.shape[0]:
            problems.append(
                f"labels has {label_array.shape[0]} rows but donor_ids has "
                f"{donors_per_cell.shape[0]}"
            )
    return problems


def validate_donor_split(
    split: DonorSplit,
    donor_ids: Sequence[Any] | np.ndarray | pd.Series,
    labels: Sequence[Any] | np.ndarray | None = None,
) -> dict[str, Any]:
    """Validate a donor split and return its report.

    Raises:
        ValueError: if any donor appears in more than one split, any cell is
            unassigned or assigned twice, or a split is empty.
    """
    problems = donor_split_problems(split, donor_ids, labels=labels)
    if problems:
        raise ValueError("; ".join(problems))
    report = dict(split.summary)
    report["donor_overlap"] = 0
    report["unassigned_cells"] = 0
    report["validated"] = True
    return report

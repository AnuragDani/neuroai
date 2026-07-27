"""Tests for donor-held-out splitting."""

from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd
import pytest

from p22.data import DonorSplit, donor_split_problems, make_donor_split, validate_donor_split
from p22.testing import make_synthetic_multimodal

SPLIT_NAMES = ("train", "val", "test")


@pytest.fixture(scope="module")
def dataset():
    return make_synthetic_multimodal(seed=42)


@pytest.fixture(scope="module")
def split(dataset):
    return make_donor_split(dataset.donor_ids, labels=dataset.labels, seed=0)


def test_donors_do_not_overlap(split):
    train, val, test = split.train_donors, split.val_donors, split.test_donors
    assert set(train) & set(val) == set()
    assert set(train) & set(test) == set()
    assert set(val) & set(test) == set()
    assert len(set(train) | set(val) | set(test)) == 12


def test_every_cell_is_assigned_exactly_once(dataset, split):
    assigned = np.concatenate([split.index(name) for name in SPLIT_NAMES])
    assert assigned.size == dataset.n_cells
    assert np.array_equal(np.unique(assigned), np.arange(dataset.n_cells))


def test_cells_follow_their_donor(dataset, split):
    for name in SPLIT_NAMES:
        donors_in_split = set(dataset.donor_ids[split.index(name)])
        assert donors_in_split == set(split.donors(name))


def test_summary_reports_counts_and_labels(split):
    summary = split.summary
    assert summary["split_unit"] == "donor"
    assert sum(summary["realized_donor_counts"].values()) == 12
    assert sum(summary["realized_cell_counts"].values()) == summary["n_cells"]
    for name in SPLIT_NAMES:
        distribution = summary["label_distribution"][name]
        assert distribution
        assert sum(distribution.values()) == summary["realized_cell_counts"][name]
    assert "reported" in summary["label_balance_note"]


def test_frame_view(split):
    frame = split.as_frame()
    assert list(frame["split"]) == list(SPLIT_NAMES)
    assert frame["cells"].sum() == split.n_cells


def test_same_seed_is_deterministic(dataset):
    first = make_donor_split(dataset.donor_ids, seed=3)
    second = make_donor_split(dataset.donor_ids, seed=3)
    assert first.train_donors == second.train_donors
    np.testing.assert_array_equal(first.test_index, second.test_index)


def test_different_seed_changes_donor_assignment(dataset):
    first = make_donor_split(dataset.donor_ids, seed=3)
    second = make_donor_split(dataset.donor_ids, seed=4)
    assert first.train_donors != second.train_donors


def test_labels_are_optional(dataset):
    split = make_donor_split(dataset.donor_ids, seed=1)
    assert split.summary["label_distribution"]["train"] is None


def test_accepts_pandas_series(dataset):
    series = pd.Series(dataset.donor_ids, name="donor_id")
    split = make_donor_split(series, seed=0)
    assert split.n_cells == dataset.n_cells


def test_fraction_requests_are_reflected(dataset):
    split = make_donor_split(dataset.donor_ids, val_fraction=0.25, test_fraction=0.25, seed=0)
    counts = split.summary["realized_donor_counts"]
    assert counts == {"train": 6, "val": 3, "test": 3}


def test_minimum_donor_counts_are_respected():
    donor_ids = [f"donor_{index:02d}" for index in range(3) for _ in range(4)]
    split = make_donor_split(donor_ids, val_fraction=0.1, test_fraction=0.1, seed=0)
    counts = split.summary["realized_donor_counts"]
    assert counts == {"train": 1, "val": 1, "test": 1}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"val_fraction": 0.0},
        {"val_fraction": 1.0},
        {"test_fraction": -0.2},
        {"val_fraction": 0.6, "test_fraction": 0.5},
    ],
)
def test_invalid_fractions_are_rejected(dataset, kwargs):
    with pytest.raises(ValueError):
        make_donor_split(dataset.donor_ids, **kwargs)


def test_too_few_donors_is_rejected():
    with pytest.raises(ValueError, match="at least 3 donors"):
        make_donor_split(["donor_00", "donor_00", "donor_01"])


def test_null_donor_ids_are_rejected():
    with pytest.raises(ValueError, match="null identifier"):
        make_donor_split(["donor_00", None, "donor_01", "donor_02"])


def test_blank_donor_ids_are_rejected():
    with pytest.raises(ValueError, match="blank identifier"):
        make_donor_split(["donor_00", "  ", "donor_01", "donor_02"])


def test_empty_donor_ids_are_rejected():
    with pytest.raises(ValueError, match="empty"):
        make_donor_split([])


def test_label_length_mismatch_is_rejected(dataset):
    with pytest.raises(ValueError, match="labels has"):
        make_donor_split(dataset.donor_ids, labels=dataset.labels[:-1])


def test_validate_rejects_donor_overlap(dataset, split):
    leaking = dataclasses.replace(
        split,
        val_donors=split.val_donors + (split.train_donors[0],),
    )
    problems = donor_split_problems(leaking, dataset.donor_ids)
    assert any("appear in both train and val" in problem for problem in problems)
    with pytest.raises(ValueError, match="appear in both train and val"):
        validate_donor_split(leaking, dataset.donor_ids)


def test_validate_rejects_incomplete_assignment(dataset, split):
    truncated = dataclasses.replace(split, test_index=split.test_index[:-1])
    with pytest.raises(ValueError, match="not assigned"):
        validate_donor_split(truncated, dataset.donor_ids)


def test_validate_rejects_duplicate_assignment(dataset, split):
    duplicated = dataclasses.replace(
        split, val_index=np.concatenate([split.val_index, split.train_index[:1]])
    )
    problems = donor_split_problems(duplicated, dataset.donor_ids)
    assert any("more than one split" in problem for problem in problems)


def test_validate_rejects_empty_split(dataset, split):
    empty = dataclasses.replace(
        split,
        val_donors=(),
        val_index=np.array([], dtype=int),
    )
    problems = donor_split_problems(empty, dataset.donor_ids)
    assert any("no donors" in problem for problem in problems)


def test_validate_rejects_cells_from_foreign_donor(dataset, split):
    swapped = dataclasses.replace(
        split,
        train_index=np.concatenate([split.train_index, split.test_index[:1]]),
        test_index=split.test_index[1:],
    )
    problems = donor_split_problems(swapped, dataset.donor_ids)
    assert any("outside the train donor list" in problem for problem in problems)


def test_validate_returns_report(dataset, split):
    report = validate_donor_split(split, dataset.donor_ids, labels=dataset.labels)
    assert report["validated"] is True
    assert report["donor_overlap"] == 0
    assert report["unassigned_cells"] == 0


def test_split_is_a_frozen_dataclass(split):
    assert isinstance(split, DonorSplit)
    with pytest.raises(dataclasses.FrozenInstanceError):
        split.train_donors = ()

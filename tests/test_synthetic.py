"""Tests for the deterministic synthetic two-view generator."""

from __future__ import annotations

import re

import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

from p22.testing import LATENT_DIM, make_synthetic_multimodal


def test_donor_label_fixture_is_pure_balanced_and_reproducible():
    fixture = make_synthetic_multimodal(n_donors=12, n_classes=2, label_unit="donor")
    assert (fixture.metadata.groupby("donor_id")["label"].nunique() == 1).all()
    assert sorted(fixture.metadata.groupby("donor_id")["label"].first().value_counts()) == [6, 6]
    again = make_synthetic_multimodal(n_donors=12, n_classes=2, label_unit="donor")
    np.testing.assert_array_equal(fixture.view_a, again.view_a)
    with pytest.raises(ValueError, match="label_unit"):
        make_synthetic_multimodal(label_unit="unknown")

BIOLOGICAL_WORDS = ("gene", "rna", "atac", "cell_type", "neuron", "expression", "morph")


@pytest.fixture(scope="module")
def dataset():
    return make_synthetic_multimodal()


def test_default_shapes_and_dtypes(dataset):
    assert dataset.view_a.shape == (240, 16)
    assert dataset.view_b.shape == (240, 12)
    assert dataset.view_a.dtype == np.float32
    assert dataset.view_b.dtype == np.float32
    assert dataset.labels.shape == (240,)
    assert dataset.labels.dtype == np.int64
    assert dataset.n_cells == 240
    assert dataset.n_donors == 12
    assert dataset.n_classes == 3
    assert dataset.generation["latent_dim"] == LATENT_DIM


def test_arrays_are_finite(dataset):
    assert np.isfinite(dataset.view_a).all()
    assert np.isfinite(dataset.view_b).all()
    assert dataset.metadata.notna().all().all()


def test_identifiers_are_unique_and_complete(dataset):
    assert len(set(dataset.cell_ids)) == dataset.n_cells
    assert len(set(dataset.donor_ids)) == 12
    counts = dataset.metadata["donor_id"].value_counts()
    assert set(counts.unique()) == {20}
    assert list(dataset.metadata["cell_id"]) == list(dataset.cell_ids)


def test_identifiers_use_neutral_names(dataset):
    for identifier in list(dataset.cell_ids[:5]) + list(dataset.donor_ids[:5]):
        assert re.fullmatch(r"(cell|donor)_\d+", identifier)
    text = " ".join(dataset.metadata.columns) + " ".join(map(str, dataset.metadata["label_name"]))
    for word in BIOLOGICAL_WORDS:
        assert word not in text.lower(), word


def test_same_seed_is_identical():
    first = make_synthetic_multimodal(seed=7)
    second = make_synthetic_multimodal(seed=7)
    np.testing.assert_array_equal(first.view_a, second.view_a)
    np.testing.assert_array_equal(first.view_b, second.view_b)
    np.testing.assert_array_equal(first.labels, second.labels)
    np.testing.assert_array_equal(first.donor_ids, second.donor_ids)


def test_different_seed_changes_arrays():
    first = make_synthetic_multimodal(seed=7)
    second = make_synthetic_multimodal(seed=8)
    assert not np.array_equal(first.view_a, second.view_a)
    assert not np.array_equal(first.view_b, second.view_b)
    assert not np.array_equal(first.labels, second.labels)
    np.testing.assert_array_equal(first.donor_ids, second.donor_ids)


def test_every_class_appears(dataset):
    assert set(np.unique(dataset.labels)) == {0, 1, 2}
    distribution = dataset.label_distribution()
    assert distribution.sum() == dataset.n_cells
    assert list(distribution.index) == ["class_0", "class_1", "class_2"]


def test_label_mix_is_uneven_across_donors(dataset):
    table = dataset.donor_label_counts()
    assert table.shape == (12, 3)
    # Donor-specific propensities are the point: at least one donor must differ
    # from the pooled mix.
    pooled = table.sum(axis=0) / table.values.sum()
    per_donor = table.div(table.sum(axis=1), axis=0)
    assert (per_donor.sub(pooled, axis=1).abs().max(axis=1) > 0.1).any()


def test_donor_nuisance_is_present(dataset):
    donor_means = dataset.metadata.groupby("donor_id")["view_b_total"].mean()
    within = dataset.metadata.groupby("donor_id")["view_b_total"].std().mean()
    assert donor_means.std() > 0.2 * within


def test_signal_is_imperfect_and_present(dataset):
    model = LogisticRegression(max_iter=2000)
    model.fit(dataset.view_a, dataset.labels)
    accuracy = model.score(dataset.view_a, dataset.labels)
    chance = dataset.label_distribution().max() / dataset.n_cells
    assert accuracy > chance
    assert accuracy < 1.0, "a perfect in-sample fit means the world is too easy"


def test_views_carry_different_information(dataset):
    scores = {}
    for name, view in (("view_a", dataset.view_a), ("view_b", dataset.view_b)):
        model = LogisticRegression(max_iter=2000)
        model.fit(view, dataset.labels)
        scores[name] = model.score(view, dataset.labels)
    assert scores["view_a"] < 1.0 and scores["view_b"] < 1.0
    assert (
        dataset.generation["view_latent_weights"]["view_a"]
        != (dataset.generation["view_latent_weights"]["view_b"])
    )


def test_generation_record_is_reproducible(dataset):
    generation = dataset.generation
    assert generation["data_mode"] == "synthetic"
    assert generation["seed"] == 42
    assert generation["generator"].endswith("make_synthetic_multimodal")
    replay = make_synthetic_multimodal(
        n_donors=generation["n_donors"],
        cells_per_donor=generation["cells_per_donor"],
        n_features_a=generation["n_features_a"],
        n_features_b=generation["n_features_b"],
        n_classes=generation["n_classes"],
        seed=generation["seed"],
    )
    np.testing.assert_array_equal(replay.view_a, dataset.view_a)


def test_shape_arguments_are_respected():
    dataset = make_synthetic_multimodal(
        n_donors=4, cells_per_donor=5, n_features_a=3, n_features_b=6, n_classes=2, seed=1
    )
    assert dataset.view_a.shape == (20, 3)
    assert dataset.view_b.shape == (20, 6)
    assert set(np.unique(dataset.labels)) == {0, 1}


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"n_donors": 1}, ValueError),
        ({"cells_per_donor": 0}, ValueError),
        ({"n_classes": 1}, ValueError),
        ({"n_features_a": -3}, ValueError),
        ({"noise": -0.1}, ValueError),
        ({"label_concentration": 0.0}, ValueError),
        ({"n_donors": 2.5}, TypeError),
        ({"n_classes": True}, TypeError),
    ],
)
def test_invalid_arguments_are_rejected(kwargs, error):
    with pytest.raises(error):
        make_synthetic_multimodal(**kwargs)

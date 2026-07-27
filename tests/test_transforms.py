"""Tests for train-only preprocessing contracts."""

from __future__ import annotations

import re

import numpy as np
import pytest

from p22.data import make_donor_split
from p22.data.transforms import PCA_KIND, STANDARD_SCALER, fit_train_only
from p22.testing import make_synthetic_multimodal


@pytest.fixture(scope="module")
def world():
    dataset = make_synthetic_multimodal(seed=42)
    split = make_donor_split(dataset.donor_ids, labels=dataset.labels, seed=0)
    train_ids = dataset.cell_ids[split.train_index]
    holdout_ids = np.concatenate(
        [dataset.cell_ids[split.val_index], dataset.cell_ids[split.test_index]]
    )
    return dataset, split, train_ids, holdout_ids


@pytest.fixture(scope="module")
def scaler(world):
    dataset, _, train_ids, holdout_ids = world
    return fit_train_only(
        dataset.view_a,
        cell_ids=dataset.cell_ids,
        train_cell_ids=train_ids,
        holdout_cell_ids=holdout_ids,
    )


def test_scaler_statistics_come_from_train_cells_only(world, scaler):
    dataset, split, _, _ = world
    expected_mean = dataset.view_a[split.train_index].astype(np.float64).mean(axis=0)
    np.testing.assert_allclose(scaler.transformer.mean_, expected_mean, rtol=1e-10)


def test_holdout_values_cannot_change_the_fit(world):
    dataset, split, train_ids, holdout_ids = world
    tampered = dataset.view_a.astype(np.float64).copy()
    tampered[split.test_index] += 1000.0
    tampered[split.val_index] *= -7.0
    refit = fit_train_only(
        tampered,
        cell_ids=dataset.cell_ids,
        train_cell_ids=train_ids,
        holdout_cell_ids=holdout_ids,
    )
    baseline = fit_train_only(
        dataset.view_a,
        cell_ids=dataset.cell_ids,
        train_cell_ids=train_ids,
        holdout_cell_ids=holdout_ids,
    )
    np.testing.assert_allclose(refit.transformer.mean_, baseline.transformer.mean_, rtol=1e-10)
    assert refit.metadata["parameter_fingerprint"] == baseline.metadata["parameter_fingerprint"]


def test_train_transform_is_standardised_but_holdout_is_not(world, scaler):
    dataset, split, _, _ = world
    train_out = scaler.transform(dataset.view_a[split.train_index])
    test_out = scaler.transform(dataset.view_a[split.test_index])
    np.testing.assert_allclose(train_out.mean(axis=0), 0.0, atol=1e-5)
    np.testing.assert_allclose(train_out.std(axis=0), 1.0, atol=1e-4)
    assert np.abs(test_out.mean(axis=0)).max() > 1e-4, "held-out data must not be re-centred"


def test_metadata_records_provenance(scaler):
    metadata = scaler.metadata
    assert metadata["kind"] == STANDARD_SCALER
    assert metadata["transformer_class"].endswith("StandardScaler")
    assert metadata["fit_scope"] == "train cells only"
    assert metadata["n_train_cells"] == 160
    assert metadata["n_features_in"] == 16
    assert metadata["n_features_out"] == 16
    assert re.fullmatch(r"[0-9a-f]{64}", metadata["training_id_hash"])
    assert re.fullmatch(r"[0-9a-f]{64}", metadata["parameter_fingerprint"])
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", metadata["fitted_at"])
    assert metadata["p22_version"]
    assert "with_mean" in metadata["parameters"]


def test_training_id_hash_is_order_independent_but_set_sensitive(world):
    dataset, split, train_ids, holdout_ids = world
    reversed_ids = train_ids[::-1]
    same_set = fit_train_only(
        dataset.view_a,
        cell_ids=dataset.cell_ids,
        train_cell_ids=reversed_ids,
        holdout_cell_ids=holdout_ids,
    )
    smaller = fit_train_only(
        dataset.view_a,
        cell_ids=dataset.cell_ids,
        train_cell_ids=train_ids[:-1],
        holdout_cell_ids=holdout_ids,
    )
    baseline_hash = fit_train_only(
        dataset.view_a,
        cell_ids=dataset.cell_ids,
        train_cell_ids=train_ids,
        holdout_cell_ids=holdout_ids,
    ).training_id_hash
    assert same_set.training_id_hash == baseline_hash
    assert smaller.training_id_hash != baseline_hash


def test_pca_is_supported(world):
    dataset, split, train_ids, holdout_ids = world
    fitted = fit_train_only(
        dataset.view_a,
        cell_ids=dataset.cell_ids,
        train_cell_ids=train_ids,
        holdout_cell_ids=holdout_ids,
        kind=PCA_KIND,
        n_components=5,
        seed=3,
    )
    assert fitted.n_features_out == 5
    assert fitted.metadata["transformer_class"].endswith("PCA")
    projected = fitted.transform(dataset.view_a[split.test_index])
    assert projected.shape == (split.test_index.size, 5)
    assert projected.dtype == np.float32
    train_projection = fitted.transform(dataset.view_a[split.train_index])
    np.testing.assert_allclose(train_projection.mean(axis=0), 0.0, atol=1e-4)


def test_pca_fit_uses_train_rows_only(world):
    dataset, split, train_ids, holdout_ids = world
    tampered = dataset.view_a.astype(np.float64).copy()
    tampered[split.test_index] += 500.0
    first = fit_train_only(
        dataset.view_a,
        cell_ids=dataset.cell_ids,
        train_cell_ids=train_ids,
        holdout_cell_ids=holdout_ids,
        kind=PCA_KIND,
        n_components=4,
    )
    second = fit_train_only(
        tampered,
        cell_ids=dataset.cell_ids,
        train_cell_ids=train_ids,
        holdout_cell_ids=holdout_ids,
        kind=PCA_KIND,
        n_components=4,
    )
    np.testing.assert_allclose(
        np.abs(first.transformer.components_), np.abs(second.transformer.components_), rtol=1e-8
    )


def test_holdout_identifier_inside_fit_set_is_rejected(world):
    dataset, _, train_ids, holdout_ids = world
    leaking = np.concatenate([train_ids, holdout_ids[:1]])
    with pytest.raises(ValueError, match="would leak"):
        fit_train_only(
            dataset.view_a,
            cell_ids=dataset.cell_ids,
            train_cell_ids=leaking,
            holdout_cell_ids=holdout_ids,
        )


def test_unknown_training_identifier_is_rejected(world):
    dataset, _, train_ids, holdout_ids = world
    with pytest.raises(ValueError, match="not present in cell_ids"):
        fit_train_only(
            dataset.view_a,
            cell_ids=dataset.cell_ids,
            train_cell_ids=np.append(train_ids, "cell_99999"),
            holdout_cell_ids=holdout_ids,
        )


def test_transform_rejects_wrong_feature_count(world, scaler):
    dataset, _, _, _ = world
    with pytest.raises(ValueError, match="features, transform was fitted on"):
        scaler.transform(dataset.view_b)


def test_transform_rejects_mutated_parameters(world):
    dataset, split, train_ids, holdout_ids = world
    fitted = fit_train_only(
        dataset.view_a,
        cell_ids=dataset.cell_ids,
        train_cell_ids=train_ids,
        holdout_cell_ids=holdout_ids,
    )
    fitted.transformer.mean_ = fitted.transformer.mean_ + 1.0
    with pytest.raises(ValueError, match="not frozen"):
        fitted.transform(dataset.view_a[split.test_index])


def test_non_finite_input_is_rejected(world, scaler):
    dataset, _, train_ids, holdout_ids = world
    broken = dataset.view_a.astype(np.float64).copy()
    broken[0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        fit_train_only(
            broken,
            cell_ids=dataset.cell_ids,
            train_cell_ids=train_ids,
            holdout_cell_ids=holdout_ids,
        )
    with pytest.raises(ValueError, match="non-finite"):
        scaler.transform(broken)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"kind": "quantile"}, "unknown transform kind"),
        ({"kind": PCA_KIND}, "n_components is required"),
        ({"n_components": 3}, "does not apply"),
        ({"kind": PCA_KIND, "n_components": 999}, "n_components must be in"),
    ],
)
def test_invalid_kind_arguments_are_rejected(world, kwargs, message):
    dataset, _, train_ids, holdout_ids = world
    with pytest.raises(ValueError, match=message):
        fit_train_only(
            dataset.view_a,
            cell_ids=dataset.cell_ids,
            train_cell_ids=train_ids,
            holdout_cell_ids=holdout_ids,
            **kwargs,
        )


def test_identifier_problems_are_rejected(world):
    dataset, _, train_ids, holdout_ids = world
    with pytest.raises(ValueError, match="entries but matrix has"):
        fit_train_only(
            dataset.view_a,
            cell_ids=dataset.cell_ids[:-1],
            train_cell_ids=train_ids,
        )
    duplicated = dataset.cell_ids.copy()
    duplicated[1] = duplicated[0]
    with pytest.raises(ValueError, match="duplicate identifiers"):
        fit_train_only(
            dataset.view_a,
            cell_ids=duplicated,
            train_cell_ids=train_ids,
        )
    with pytest.raises(ValueError, match="empty"):
        fit_train_only(
            dataset.view_a,
            cell_ids=dataset.cell_ids,
            train_cell_ids=[],
        )
    with pytest.raises(ValueError, match="null or blank"):
        fit_train_only(
            dataset.view_a,
            cell_ids=dataset.cell_ids,
            train_cell_ids=np.append(train_ids[:-1], None),
        )

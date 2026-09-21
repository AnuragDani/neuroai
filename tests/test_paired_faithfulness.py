"""Tests for donor-level paired faithfulness and initialization sensitivity.

Claims under test: the intervention table reuses the seven held-out manipulations,
the donor metric matches the estimand aggregation, a non-gated model reports the
uniform-route intervention as not applicable while a gated model measures it, and
initialization-seed spread is summarised without overclaiming.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from p22.eval.faithfulness import CLAMP_VIEW_A, INTERVENTIONS, UNIFORM_ROUTE
from p22.eval.paired_faithfulness import (
    aggregate_interventions,
    donor_balanced_accuracy,
    initialization_seed_spread,
    run_donor_interventions,
)
from p22.models.fusion import VIEW_A, VIEW_B, ConcatFusionModel, GatedFusionModel
from p22.training.loop import train_model

N_FEATURES_A = 6
N_FEATURES_B = 5
CELLS_PER_DONOR = 10


def make_binary_world(seed: int = 0):
    rng = np.random.default_rng(seed)
    donors = np.repeat([f"donor_{index:02d}" for index in range(8)], CELLS_PER_DONOR)
    n_cells = donors.size
    labels = np.repeat([0, 1, 0, 1, 0, 1, 0, 1], CELLS_PER_DONOR)
    centres = rng.normal(scale=3.0, size=(2, N_FEATURES_A))
    view_a = centres[labels] + rng.normal(scale=0.6, size=(n_cells, N_FEATURES_A))
    view_b = rng.normal(scale=1.0, size=(n_cells, N_FEATURES_B))
    return {
        "donors": donors,
        "labels": labels,
        VIEW_A: view_a.astype(np.float32),
        VIEW_B: view_b.astype(np.float32),
    }


def _splits(world):
    donors = world["donors"]
    unique = sorted(set(donors))
    train_donors, val_donors, test_donors = unique[:4], unique[4:6], unique[6:]
    masks = {
        "train": np.isin(donors, train_donors),
        "val": np.isin(donors, val_donors),
        "test": np.isin(donors, test_donors),
    }
    return {
        split: {
            VIEW_A: world[VIEW_A][mask],
            VIEW_B: world[VIEW_B][mask],
            "labels": world["labels"][mask],
            "donors": donors[mask],
        }
        for split, mask in masks.items()
    }


def _fit(model, splits):
    return train_model(
        model,
        {VIEW_A: splits["train"][VIEW_A], VIEW_B: splits["train"][VIEW_B]},
        splits["train"]["labels"],
        {VIEW_A: splits["val"][VIEW_A], VIEW_B: splits["val"][VIEW_B]},
        splits["val"]["labels"],
        max_epochs=20,
        batch_size=16,
        learning_rate=0.02,
        patience=20,
        seed=0,
        train_donor_ids=splits["train"]["donors"],
        val_donor_ids=splits["val"]["donors"],
    ).model


@pytest.fixture(scope="module")
def gated_run():
    world = make_binary_world()
    splits = _splits(world)
    torch.manual_seed(0)
    model = GatedFusionModel(
        n_features_a=N_FEATURES_A,
        n_features_b=N_FEATURES_B,
        n_classes=2,
        embed_dim=8,
        hidden_dim=16,
    )
    _fit(model, splits)
    test, train = splits["test"], splits["train"]
    rows = run_donor_interventions(
        model,
        {VIEW_A: test[VIEW_A], VIEW_B: test[VIEW_B]},
        {VIEW_A: train[VIEW_A], VIEW_B: train[VIEW_B]},
        test["labels"],
        test["donors"],
        seed=0,
    )
    return model, splits, rows


@pytest.fixture(scope="module")
def nongated_run():
    world = make_binary_world()
    splits = _splits(world)
    torch.manual_seed(0)
    model = ConcatFusionModel(
        n_features_a=N_FEATURES_A,
        n_features_b=N_FEATURES_B,
        n_classes=2,
        embed_dim=8,
        hidden_dim=16,
    )
    _fit(model, splits)
    test, train = splits["test"], splits["train"]
    rows = run_donor_interventions(
        model,
        {VIEW_A: test[VIEW_A], VIEW_B: test[VIEW_B]},
        {VIEW_A: train[VIEW_A], VIEW_B: train[VIEW_B]},
        test["labels"],
        test["donors"],
        seed=0,
    )
    return model, splits, rows


def test_donor_metric_matches_manual_aggregation():
    donors = ["a", "a", "b", "b"]
    labels = [0, 0, 1, 1]
    probabilities = np.array([0.1, 0.3, 0.9, 0.7])
    result = donor_balanced_accuracy(probabilities, donors, labels)
    assert result["n_donors"] == 2
    assert result["n_control"] == 1
    assert result["n_positive"] == 1
    assert result["value"] == pytest.approx(1.0)


def test_donor_metric_rejects_length_mismatch():
    with pytest.raises(ValueError):
        donor_balanced_accuracy(np.array([0.1, 0.2]), ["a"], [0, 0])


def test_all_seven_interventions_are_reported(gated_run):
    _, _, rows = gated_run
    assert [row["intervention"] for row in rows] == list(INTERVENTIONS)


def test_gated_model_measures_uniform_route(gated_run):
    _, _, rows = gated_run
    route = next(row for row in rows if row["intervention"] == UNIFORM_ROUTE)
    assert route["status"] == "measured"
    assert route["routing_shift"] is not None


def test_nongated_model_refuses_uniform_route(nongated_run):
    _, _, rows = nongated_run
    route = next(row for row in rows if row["intervention"] == UNIFORM_ROUTE)
    assert route["status"] == "NOT_APPLICABLE"
    assert route["not_applicable"]


def test_before_metric_matches_direct_aggregation(gated_run):
    model, splits, rows = gated_run
    from p22.eval.faithfulness import predict_with

    test = splits["test"]
    baseline = predict_with(model, {VIEW_A: test[VIEW_A], VIEW_B: test[VIEW_B]})
    expected = donor_balanced_accuracy(baseline.probabilities[:, 1], test["donors"], test["labels"])
    measured = {row["donor_balanced_accuracy_before"] for row in rows}
    assert measured == {expected["value"]}


def test_measured_rows_report_finite_effects(gated_run):
    _, _, rows = gated_run
    for row in rows:
        if row["status"] != "measured":
            continue
        assert 0.0 <= row["cell_flip_rate"] <= 1.0
        assert np.isfinite(row["mean_confidence_drop"])
        assert row["n_donors"] == 2
        assert row["evidence"]


def test_initialization_seed_spread_summary():
    summary = initialization_seed_spread({0: 0.5, 1: 0.625, 2: 0.75})
    assert summary["seeds"] == [0, 1, 2]
    assert summary["min"] == pytest.approx(0.5)
    assert summary["max"] == pytest.approx(0.75)
    assert summary["spread"] == pytest.approx(0.25)
    assert summary["n_seeds"] == 3


def test_initialization_seed_spread_rejects_empty_and_nonfinite():
    with pytest.raises(ValueError):
        initialization_seed_spread({})
    with pytest.raises(ValueError):
        initialization_seed_spread({0: float("nan")})


def _measured_row(name, before, after, drop, routing=None):
    return {
        "intervention": name,
        "status": "measured",
        "donor_balanced_accuracy_before": before,
        "donor_balanced_accuracy_after": after,
        "donor_balanced_accuracy_drop": drop,
        "routing_shift": routing,
    }


def _not_applicable_row(name, before):
    return {
        "intervention": name,
        "status": "NOT_APPLICABLE",
        "donor_balanced_accuracy_before": before,
        "donor_balanced_accuracy_after": None,
        "donor_balanced_accuracy_drop": None,
        "routing_shift": None,
    }


def _table(rows_by_name):
    return [rows_by_name[name] for name in INTERVENTIONS]


def test_aggregate_interventions_means_over_measured_folds():
    clamp = CLAMP_VIEW_A
    tables = [
        _table({name: _measured_row(name, 0.6, 0.4, 0.2) for name in INTERVENTIONS}),
        _table({name: _measured_row(name, 0.4, 0.2, 0.2) for name in INTERVENTIONS}),
    ]
    summary = aggregate_interventions({"concat": tables})["concat"][clamp]
    assert summary["n_folds"] == 2
    assert summary["n_folds_measured"] == 2
    assert summary["n_folds_not_applicable"] == 0
    assert summary["donor_balanced_accuracy_before_mean"] == pytest.approx(0.5)
    assert summary["donor_balanced_accuracy_after_mean"] == pytest.approx(0.3)
    assert summary["donor_balanced_accuracy_drop_mean"] == pytest.approx(0.2)
    assert summary["donor_balanced_accuracy_drop_min"] == pytest.approx(0.2)
    assert summary["donor_balanced_accuracy_drop_max"] == pytest.approx(0.2)


def test_aggregate_interventions_refusal_is_not_a_zero_effect():
    tables = [
        _table({name: _measured_row(name, 0.6, 0.5, 0.1) for name in INTERVENTIONS}),
        _table(
            {
                name: (
                    _not_applicable_row(name, 0.6)
                    if name == UNIFORM_ROUTE
                    else _measured_row(name, 0.6, 0.5, 0.1)
                )
                for name in INTERVENTIONS
            }
        ),
    ]
    route = aggregate_interventions({"concat": tables})["concat"][UNIFORM_ROUTE]
    assert route["n_folds_measured"] == 1
    assert route["n_folds_not_applicable"] == 1
    assert route["donor_balanced_accuracy_drop_mean"] == pytest.approx(0.1)


def test_aggregate_interventions_reports_routing_shift_only_where_measured():
    tables = [
        _table(
            {
                name: _measured_row(
                    name, 0.6, 0.5, 0.1, routing=0.4 if name == UNIFORM_ROUTE else None
                )
                for name in INTERVENTIONS
            }
        )
    ]
    summary = aggregate_interventions({"gated": tables})["gated"]
    assert summary[UNIFORM_ROUTE]["routing_shift_mean"] == pytest.approx(0.4)
    assert summary[CLAMP_VIEW_A]["routing_shift_mean"] is None


def test_aggregate_interventions_rejects_unknown_status():
    tables = [
        _table({name: _measured_row(name, 0.6, 0.5, 0.1) for name in INTERVENTIONS}),
    ]
    tables[0][0] = {**tables[0][0], "status": "MAYBE"}
    with pytest.raises(ValueError, match="unknown status"):
        aggregate_interventions({"concat": tables})


def test_aggregate_interventions_rejects_missing_intervention():
    tables = [[_measured_row(CLAMP_VIEW_A, 0.6, 0.5, 0.1)]]
    with pytest.raises(ValueError, match="missing intervention"):
        aggregate_interventions({"concat": tables})


def test_aggregate_interventions_rejects_empty_family():
    with pytest.raises(ValueError, match="no fold tables"):
        aggregate_interventions({"concat": []})

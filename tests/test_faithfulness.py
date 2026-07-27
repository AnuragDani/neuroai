"""Tests for the held-out routing interventions.

Claims under test: permutations stay inside a donor, the clamp value comes from training
data, an intervention on an informative view moves predictions more than the same
intervention on a noise view, and every reported effect is labelled as intervention
evidence rather than a causal finding.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from p22.eval.faithfulness import (
    ABLATE_VIEW_A,
    ABLATE_VIEW_B,
    CLAMP_VIEW_A,
    CLAMP_VIEW_B,
    INTERVENTIONS,
    PERMUTE_VIEW_A,
    PERMUTE_VIEW_B,
    UNIFORM_ROUTE,
    clamp_to_train_mean,
    intervention_table,
    permute_within_donor,
    predict_with,
    run_all_interventions,
    run_intervention,
)
from p22.models.fusion import VIEW_A, VIEW_B, ConcatFusionModel, GatedFusionModel
from p22.training.loop import train_model

N_CLASSES = 3
N_FEATURES_A = 6
N_FEATURES_B = 5


def make_world(seed: int = 0, n_donors: int = 8, cells_per_donor: int = 12):
    """Build a world where view A carries the label and view B is noise.

    A model fitted here should depend on view A. That gives the interventions something
    with a known answer to detect.
    """
    rng = np.random.default_rng(seed)
    donors = np.repeat([f"donor_{index:02d}" for index in range(n_donors)], cells_per_donor)
    n_cells = donors.size
    labels = rng.integers(0, N_CLASSES, size=n_cells)
    centres = rng.normal(scale=3.0, size=(N_CLASSES, N_FEATURES_A))
    view_a = centres[labels] + rng.normal(scale=0.6, size=(n_cells, N_FEATURES_A))
    view_b = rng.normal(scale=1.0, size=(n_cells, N_FEATURES_B))
    return {
        "donors": donors,
        "labels": labels,
        VIEW_A: view_a.astype(np.float32),
        VIEW_B: view_b.astype(np.float32),
    }


@pytest.fixture(scope="module")
def trained_world():
    """A gated model fitted on donor-split data where only view A is informative."""
    world = make_world(seed=0)
    donors = world["donors"]
    unique = sorted(set(donors))
    train_donors, val_donors, test_donors = unique[:4], unique[4:6], unique[6:]
    masks = {
        "train": np.isin(donors, train_donors),
        "val": np.isin(donors, val_donors),
        "test": np.isin(donors, test_donors),
    }
    splits = {
        split: {
            VIEW_A: world[VIEW_A][mask],
            VIEW_B: world[VIEW_B][mask],
            "labels": world["labels"][mask],
            "donors": donors[mask],
        }
        for split, mask in masks.items()
    }
    torch.manual_seed(0)
    model = GatedFusionModel(
        n_features_a=N_FEATURES_A,
        n_features_b=N_FEATURES_B,
        n_classes=N_CLASSES,
        embed_dim=8,
        hidden_dim=16,
    )
    trained = train_model(
        model,
        {VIEW_A: splits["train"][VIEW_A], VIEW_B: splits["train"][VIEW_B]},
        splits["train"]["labels"],
        {VIEW_A: splits["val"][VIEW_A], VIEW_B: splits["val"][VIEW_B]},
        splits["val"]["labels"],
        max_epochs=25,
        batch_size=16,
        learning_rate=0.02,
        patience=25,
        seed=0,
    )
    return trained.model, splits


@pytest.fixture(scope="module")
def effects(trained_world):
    model, splits = trained_world
    test = splits["test"]
    return run_all_interventions(
        model,
        {VIEW_A: test[VIEW_A], VIEW_B: test[VIEW_B]},
        test["labels"],
        test["donors"],
        train_views={VIEW_A: splits["train"][VIEW_A], VIEW_B: splits["train"][VIEW_B]},
        seed=0,
    )


class TestPermutationStaysInsideDonors:
    def test_each_donor_keeps_exactly_its_own_rows(self):
        world = make_world(seed=1, n_donors=5, cells_per_donor=6)
        permuted = permute_within_donor(world[VIEW_A], world["donors"], seed=3)
        for donor in np.unique(world["donors"]):
            rows = world["donors"] == donor
            original = {tuple(row) for row in world[VIEW_A][rows]}
            shuffled = {tuple(row) for row in permuted[rows]}
            assert original == shuffled

    def test_no_row_moves_between_donors(self):
        world = make_world(seed=2, n_donors=4, cells_per_donor=8)
        permuted = permute_within_donor(world[VIEW_A], world["donors"], seed=5)
        first_donor = world["donors"] == "donor_00"
        elsewhere = {tuple(row) for row in world[VIEW_A][~first_donor]}
        assert all(tuple(row) not in elsewhere for row in permuted[first_donor])

    def test_permutation_actually_reorders_rows(self):
        world = make_world(seed=3, n_donors=3, cells_per_donor=10)
        permuted = permute_within_donor(world[VIEW_A], world["donors"], seed=1)
        assert not np.array_equal(permuted, world[VIEW_A])
        assert permuted.shape == world[VIEW_A].shape

    def test_same_seed_gives_the_same_permutation(self):
        world = make_world(seed=4, n_donors=3, cells_per_donor=8)
        first = permute_within_donor(world[VIEW_A], world["donors"], seed=7)
        second = permute_within_donor(world[VIEW_A], world["donors"], seed=7)
        other = permute_within_donor(world[VIEW_A], world["donors"], seed=8)
        assert np.array_equal(first, second)
        assert not np.array_equal(first, other)

    def test_single_cell_donor_is_left_alone(self):
        matrix = np.arange(6, dtype=float).reshape(3, 2)
        donors = np.array(["a", "b", "b"])
        permuted = permute_within_donor(matrix, donors, seed=0)
        assert np.array_equal(permuted[0], matrix[0])

    def test_rejects_shape_problems(self):
        matrix = np.zeros((4, 2))
        with pytest.raises(ValueError, match="covers"):
            permute_within_donor(matrix, np.array(["a", "b", "c"]))
        with pytest.raises(ValueError, match="two-dimensional"):
            permute_within_donor(np.zeros(4), np.array(["a", "b", "c", "d"]))


class TestClamp:
    def test_every_row_becomes_the_training_mean(self):
        train = np.array([[0.0, 10.0], [2.0, 20.0]])
        clamped = clamp_to_train_mean(np.zeros((5, 2)), train)
        assert clamped.shape == (5, 2)
        assert np.allclose(clamped, np.array([1.0, 15.0]))

    def test_clamp_value_ignores_the_held_out_cells(self):
        train = np.zeros((4, 3))
        holdout = np.full((6, 3), 99.0)
        clamped = clamp_to_train_mean(holdout, train)
        assert np.allclose(clamped, 0.0)

    def test_rejects_feature_mismatch(self):
        with pytest.raises(ValueError, match="features"):
            clamp_to_train_mean(np.zeros((3, 4)), np.zeros((3, 2)))


class TestPredictWith:
    def test_returns_labels_probabilities_and_routing(self, trained_world):
        model, splits = trained_world
        test = splits["test"]
        prediction = predict_with(model, {VIEW_A: test[VIEW_A], VIEW_B: test[VIEW_B]})
        n_cells = test["labels"].size
        assert prediction.labels.shape == (n_cells,)
        assert prediction.probabilities.shape == (n_cells, N_CLASSES)
        assert np.allclose(prediction.probabilities.sum(axis=1), 1.0, atol=1e-5)
        assert prediction.routing_weights.shape == (n_cells, 2)
        assert np.allclose(prediction.routing_weights.sum(axis=1), 1.0, atol=1e-5)

    def test_missing_view_is_refused(self, trained_world):
        model, splits = trained_world
        with pytest.raises(ValueError, match="needs view"):
            predict_with(model, {VIEW_A: splits["test"][VIEW_A]})

    def test_route_override_needs_a_gate(self, trained_world):
        _, splits = trained_world
        torch.manual_seed(0)
        concat = ConcatFusionModel(
            n_features_a=N_FEATURES_A,
            n_features_b=N_FEATURES_B,
            n_classes=N_CLASSES,
            embed_dim=8,
            hidden_dim=16,
        )
        test = splits["test"]
        with pytest.raises(ValueError, match="no gate"):
            predict_with(
                concat,
                {VIEW_A: test[VIEW_A], VIEW_B: test[VIEW_B]},
                route_override=[0.5, 0.5],
            )


class TestInterventionSet:
    def test_seven_interventions_are_defined(self):
        assert len(INTERVENTIONS) == 7
        assert set(INTERVENTIONS) == {
            CLAMP_VIEW_A,
            CLAMP_VIEW_B,
            PERMUTE_VIEW_A,
            PERMUTE_VIEW_B,
            ABLATE_VIEW_A,
            ABLATE_VIEW_B,
            UNIFORM_ROUTE,
        }

    def test_all_seven_run_and_report(self, effects):
        assert sorted(effects) == sorted(INTERVENTIONS)
        for name, effect in effects.items():
            assert effect.name == name
            assert effect.n_cells > 0

    def test_unknown_intervention_is_refused(self, trained_world):
        model, splits = trained_world
        test = splits["test"]
        with pytest.raises(ValueError, match="unknown intervention"):
            run_intervention(
                "delete_the_inconvenient_cells",
                model,
                {VIEW_A: test[VIEW_A], VIEW_B: test[VIEW_B]},
                test["labels"],
                test["donors"],
            )

    def test_clamp_without_training_views_is_refused(self, trained_world):
        model, splits = trained_world
        test = splits["test"]
        with pytest.raises(ValueError, match="comes from training data"):
            run_intervention(
                CLAMP_VIEW_A,
                model,
                {VIEW_A: test[VIEW_A], VIEW_B: test[VIEW_B]},
                test["labels"],
                test["donors"],
            )

    def test_unknown_metric_is_refused(self, trained_world):
        model, splits = trained_world
        test = splits["test"]
        with pytest.raises(ValueError, match="metric_name"):
            run_intervention(
                ABLATE_VIEW_A,
                model,
                {VIEW_A: test[VIEW_A], VIEW_B: test[VIEW_B]},
                test["labels"],
                test["donors"],
                metric_name="vibes",
            )


class TestReportedQuantities:
    def test_flip_rate_and_confidence_drop_are_finite(self, effects):
        for name, effect in effects.items():
            if effect.not_applicable:
                continue
            assert 0.0 <= effect.flip_rate <= 1.0, name
            assert np.isfinite(effect.mean_confidence_drop), name

    def test_metric_drop_is_before_minus_after(self, effects):
        for effect in effects.values():
            if effect.not_applicable:
                continue
            assert effect.metric_drop == pytest.approx(effect.metric_before - effect.metric_after)

    def test_baseline_metric_is_shared_across_interventions(self, effects):
        values = {effect.metric_before for effect in effects.values()}
        assert len(values) == 1

    def test_per_donor_summary_covers_every_held_out_donor(self, effects, trained_world):
        _, splits = trained_world
        expected = {str(donor) for donor in set(splits["test"]["donors"])}
        for effect in effects.values():
            if effect.not_applicable:
                continue
            assert set(effect.per_donor) == expected
            assert sum(entry["n_cells"] for entry in effect.per_donor.values()) == effect.n_cells

    def test_per_label_summary_covers_every_label_present(self, effects, trained_world):
        _, splits = trained_world
        expected = {f"class_{label}" for label in set(splits["test"]["labels"].tolist())}
        for effect in effects.values():
            if effect.not_applicable:
                continue
            assert set(effect.per_label) == expected

    def test_routing_shift_is_reported_for_a_gated_model(self, effects):
        assert effects[UNIFORM_ROUTE].routing_shift is not None
        assert effects[UNIFORM_ROUTE].routing_shift >= 0.0

    def test_every_effect_is_labelled_as_intervention_evidence(self, effects):
        for effect in effects.values():
            assert "not a causal claim about biology" in effect.evidence
            assert "intervention evidence" in effect.evidence

    def test_effects_serialise_with_their_evidence_statement(self, effects):
        record = effects[ABLATE_VIEW_A].to_dict()
        assert record["name"] == ABLATE_VIEW_A
        assert record["target_view"] == VIEW_A
        assert "evidence" in record
        assert "per_donor" in record and "per_label" in record


class TestSensitivityToTheInformativeView:
    def test_interventions_on_the_label_carrying_view_hurt_more(self, effects):
        for informative, noise in (
            (CLAMP_VIEW_A, CLAMP_VIEW_B),
            (PERMUTE_VIEW_A, PERMUTE_VIEW_B),
            (ABLATE_VIEW_A, ABLATE_VIEW_B),
        ):
            assert effects[informative].metric_drop > effects[noise].metric_drop, informative
            assert effects[informative].flip_rate > effects[noise].flip_rate, informative

    def test_removing_the_informative_view_costs_real_accuracy(self, effects):
        assert effects[ABLATE_VIEW_A].metric_drop > 0.1
        assert effects[ABLATE_VIEW_A].flip_rate > 0.1

    def test_noise_view_interventions_barely_move_predictions(self, effects):
        assert effects[ABLATE_VIEW_B].flip_rate < 0.5


class TestUniformRoute:
    def test_gated_model_reports_a_measured_effect(self, effects):
        effect = effects[UNIFORM_ROUTE]
        assert effect.not_applicable is None
        assert effect.target_view is None
        assert effect.flip_rate is not None

    def test_model_without_a_gate_reports_why_it_does_not_apply(self, trained_world):
        _, splits = trained_world
        torch.manual_seed(0)
        concat = ConcatFusionModel(
            n_features_a=N_FEATURES_A,
            n_features_b=N_FEATURES_B,
            n_classes=N_CLASSES,
            embed_dim=8,
            hidden_dim=16,
        )
        test = splits["test"]
        effect = run_intervention(
            UNIFORM_ROUTE,
            concat,
            {VIEW_A: test[VIEW_A], VIEW_B: test[VIEW_B]},
            test["labels"],
            test["donors"],
        )
        assert effect.flip_rate is None
        assert "no gate" in effect.not_applicable
        assert effect.metric_before is not None


class TestDeterminismAndTable:
    def test_same_seed_reproduces_the_permutation_effect(self, trained_world):
        model, splits = trained_world
        test = splits["test"]
        arguments = (
            model,
            {VIEW_A: test[VIEW_A], VIEW_B: test[VIEW_B]},
            test["labels"],
            test["donors"],
        )
        first = run_intervention(PERMUTE_VIEW_A, *arguments, seed=11)
        second = run_intervention(PERMUTE_VIEW_A, *arguments, seed=11)
        other = run_intervention(PERMUTE_VIEW_A, *arguments, seed=12)
        assert first.to_dict() == second.to_dict()
        assert 0.0 <= other.flip_rate <= 1.0
        assert other.metric_before == first.metric_before

    def test_table_has_one_row_per_intervention_in_a_fixed_order(self, effects):
        rows = intervention_table(effects)
        assert [row["intervention"] for row in rows] == list(INTERVENTIONS)
        assert all("status" in row for row in rows)

    def test_table_surfaces_a_not_applicable_status(self, trained_world):
        _, splits = trained_world
        torch.manual_seed(0)
        concat = ConcatFusionModel(
            n_features_a=N_FEATURES_A,
            n_features_b=N_FEATURES_B,
            n_classes=N_CLASSES,
            embed_dim=8,
            hidden_dim=16,
        )
        test = splits["test"]
        effects = run_all_interventions(
            concat,
            {VIEW_A: test[VIEW_A], VIEW_B: test[VIEW_B]},
            test["labels"],
            test["donors"],
            train_views={VIEW_A: splits["train"][VIEW_A], VIEW_B: splits["train"][VIEW_B]},
        )
        rows = {row["intervention"]: row["status"] for row in intervention_table(effects)}
        assert "no gate" in rows[UNIFORM_ROUTE]
        assert rows[ABLATE_VIEW_A] == "measured"

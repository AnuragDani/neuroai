"""Tests for the training loop.

The claims under test: selection reads the validation split only, the returned weights are
the best validation weights rather than the last ones, and the same seed gives the same
result on CPU.
"""

from __future__ import annotations

import inspect

import numpy as np
import pytest
import torch

from p22.models.baselines import BaselineMLP
from p22.models.fusion import VIEW_A, VIEW_B, ConcatFusionModel, GatedFusionModel
from p22.training.loop import (
    SELECTION_METRICS,
    forward_logits,
    forward_views,
    predict,
    set_all_seeds,
    train_model,
)


def separable_split(seed: int = 0, n_features: int = 6, n_classes: int = 3):
    """Return an easy two-split problem where training should reduce loss."""
    rng = np.random.default_rng(seed)
    centres = rng.normal(scale=3.0, size=(n_classes, n_features))

    def sample(n_per_class: int):
        labels = np.repeat(np.arange(n_classes), n_per_class)
        features = centres[labels] + rng.normal(scale=0.5, size=(labels.size, n_features))
        return features.astype(np.float32), labels

    train_features, train_labels = sample(24)
    val_features, val_labels = sample(8)
    return (train_features, train_labels), (val_features, val_labels)


def small_mlp(n_features: int = 6, n_classes: int = 3) -> BaselineMLP:
    torch.manual_seed(0)
    return BaselineMLP(n_features=n_features, n_classes=n_classes, embed_dim=8, hidden_dim=16)


class TestSeeding:
    def test_seeds_python_numpy_and_torch_together(self):
        record = set_all_seeds(7)
        assert record == {"python_random": 7, "numpy": 7, "torch": 7}

    def test_same_seed_reproduces_draws_from_every_generator(self):
        import random

        set_all_seeds(3)
        first = (random.random(), np.random.rand(), float(torch.rand(1)))
        set_all_seeds(3)
        second = (random.random(), np.random.rand(), float(torch.rand(1)))
        assert first == second

    def test_rejects_negative_or_non_integer_seeds(self):
        with pytest.raises(ValueError, match="non-negative"):
            set_all_seeds(-1)
        with pytest.raises(ValueError, match="must be an int"):
            set_all_seeds(1.5)


class TestForwardHelpers:
    def test_single_view_model_takes_exactly_one_view(self):
        model = small_mlp()
        view = torch.randn(10, 6)
        logits = forward_logits(model, {VIEW_A: view})
        assert logits.shape == (10, 3)
        with pytest.raises(ValueError, match="exactly one view"):
            forward_logits(model, {VIEW_A: view, VIEW_B: torch.randn(10, 4)})

    def test_fusion_model_needs_both_views(self):
        torch.manual_seed(0)
        model = ConcatFusionModel(
            n_features_a=6, n_features_b=4, n_classes=3, embed_dim=8, hidden_dim=16
        )
        with pytest.raises(ValueError, match="needs view"):
            forward_logits(model, {VIEW_A: torch.randn(10, 6)})
        logits = forward_logits(model, {VIEW_A: torch.randn(10, 6), VIEW_B: torch.randn(10, 4)})
        assert logits.shape == (10, 3)

    def test_forward_views_returns_the_native_output_type(self):
        torch.manual_seed(0)
        gated = GatedFusionModel(
            n_features_a=6, n_features_b=4, n_classes=3, embed_dim=8, hidden_dim=16
        )
        output = forward_views(gated, {VIEW_A: torch.randn(5, 6), VIEW_B: torch.randn(5, 4)})
        assert output.routing_weights.shape == (5, 2)
        plain = forward_views(small_mlp(), {VIEW_A: torch.randn(5, 6)})
        assert isinstance(plain, torch.Tensor)

    def test_single_view_model_refuses_fusion_only_arguments(self):
        with pytest.raises(ValueError, match="does not accept"):
            forward_logits(small_mlp(), {VIEW_A: torch.randn(4, 6)}, route_override=[1.0, 0.0])


class TestSelectionCannotSeeTest:
    def test_signature_has_no_test_arguments(self):
        parameters = set(inspect.signature(train_model).parameters)
        assert not any("test" in name for name in parameters)
        assert {"train_views", "train_labels", "val_views", "val_labels"} <= parameters

    def test_selection_split_is_recorded_as_val(self):
        (train_features, train_labels), (val_features, val_labels) = separable_split()
        trained = train_model(
            small_mlp(),
            {VIEW_A: train_features},
            train_labels,
            {VIEW_A: val_features},
            val_labels,
            max_epochs=3,
            patience=3,
            seed=0,
        )
        assert trained.to_dict()["selection_split"] == "val"


class TestTrainingBehaviour:
    def test_training_reduces_loss_on_a_separable_problem(self):
        (train_features, train_labels), (val_features, val_labels) = separable_split()
        trained = train_model(
            small_mlp(),
            {VIEW_A: train_features},
            train_labels,
            {VIEW_A: val_features},
            val_labels,
            max_epochs=15,
            batch_size=16,
            learning_rate=0.01,
            patience=15,
            seed=0,
        )
        assert trained.history[-1].train_loss < trained.history[0].train_loss
        assert trained.best_val_score > 0.5

    def test_returned_weights_are_the_best_validation_weights(self):
        (train_features, train_labels), (val_features, val_labels) = separable_split()
        trained = train_model(
            small_mlp(),
            {VIEW_A: train_features},
            train_labels,
            {VIEW_A: val_features},
            val_labels,
            max_epochs=12,
            batch_size=16,
            learning_rate=0.01,
            patience=12,
            seed=1,
        )
        from p22.eval.metrics import balanced_accuracy

        predictions, _ = predict(trained.model, {VIEW_A: val_features})
        rescored = balanced_accuracy(val_labels, predictions).value
        assert rescored == pytest.approx(trained.best_val_score)
        assert trained.best_val_score == pytest.approx(
            max(record.val_score for record in trained.history)
        )

    def test_early_stopping_respects_patience(self):
        (train_features, train_labels), (val_features, val_labels) = separable_split()
        trained = train_model(
            small_mlp(),
            {VIEW_A: train_features},
            train_labels,
            {VIEW_A: val_features},
            val_labels,
            max_epochs=60,
            batch_size=16,
            learning_rate=0.02,
            patience=2,
            seed=2,
        )
        assert trained.epochs_run <= 60
        assert trained.epochs_run <= trained.best_epoch + 2
        if trained.epochs_run < 60:
            assert trained.stopped_early

    def test_history_covers_every_epoch_run(self):
        (train_features, train_labels), (val_features, val_labels) = separable_split()
        trained = train_model(
            small_mlp(),
            {VIEW_A: train_features},
            train_labels,
            {VIEW_A: val_features},
            val_labels,
            max_epochs=5,
            patience=5,
            seed=0,
        )
        assert len(trained.history) == trained.epochs_run
        assert [record.epoch for record in trained.history] == list(
            range(1, trained.epochs_run + 1)
        )

    def test_same_seed_gives_the_same_result(self):
        (train_features, train_labels), (val_features, val_labels) = separable_split()

        def run(seed: int):
            return train_model(
                small_mlp(),
                {VIEW_A: train_features},
                train_labels,
                {VIEW_A: val_features},
                val_labels,
                max_epochs=6,
                batch_size=16,
                learning_rate=0.01,
                patience=6,
                seed=seed,
            )

        first, second, other = run(4), run(4), run(5)
        assert [record.train_loss for record in first.history] == [
            record.train_loss for record in second.history
        ]
        assert [record.train_loss for record in first.history] != [
            record.train_loss for record in other.history
        ]

    def test_runs_on_cpu_by_default(self):
        (train_features, train_labels), (val_features, val_labels) = separable_split()
        trained = train_model(
            small_mlp(),
            {VIEW_A: train_features},
            train_labels,
            {VIEW_A: val_features},
            val_labels,
            max_epochs=2,
            patience=2,
        )
        assert trained.device == "cpu"
        assert all(parameter.device.type == "cpu" for parameter in trained.model.parameters())

    def test_trains_fusion_models_too(self):
        (train_a, train_labels), (val_a, val_labels) = separable_split(seed=1)
        (train_b, _), (val_b, _) = separable_split(seed=2, n_features=4)
        torch.manual_seed(0)
        model = GatedFusionModel(
            n_features_a=train_a.shape[1],
            n_features_b=train_b.shape[1],
            n_classes=3,
            embed_dim=8,
            hidden_dim=16,
        )
        trained = train_model(
            model,
            {VIEW_A: train_a, VIEW_B: train_b},
            train_labels,
            {VIEW_A: val_a, VIEW_B: val_b},
            val_labels,
            max_epochs=6,
            batch_size=16,
            learning_rate=0.01,
            patience=6,
            seed=0,
        )
        assert trained.epochs_run >= 1
        predictions, probabilities = predict(trained.model, {VIEW_A: val_a, VIEW_B: val_b})
        assert predictions.shape == val_labels.shape
        assert np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-5)


class TestTrainingRefusals:
    def setup_method(self):
        (self.train_features, self.train_labels), (self.val_features, self.val_labels) = (
            separable_split()
        )

    def _train(self, **overrides):
        arguments = {
            "model": small_mlp(),
            "train_views": {VIEW_A: self.train_features},
            "train_labels": self.train_labels,
            "val_views": {VIEW_A: self.val_features},
            "val_labels": self.val_labels,
            "max_epochs": 2,
            "patience": 2,
        }
        arguments.update(overrides)
        return train_model(**arguments)

    def test_unknown_selection_metric_is_refused(self):
        with pytest.raises(ValueError, match="unknown selection_metric"):
            self._train(selection_metric="vibes")

    def test_selection_metrics_are_the_documented_set(self):
        assert set(SELECTION_METRICS) == {
            "accuracy",
            "balanced_accuracy",
            "macro_f1",
            "weighted_f1",
        }

    def test_invalid_hyperparameters_are_refused(self):
        with pytest.raises(ValueError, match="max_epochs"):
            self._train(max_epochs=0)
        with pytest.raises(ValueError, match="batch_size"):
            self._train(batch_size=-1)
        with pytest.raises(ValueError, match="learning_rate"):
            self._train(learning_rate=5.0)

    def test_mismatched_view_names_are_refused(self):
        with pytest.raises(ValueError, match="do not match"):
            self._train(val_views={VIEW_B: self.val_features})

    def test_mismatched_feature_widths_are_refused(self):
        with pytest.raises(ValueError, match="training features"):
            self._train(val_views={VIEW_A: self.val_features[:, :-1]})

    def test_label_and_row_mismatch_is_refused(self):
        with pytest.raises(ValueError, match="labels were given"):
            self._train(train_labels=self.train_labels[:-1])

    def test_empty_split_is_refused(self):
        with pytest.raises(ValueError, match="no cells"):
            self._train(val_views={VIEW_A: self.val_features[:0]}, val_labels=self.val_labels[:0])

    def test_non_finite_features_are_refused(self):
        broken = self.train_features.copy()
        broken[0, 0] = np.nan
        with pytest.raises(ValueError, match="non-finite"):
            self._train(train_views={VIEW_A: broken})

    def test_validation_split_that_cannot_score_is_refused(self):
        single_class = np.zeros(self.val_labels.size, dtype=int)
        with pytest.raises(ValueError, match="cannot support"):
            self._train(val_labels=single_class, selection_metric="balanced_accuracy")


class EpochProbabilityModel(torch.nn.Module):
    """Controlled predictions expose cell-versus-donor checkpoint selection."""

    def __init__(self):
        super().__init__()
        self.bias = torch.nn.Parameter(torch.tensor(0.0))
        self.epoch = 0

    def forward(self, features):
        if self.training:
            self.epoch += 1
            probability = torch.full((len(features),), 0.8)
        else:
            probability = torch.tensor(
                [0.1] * 9 + [0.9, 0.9] if self.epoch == 1 else [0.9] * 4 + [0.01] * 5 + [0.1, 0.9]
            )
        return torch.stack([(1 - probability).log(), probability.log()], dim=1) + self.bias


def donor_training_arguments():
    return dict(
        train_views={VIEW_A: np.ones((4, 1))},
        train_labels=np.array([0, 0, 0, 1]),
        val_views={VIEW_A: np.ones((11, 1))},
        val_labels=np.array([0] * 10 + [1]),
        train_donor_ids=["t0"] * 3 + ["t1"],
        val_donor_ids=["v0"] * 9 + ["v1", "v2"],
        max_epochs=2,
        batch_size=64,
        patience=2,
    )


def test_donor_selection_differs_from_cell_selection_and_weights_donors_equally():
    arguments = donor_training_arguments()
    donor_run = train_model(EpochProbabilityModel(), **arguments)
    assert donor_run.best_epoch == 2
    assert donor_run.best_val_score == 1.0
    assert donor_run.to_dict()["selection_unit"] == "donor"
    assert donor_run.to_dict()["training_weighting"] == "inverse_donor_cell_count"
    assert donor_run.history[0].train_loss == pytest.approx(-np.log([0.2, 0.8]).mean())
    arguments.pop("train_donor_ids")
    arguments.pop("val_donor_ids")
    cell_run = train_model(EpochProbabilityModel(), **arguments)
    assert cell_run.best_epoch == 1
    assert cell_run.to_dict()["selection_unit"] == "cell"


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"train_donor_ids": None}, "both"),
        ({"val_donor_ids": ["t0"] * 9 + ["v1", "v2"]}, "overlap"),
        ({"train_donor_ids": ["t0"] * 4}, "mixed labels"),
        ({"val_donor_ids": ["v0"]}, "length"),
        ({"val_donor_ids": [None] * 11}, "null"),
        ({"val_labels": [0] * 11}, "both binary classes"),
        ({"train_labels": [0, 0, 0, 0.5]}, "both binary classes"),
    ],
)
def test_donor_training_rejects_invalid_identity_or_labels_before_fitting(overrides, message):
    arguments = donor_training_arguments() | overrides
    model = EpochProbabilityModel()
    with pytest.raises(ValueError, match=message):
        train_model(model, **arguments)
    assert model.epoch == 0


def test_final_refit_runs_exact_frozen_epochs_without_validation():
    import numpy as np
    import torch

    from p22.models.baselines import BaselineMLP
    from p22.training.loop import refit_model, set_all_seeds

    views = {"rna": np.arange(24, dtype=np.float32).reshape(8, 3) / 24}
    labels = np.array([0] * 4 + [1] * 4)
    donors = ["a"] * 3 + ["b"] + ["c"] * 2 + ["d"] * 2
    set_all_seeds(7)
    model = BaselineMLP(3, n_classes=2, dropout=0)
    before = {key: value.clone() for key, value in model.state_dict().items()}
    result = refit_model(model, views, labels, donors, epochs=3, batch_size=4, seed=7)
    assert result["epochs_run"] == 3 and len(result["train_loss"]) == 3
    assert result["selection_split"] is None
    assert result["training_weighting"] == "inverse_donor_cell_count"
    assert not model.training
    assert any(not torch.equal(before[key], value) for key, value in model.state_dict().items())
    with pytest.raises(ValueError):
        refit_model(model, views, labels, donors, epochs=True)

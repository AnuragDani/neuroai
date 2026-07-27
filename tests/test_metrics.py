"""Tests for classification metrics.

The central claim under test: a metric that cannot be computed says so, and never
returns a NaN that could be mistaken for a measurement.
"""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.metrics import balanced_accuracy_score, f1_score, roc_auc_score

from p22.eval.metrics import (
    MetricValue,
    accuracy,
    balanced_accuracy,
    compute_metrics,
    macro_f1,
    macro_ovr_auroc,
    multiclass_ece,
    weighted_f1,
)


def one_hot(labels: np.ndarray, n_classes: int) -> np.ndarray:
    matrix = np.zeros((labels.size, n_classes), dtype=np.float64)
    matrix[np.arange(labels.size), labels] = 1.0
    return matrix


def soft_probabilities(labels: np.ndarray, n_classes: int, confidence: float) -> np.ndarray:
    rest = (1.0 - confidence) / (n_classes - 1)
    matrix = np.full((labels.size, n_classes), rest, dtype=np.float64)
    matrix[np.arange(labels.size), labels] = confidence
    return matrix


class TestAccuracy:
    def test_counts_exact_matches(self):
        y_true = np.array([0, 1, 2, 0, 1, 2])
        y_pred = np.array([0, 1, 2, 0, 2, 1])
        result = accuracy(y_true, y_pred)
        assert result.value == pytest.approx(4 / 6)
        assert result.applicable
        assert result.not_applicable is None
        assert result.detail["n_cells"] == 6

    def test_all_correct_and_all_wrong(self):
        y_true = np.array([0, 1, 0, 1])
        assert accuracy(y_true, y_true).value == 1.0
        assert accuracy(y_true, 1 - y_true).value == 0.0

    def test_rejects_length_mismatch(self):
        with pytest.raises(ValueError, match="shape"):
            accuracy(np.array([0, 1, 0]), np.array([0, 1]))

    def test_rejects_empty_input(self):
        with pytest.raises(ValueError, match="empty"):
            accuracy(np.array([]), np.array([]))

    def test_rejects_two_dimensional_input(self):
        with pytest.raises(ValueError, match="one-dimensional"):
            accuracy(np.zeros((4, 2), dtype=int), np.zeros((4, 2), dtype=int))


class TestBalancedAccuracyAndF1:
    def test_balanced_accuracy_matches_reference(self):
        rng = np.random.default_rng(0)
        y_true = rng.integers(0, 3, size=200)
        y_pred = np.where(rng.random(200) < 0.7, y_true, rng.integers(0, 3, size=200))
        result = balanced_accuracy(y_true, y_pred)
        assert result.value == pytest.approx(balanced_accuracy_score(y_true, y_pred))

    def test_balanced_accuracy_penalises_majority_only_prediction(self):
        y_true = np.array([0] * 90 + [1] * 10)
        y_pred = np.zeros(100, dtype=int)
        plain = accuracy(y_true, y_pred).value
        balanced = balanced_accuracy(y_true, y_pred).value
        assert plain == pytest.approx(0.9)
        assert balanced == pytest.approx(0.5)
        assert balanced < plain

    def test_balanced_accuracy_not_applicable_for_single_class(self):
        y_true = np.zeros(10, dtype=int)
        result = balanced_accuracy(y_true, y_true)
        assert result.value is None
        assert not result.applicable
        assert "only 1 class" in result.not_applicable

    def test_macro_and_weighted_f1_match_reference(self):
        rng = np.random.default_rng(1)
        y_true = rng.integers(0, 4, size=300)
        y_pred = np.where(rng.random(300) < 0.6, y_true, rng.integers(0, 4, size=300))
        assert macro_f1(y_true, y_pred).value == pytest.approx(
            f1_score(y_true, y_pred, average="macro", zero_division=0)
        )
        assert weighted_f1(y_true, y_pred).value == pytest.approx(
            f1_score(y_true, y_pred, average="weighted", zero_division=0)
        )

    def test_macro_f1_differs_from_weighted_under_imbalance(self):
        y_true = np.array([0] * 90 + [1] * 10)
        y_pred = np.zeros(100, dtype=int)
        assert macro_f1(y_true, y_pred).value < weighted_f1(y_true, y_pred).value


class TestMacroOvrAuroc:
    def test_matches_reference_when_all_classes_present(self):
        rng = np.random.default_rng(2)
        y_true = rng.integers(0, 3, size=180)
        y_prob = soft_probabilities(y_true, 3, 0.6)
        y_prob = y_prob + rng.normal(scale=0.05, size=y_prob.shape)
        y_prob = np.clip(y_prob, 1e-6, None)
        y_prob = y_prob / y_prob.sum(axis=1, keepdims=True)
        result = macro_ovr_auroc(y_true, y_prob)
        expected = roc_auc_score(y_true, y_prob, multi_class="ovr", average="macro")
        assert result.value == pytest.approx(expected)
        assert result.detail["n_classes_present"] == 3

    def test_perfect_ranking_scores_one(self):
        y_true = np.array([0, 0, 1, 1, 2, 2])
        result = macro_ovr_auroc(y_true, one_hot(y_true, 3))
        assert result.value == pytest.approx(1.0)

    def test_not_applicable_when_a_class_is_absent(self):
        y_true = np.array([0, 0, 1, 1])
        y_prob = soft_probabilities(y_true, 3, 0.7)
        result = macro_ovr_auroc(y_true, y_prob)
        assert result.value is None
        assert "absent from y_true" in result.not_applicable
        assert result.detail["n_classes_present"] == 2
        assert result.detail["n_classes_expected"] == 3

    def test_not_applicable_when_column_count_disagrees(self):
        y_true = np.array([0, 1, 2, 0])
        y_prob = soft_probabilities(np.array([0, 1, 1, 0]), 2, 0.8)
        result = macro_ovr_auroc(y_true, y_prob, n_classes=3)
        assert result.value is None
        assert "expected 3" in result.not_applicable

    def test_value_is_never_nan(self):
        y_true = np.array([0, 0, 0, 0])
        result = macro_ovr_auroc(y_true, soft_probabilities(y_true, 2, 0.9))
        assert result.value is None
        assert result.not_applicable

    def test_rejects_rows_that_do_not_sum_to_one(self):
        y_true = np.array([0, 1])
        with pytest.raises(ValueError, match="sum to one"):
            macro_ovr_auroc(y_true, np.array([[0.2, 0.2], [0.5, 0.5]]))

    def test_rejects_probabilities_outside_unit_interval(self):
        y_true = np.array([0, 1])
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            macro_ovr_auroc(y_true, np.array([[1.4, -0.4], [0.5, 0.5]]))

    def test_rejects_row_count_mismatch(self):
        y_true = np.array([0, 1, 0])
        with pytest.raises(ValueError, match="rows"):
            macro_ovr_auroc(y_true, soft_probabilities(np.array([0, 1]), 2, 0.9))


class TestCalibration:
    def test_confident_and_correct_is_perfectly_calibrated(self):
        y_true = np.array([0, 1, 2, 0, 1, 2])
        result = multiclass_ece(y_true, one_hot(y_true, 3))
        assert result.value == pytest.approx(0.0)

    def test_confident_and_wrong_is_maximally_miscalibrated(self):
        y_true = np.array([0, 0, 0, 0])
        y_prob = one_hot(np.ones(4, dtype=int), 2)
        assert multiclass_ece(y_true, y_prob).value == pytest.approx(1.0)

    def test_matches_hand_computed_value(self):
        y_true = np.array([0, 0, 1, 1])
        y_prob = np.array([[0.9, 0.1], [0.9, 0.1], [0.9, 0.1], [0.1, 0.9]])
        # All four top-label confidences are 0.9 and three of four are correct,
        # so the single occupied bin contributes |0.75 - 0.9|.
        assert multiclass_ece(y_true, y_prob, n_bins=10).value == pytest.approx(0.15)

    def test_detail_reports_occupied_bins_only(self):
        y_true = np.array([0, 1, 0, 1])
        result = multiclass_ece(y_true, soft_probabilities(y_true, 2, 0.75), n_bins=10)
        assert result.detail["n_bins"] == 10
        assert result.detail["occupied_bins"] == 1
        assert result.detail["bins"][0]["cells"] == 4

    def test_rejects_non_positive_bin_count(self):
        y_true = np.array([0, 1])
        with pytest.raises(ValueError, match="n_bins"):
            multiclass_ece(y_true, one_hot(y_true, 2), n_bins=0)


class TestMetricBundle:
    def test_computes_the_full_set_when_probabilities_are_given(self):
        rng = np.random.default_rng(3)
        y_true = rng.integers(0, 3, size=120)
        y_prob = soft_probabilities(y_true, 3, 0.7)
        y_pred = y_prob.argmax(axis=1)
        results = compute_metrics(y_true, y_pred, y_prob)
        assert set(results) == {
            "accuracy",
            "balanced_accuracy",
            "macro_f1",
            "weighted_f1",
            "macro_ovr_auroc",
            "multiclass_ece",
        }
        assert all(isinstance(value, MetricValue) for value in results.values())
        assert all(value.applicable for value in results.values())

    def test_marks_probability_metrics_not_applicable_without_probabilities(self):
        y_true = np.array([0, 1, 0, 1])
        results = compute_metrics(y_true, y_true)
        assert results["accuracy"].value == 1.0
        for name in ("macro_ovr_auroc", "multiclass_ece"):
            assert results[name].value is None
            assert results[name].not_applicable == "probabilities were not supplied"

    def test_serialises_to_plain_dictionaries(self):
        y_true = np.array([0, 1, 0, 1])
        record = accuracy(y_true, y_true).to_dict()
        assert record == {
            "name": "accuracy",
            "value": 1.0,
            "not_applicable": None,
            "detail": {"n_cells": 4},
        }

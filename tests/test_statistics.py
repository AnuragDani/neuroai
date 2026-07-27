"""Tests for donor-level uncertainty and comparison statistics.

Two claims under test: resampling happens over whole donors rather than cells, and a
bootstrap that partly failed reports its failures instead of averaging over them.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats

from p22.eval.metrics import MetricValue, accuracy, balanced_accuracy
from p22.eval.statistics import (
    cohens_h,
    donor_bootstrap,
    mcnemar_test,
    summarize_seeds,
)


def donor_labels(n_donors: int, cells_per_donor: int) -> np.ndarray:
    return np.repeat([f"donor_{index:02d}" for index in range(n_donors)], cells_per_donor)


class TestDonorBootstrap:
    def test_interval_brackets_the_full_sample_estimate(self):
        rng = np.random.default_rng(0)
        donors = donor_labels(12, 20)
        y_true = rng.integers(0, 2, size=donors.size)
        y_pred = np.where(rng.random(donors.size) < 0.8, y_true, 1 - y_true)
        result = donor_bootstrap(accuracy, y_true, y_pred, donors, n_replicates=200, seed=0)
        assert result.estimate is not None
        assert result.lower <= result.estimate <= result.upper
        assert result.unit == "donor"
        assert result.level == 0.95
        assert result.not_applicable is None

    def test_replicate_counts_add_up(self):
        donors = donor_labels(8, 10)
        y_true = np.tile([0, 1], donors.size // 2)
        y_pred = y_true.copy()
        result = donor_bootstrap(accuracy, y_true, y_pred, donors, n_replicates=50, seed=1)
        assert result.n_replicates_requested == 50
        assert result.n_valid + result.n_failed == 50
        assert result.n_valid == 50

    def test_resamples_whole_donors_not_cells(self):
        donors = donor_labels(5, 7)
        # Donor identity is encoded in y_true so each replicate reveals which donors it drew.
        y_true = np.repeat(np.arange(5), 7)
        y_pred = y_true.copy()
        seen: list[np.ndarray] = []

        def recording_metric(subset_true: np.ndarray, subset_pred: np.ndarray) -> MetricValue:
            seen.append(subset_true.copy())
            return accuracy(subset_true, subset_pred)

        donor_bootstrap(recording_metric, y_true, y_pred, donors, n_replicates=20, seed=2)

        replicates = seen[1:]
        assert len(replicates) == 20
        for sample in replicates:
            assert sample.size == donors.size
            counts = np.bincount(sample, minlength=5)
            # Every donor appears zero times or as a full block of seven cells.
            assert set(np.unique(counts)) <= {0, 7, 14, 21, 28, 35}
            assert counts.sum() == donors.size

    def test_donor_bootstrap_is_wider_than_cell_resampling(self):
        rng = np.random.default_rng(3)
        n_donors, cells = 10, 40
        donors = donor_labels(n_donors, cells)
        # Donor-level skill varies, which is exactly what cell resampling misses.
        skill = rng.uniform(0.4, 1.0, size=n_donors)
        y_true = rng.integers(0, 2, size=donors.size)
        correct = rng.random(donors.size) < np.repeat(skill, cells)
        y_pred = np.where(correct, y_true, 1 - y_true)

        donor_result = donor_bootstrap(accuracy, y_true, y_pred, donors, n_replicates=300, seed=4)
        cell_donors = np.array([f"cell_{index}" for index in range(donors.size)])
        cell_result = donor_bootstrap(
            accuracy, y_true, y_pred, cell_donors, n_replicates=300, seed=4
        )
        donor_width = donor_result.upper - donor_result.lower
        cell_width = cell_result.upper - cell_result.lower
        assert donor_width > cell_width

    def test_deterministic_for_a_fixed_seed(self):
        donors = donor_labels(6, 15)
        rng = np.random.default_rng(5)
        y_true = rng.integers(0, 3, size=donors.size)
        y_pred = np.where(rng.random(donors.size) < 0.7, y_true, (y_true + 1) % 3)
        first = donor_bootstrap(accuracy, y_true, y_pred, donors, n_replicates=100, seed=7)
        second = donor_bootstrap(accuracy, y_true, y_pred, donors, n_replicates=100, seed=7)
        third = donor_bootstrap(accuracy, y_true, y_pred, donors, n_replicates=100, seed=8)
        assert (first.lower, first.upper) == (second.lower, second.upper)
        assert (first.lower, first.upper) != (third.lower, third.upper)

    def test_single_donor_is_not_applicable(self):
        donors = donor_labels(1, 30)
        y_true = np.tile([0, 1], 15)
        result = donor_bootstrap(accuracy, y_true, y_true, donors, n_replicates=10)
        assert result.lower is None
        assert result.upper is None
        assert "at least two donors" in result.not_applicable
        assert result.estimate == 1.0

    def test_records_failed_replicates_with_reasons(self):
        # Balanced accuracy needs two classes; one donor holds the only minority cells,
        # so replicates that omit that donor cannot compute the metric.
        donors = np.concatenate([donor_labels(4, 10), np.repeat("donor_rare", 10)])
        y_true = np.concatenate([np.zeros(40, dtype=int), np.ones(10, dtype=int)])
        y_pred = y_true.copy()
        result = donor_bootstrap(
            balanced_accuracy, y_true, y_pred, donors, n_replicates=100, seed=9
        )
        assert result.n_failed > 0
        assert result.n_valid + result.n_failed == 100
        assert any("class" in reason for reason in result.failure_reasons)
        assert result.estimate == pytest.approx(1.0)

    def test_full_sample_failure_blocks_the_interval(self):
        donors = donor_labels(4, 10)
        y_true = np.zeros(donors.size, dtype=int)
        result = donor_bootstrap(balanced_accuracy, y_true, y_true, donors, n_replicates=10)
        assert result.estimate is None
        assert result.lower is None
        assert "does not apply to the full sample" in result.not_applicable

    def test_narrower_level_gives_narrower_interval(self):
        rng = np.random.default_rng(10)
        donors = donor_labels(10, 20)
        y_true = rng.integers(0, 2, size=donors.size)
        y_pred = np.where(rng.random(donors.size) < 0.75, y_true, 1 - y_true)
        wide = donor_bootstrap(accuracy, y_true, y_pred, donors, n_replicates=200, level=0.95)
        narrow = donor_bootstrap(accuracy, y_true, y_pred, donors, n_replicates=200, level=0.80)
        assert (narrow.upper - narrow.lower) < (wide.upper - wide.lower)

    def test_rejects_bad_arguments(self):
        donors = donor_labels(4, 5)
        y_true = np.zeros(donors.size, dtype=int)
        with pytest.raises(ValueError, match="n_replicates"):
            donor_bootstrap(accuracy, y_true, y_true, donors, n_replicates=0)
        with pytest.raises(ValueError, match="level"):
            donor_bootstrap(accuracy, y_true, y_true, donors, level=1.0)
        with pytest.raises(ValueError, match="shape"):
            donor_bootstrap(accuracy, y_true, y_true[:-1], donors)
        with pytest.raises(ValueError, match="covers"):
            donor_bootstrap(accuracy, y_true, y_true, donors[:-1])

    def test_serialises_to_plain_dictionary(self):
        donors = donor_labels(4, 5)
        y_true = np.tile([0, 1], 10)
        record = donor_bootstrap(accuracy, y_true, y_true, donors, n_replicates=10).to_dict()
        assert record["unit"] == "donor"
        assert record["metric"] == "accuracy"
        assert len(record["interval"]) == 2


class TestMcNemar:
    def test_matches_hand_computed_chi_square(self):
        correct_a = np.array([True] * 20 + [False] * 5 + [True] * 10 + [False] * 10)
        correct_b = np.array([True] * 20 + [True] * 5 + [False] * 10 + [False] * 10)
        result = mcnemar_test(correct_a, correct_b)
        assert result.n_only_a_correct == 10
        assert result.n_only_b_correct == 5
        expected = (abs(10 - 5) - 1) ** 2 / 15
        assert result.statistic == pytest.approx(expected)
        assert result.p_value == pytest.approx(stats.chi2.sf(expected, df=1))
        assert result.continuity_corrected

    def test_continuity_correction_raises_the_p_value(self):
        correct_a = np.array([True] * 12 + [False] * 4 + [True] * 40)
        correct_b = np.array([False] * 12 + [True] * 4 + [True] * 40)
        corrected = mcnemar_test(correct_a, correct_b, continuity=True)
        raw = mcnemar_test(correct_a, correct_b, continuity=False)
        assert corrected.p_value > raw.p_value

    def test_large_asymmetry_is_significant(self):
        correct_a = np.array([True] * 30 + [False] * 2)
        correct_b = np.array([False] * 30 + [True] * 2)
        assert mcnemar_test(correct_a, correct_b).p_value < 0.01

    def test_no_disagreement_is_not_applicable(self):
        correct = np.array([True, False, True, True])
        result = mcnemar_test(correct, correct)
        assert result.statistic is None
        assert result.p_value is None
        assert "never disagree" in result.not_applicable

    def test_symmetric_disagreement_is_not_significant(self):
        correct_a = np.array([True] * 10 + [False] * 10)
        correct_b = np.array([False] * 10 + [True] * 10)
        assert mcnemar_test(correct_a, correct_b).p_value > 0.05

    def test_rejects_mismatched_or_empty_input(self):
        with pytest.raises(ValueError, match="shape"):
            mcnemar_test(np.array([True, False]), np.array([True]))
        with pytest.raises(ValueError, match="empty"):
            mcnemar_test(np.array([], dtype=bool), np.array([], dtype=bool))

    def test_serialises_to_plain_dictionary(self):
        correct_a = np.array([True, True, False, False])
        correct_b = np.array([True, False, True, False])
        record = mcnemar_test(correct_a, correct_b).to_dict()
        assert set(record) == {
            "n_only_a_correct",
            "n_only_b_correct",
            "statistic",
            "p_value",
            "continuity_corrected",
            "not_applicable",
        }


class TestEffectSize:
    def test_equal_proportions_give_zero(self):
        assert cohens_h(0.6, 0.6) == pytest.approx(0.0)

    def test_matches_hand_computed_value(self):
        expected = abs(2 * np.arcsin(np.sqrt(0.8)) - 2 * np.arcsin(np.sqrt(0.6)))
        assert cohens_h(0.8, 0.6) == pytest.approx(expected)

    def test_is_symmetric(self):
        assert cohens_h(0.2, 0.7) == pytest.approx(cohens_h(0.7, 0.2))

    def test_grows_with_separation(self):
        assert cohens_h(0.5, 0.55) < cohens_h(0.5, 0.75)

    def test_rejects_values_outside_unit_interval(self):
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            cohens_h(1.2, 0.5)
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            cohens_h(0.5, -0.1)


class TestSeedSummary:
    def test_reports_mean_spread_and_interval(self):
        values = [0.80, 0.82, 0.78, 0.81, 0.79]
        summary = summarize_seeds(values, metric="accuracy")
        array = np.asarray(values)
        assert summary.n_seeds == 5
        assert summary.mean == pytest.approx(array.mean())
        assert summary.std == pytest.approx(array.std(ddof=1))
        assert summary.minimum == pytest.approx(array.min())
        assert summary.maximum == pytest.approx(array.max())
        assert summary.lower < summary.mean < summary.upper
        assert summary.not_applicable is None

    def test_single_seed_has_no_spread(self):
        summary = summarize_seeds([0.8])
        assert summary.n_seeds == 1
        assert summary.mean == 0.8
        assert summary.std is None
        assert summary.lower is None
        assert "at least two usable seeds" in summary.not_applicable

    def test_unusable_values_are_dropped_and_counted(self):
        summary = summarize_seeds([0.8, None, 0.9, float("nan")])
        assert summary.n_seeds == 2
        assert summary.mean == pytest.approx(0.85)

    def test_all_unusable_is_not_applicable(self):
        summary = summarize_seeds([None, None])
        assert summary.n_seeds == 0
        assert summary.mean is None
        assert summary.not_applicable

    def test_identical_seeds_give_a_zero_width_interval(self):
        summary = summarize_seeds([0.75, 0.75, 0.75])
        assert summary.std == pytest.approx(0.0)
        assert summary.lower == summary.upper == pytest.approx(0.75)

    def test_serialises_to_plain_dictionary(self):
        record = summarize_seeds([0.7, 0.8, 0.9], metric="macro_f1").to_dict()
        assert record["metric"] == "macro_f1"
        assert record["n_seeds"] == 3
        assert len(record["interval"]) == 2

"""Offline tests for the repeated donor-split primary contrast."""

import pandas as pd
import pytest

from p22.eval.repeated_comparison import (
    initialization_primary_sensitivity,
    repeated_model_accuracy,
    repeated_primary_contrast,
)


def predictions(probabilities, labels, donors):
    return pd.DataFrame(
        {
            "donor_id": [str(value) for value in donors],
            "label": [int(value) for value in labels],
            "probability": [float(value) for value in probabilities],
        }
    )


def repeat_entry(repeat, cross, token, labels, donors):
    return {
        "repeat": repeat,
        "cross_attention": predictions(cross, labels, donors),
        "token_concat": predictions(token, labels, donors),
    }


def test_identical_models_give_zero_delta():
    labels = [0, 0, 1, 1]
    donors = ["d0", "d1", "d2", "d3"]
    probs = [0.1, 0.2, 0.8, 0.9]
    repeats = [repeat_entry(r, probs, probs, labels, donors) for r in range(3)]
    result = repeated_primary_contrast(repeats, n_replicates=50, seed=1)
    assert result["estimate"] == 0.0
    assert result["interval"] == [0.0, 0.0]
    assert result["advantage_demonstrated"] is False
    assert result["n_donors"] == 4


def test_consistent_advantage_detected():
    labels = [0, 0, 1, 1]
    donors = ["d0", "d1", "d2", "d3"]
    cross = [0.1, 0.2, 0.8, 0.9]
    token = [0.9, 0.8, 0.1, 0.2]  # flips every donor
    repeats = [repeat_entry(r, cross, token, labels, donors) for r in range(4)]
    result = repeated_primary_contrast(repeats, n_replicates=200, seed=3)
    assert result["estimate"] == 1.0
    assert result["interval"][0] is not None and result["interval"][0] > 0
    assert result["advantage_demonstrated"] is True
    assert result["practical_margin"] == 0.5


def test_donor_sets_must_match_across_repeats():
    labels = [0, 0, 1, 1]
    donors = ["d0", "d1", "d2", "d3"]
    repeats = [repeat_entry(0, [0.1, 0.2, 0.8, 0.9], [0.1, 0.2, 0.8, 0.9], labels, donors)]
    repeats.append(
        repeat_entry(
            1, [0.1, 0.2, 0.8, 0.9], [0.1, 0.2, 0.8, 0.9], labels, ["d0", "d1", "d2", "dX"]
        )
    )
    with pytest.raises(ValueError, match="identical across repeats"):
        repeated_primary_contrast(repeats)


def test_duplicate_donors_refused():
    labels = [0, 0, 1, 1]
    donors = ["d0", "d0", "d2", "d3"]
    repeats = [repeat_entry(0, [0.1, 0.2, 0.8, 0.9], [0.1, 0.2, 0.8, 0.9], labels, donors)]
    with pytest.raises(ValueError, match="duplicate donor"):
        repeated_primary_contrast(repeats)


def test_single_class_refused():
    labels = [0, 0, 0, 0]
    donors = ["d0", "d1", "d2", "d3"]
    repeats = [repeat_entry(0, [0.1, 0.2, 0.8, 0.9], [0.1, 0.2, 0.8, 0.9], labels, donors)]
    with pytest.raises(ValueError, match="both binary classes"):
        repeated_primary_contrast(repeats)


def test_two_donors_count_failed_resamples():
    labels = [0, 1]
    donors = ["d0", "d1"]
    repeats = [repeat_entry(r, [0.1, 0.9], [0.1, 0.9], labels, donors) for r in range(2)]
    result = repeated_primary_contrast(repeats, n_replicates=40, seed=5)
    assert result["estimate"] == 0.0
    assert result["n_failed"] > 0
    assert result["n_valid"] + result["n_failed"] == 40
    assert "single-class donor resample" in result["failure_reasons"]


def test_bootstrap_is_deterministic():
    labels = [0, 0, 0, 1, 1, 1]
    donors = [f"d{i}" for i in range(6)]
    cross = [0.1, 0.2, 0.3, 0.7, 0.8, 0.9]
    token = [0.4, 0.4, 0.5, 0.6, 0.5, 0.6]
    repeats = [repeat_entry(r, cross, token, labels, donors) for r in range(3)]
    first = repeated_primary_contrast(repeats, n_replicates=100, seed=9)
    second = repeated_primary_contrast(repeats, n_replicates=100, seed=9)
    assert first == second


def test_model_accuracy_summary():
    labels = [0, 0, 1, 1]
    donors = ["d0", "d1", "d2", "d3"]
    probs = [0.1, 0.2, 0.8, 0.9]
    repeats = [repeat_entry(r, probs, probs, labels, donors) for r in range(2)]
    summary = repeated_model_accuracy(repeats, "cross_attention")
    assert summary["per_repeat"] == {0: 1.0, 1: 1.0}
    assert summary["mean"] == 1.0
    assert summary["n_usable"] == 2


def test_invalid_level_and_replicates_refused():
    labels = [0, 1]
    donors = ["d0", "d1"]
    repeats = [repeat_entry(0, [0.1, 0.9], [0.1, 0.9], labels, donors)]
    with pytest.raises(ValueError, match="n_replicates"):
        repeated_primary_contrast(repeats, n_replicates=0)
    with pytest.raises(ValueError, match="level"):
        repeated_primary_contrast(repeats, level=1.0)


def _uneven_class_repeat(seed: int, cross_flip: bool = False):
    """One pooled repeat whose pooled delta differs from the per-fold delta mean.

    The donors split into two held-out folds with different class balances:
      fold A: d0=0, d1=1, d2=1
      fold B: d3=0, d4=0, d5=1
    Pooled across a repeat the donor balanced-accuracy delta is +1/6; averaged
    per fold it is 0.0, because each fold is individually degenerate.
    """
    labels = [0, 1, 1, 0, 0, 1]
    donors = [f"d{i}" for i in range(6)]
    cross = [0.9, 0.9, 0.9, 0.1, 0.1, 0.1]  # predicts A correctly, B negatively
    token = [0.1] * 6  # always predicts class 0
    if cross_flip:
        cross = [1.0 - value for value in cross]
    return repeat_entry(seed, cross, token, labels, donors)


def test_initialization_primary_sensitivity_uses_pooled_donor_estimand():
    repeats = [_uneven_class_repeat(0)]
    pooled = repeated_primary_contrast(repeats, n_replicates=40, seed=7)
    result = initialization_primary_sensitivity({0: repeats}, n_replicates=40, seed=7)
    summary = result["per_seed"][0]
    assert summary["estimate"] == pooled["estimate"]
    assert abs(summary["estimate"] - 1.0 / 6.0) < 1e-12
    assert summary["n_donors"] == 6
    assert summary["practical_margin"] == pooled["practical_margin"]

    per_fold_deltas = [
        repeated_primary_contrast(
            [
                repeat_entry(
                    0,
                    [0.9, 0.9, 0.9],
                    [0.1, 0.1, 0.1],
                    [0, 1, 1],
                    ["d0", "d1", "d2"],
                )
            ],
            n_replicates=5,
            seed=7,
        )["estimate"],
        repeated_primary_contrast(
            [
                repeat_entry(
                    0,
                    [0.1, 0.1, 0.1],
                    [0.1, 0.1, 0.1],
                    [0, 0, 1],
                    ["d3", "d4", "d5"],
                )
            ],
            n_replicates=5,
            seed=7,
        )["estimate"],
    ]
    assert summary["estimate"] != pytest.approx(sum(float(v) for v in per_fold_deltas) / 2)
    assert float(sum(per_fold_deltas) / 2) == 0.0


def test_initialization_primary_sensitivity_spread_over_seed_estimates():
    seed_repeats = {
        0: [_uneven_class_repeat(0)],
        1: [_uneven_class_repeat(0, cross_flip=True)],
    }
    result = initialization_primary_sensitivity(seed_repeats, n_replicates=40, seed=7)
    assert result["n_seeds"] == 2
    assert set(result["per_seed"]) == {0, 1}
    scores = result["estimate_spread"]["scores"]
    assert set(scores) == {0, 1}
    assert result["estimate_spread"]["spread"] == pytest.approx(
        max(scores.values()) - min(scores.values())
    )
    assert result["advantage_by_seed"] == {0: False, 1: False}
    assert scores[0] != pytest.approx(scores[1])


def test_initialization_primary_sensitivity_refuses_empty():
    with pytest.raises(ValueError, match="at least one initialization seed"):
        initialization_primary_sensitivity({})
    with pytest.raises(ValueError, match="no repeats"):
        initialization_primary_sensitivity({0: []})

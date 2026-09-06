"""Paired comparison contracts, tested without external predictions."""

from dataclasses import FrozenInstanceError, replace

import numpy as np
import pandas as pd
import pytest

from p22.eval.multiome_protocol import MultiomeProtocol, paired_comparison


def predictions():
    labels = np.array([0] * 13 + [1] * 13)
    return pd.DataFrame(
        {
            "donor_id": [f"d{i:02}" for i in range(26)],
            "label": labels,
            "probability": labels.astype(float),
        }
    )


def test_protocol_is_immutable_fingerprinted_and_rejects_invalid_settings():
    protocol = MultiomeProtocol()
    assert protocol.fingerprint == MultiomeProtocol().fingerprint
    assert protocol.fingerprint != replace(protocol, max_epochs=2).fingerprint
    with pytest.raises(FrozenInstanceError):
        protocol.max_epochs = 2
    for settings in (
        {"max_epochs": True},
        {"n_tokens": 1},
        {"n_heads": 3},
        {"learning_rate": float("nan")},
        {"dropout": 1},
        {"feature_budget": 0},
        {"n_folds": 1},
    ):
        with pytest.raises(ValueError):
            MultiomeProtocol(**settings)


def test_paired_delta_uses_same_donor_indices_and_directional_success():
    left = predictions()
    right = left.copy()
    right.loc[[0, 13], "probability"] = [1, 0]
    result = paired_comparison(left, right.iloc[::-1])
    assert result["estimate"] == pytest.approx(1 / 13)
    assert result["practical_margin"] == 0.08
    assert result["n_valid"] + result["n_failed"] == 1000
    assert not result["advantage_demonstrated"]  # delta below the frozen practical margin
    identical = paired_comparison(left, left)
    assert identical["estimate"] == 0 and identical["interval"] == [0, 0]
    reverse = paired_comparison(right, left)
    assert reverse["estimate"] < 0 and not reverse["advantage_demonstrated"]
    right["probability"] = 1 - left["probability"]
    assert paired_comparison(left, right)["advantage_demonstrated"]


@pytest.mark.parametrize("problem", ["missing", "duplicate", "label", "nan", "range", "null"])
def test_comparison_rejects_unpaired_or_invalid_predictions(problem):
    left, right = predictions(), predictions()
    if problem == "missing":
        right = right.iloc[1:]
    elif problem == "duplicate":
        right.loc[0, "donor_id"] = right.loc[1, "donor_id"]
    elif problem == "label":
        right.loc[0, "label"] = 1
    elif problem == "nan":
        right.loc[0, "probability"] = np.nan
    elif problem == "range":
        right.loc[0, "probability"] = 1.1
    else:
        right.loc[0, "donor_id"] = None
    with pytest.raises(ValueError):
        paired_comparison(left, right)


def test_failed_single_class_resamples_are_reported():
    two = predictions().iloc[[0, 13]]
    result = paired_comparison(two, two)
    assert result["n_failed"] > 0
    assert result["failure_reasons"]

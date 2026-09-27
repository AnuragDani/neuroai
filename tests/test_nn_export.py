"""Tests for N15 out-of-fold cell-score export helpers."""

from __future__ import annotations

import pytest

from scripts.export_nn_v2_cell_scores import assert_five_appearances


def test_export_script_exposes_main():
    import scripts.export_nn_v2_cell_scores as ex

    assert hasattr(ex, "main")
    assert hasattr(ex, "assert_five_appearances")
    assert hasattr(ex, "export_run")


def test_assert_five_appearances_passes_when_each_cell_has_five():
    scores = {
        "R3_ca": {
            "c1": {"s": [0.1] * 5, "a": [0.2] * 5, "chr21": [0.0] * 5},
            "c2": {"s": [0.3] * 5, "a": [0.1] * 5, "chr21": [0.1] * 5},
        }
    }
    assert_five_appearances(scores)


def test_assert_five_appearances_rejects_partial_repeats():
    scores = {
        "R3_ca": {
            "c1": {"s": [0.1, 0.2, 0.3, 0.4], "a": [0.1] * 4, "chr21": [0.0] * 4},
        }
    }
    with pytest.raises(AssertionError, match="appeared 4 times"):
        assert_five_appearances(scores)

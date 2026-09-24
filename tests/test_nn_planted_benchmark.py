"""Offline tests for the N4 planted-signal benchmark helpers.

Only the pure helpers are exercised; no real data is read and no model is fit.
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


bench = load("run_nn_planted_benchmark", "scripts/run_nn_planted_benchmark.py")


def test_delta_grid_has_16_cells():
    cells = bench.delta_grid()
    assert len(cells) == 16
    assert cells[0] == ("S0", 0.0)
    assert sum(scenario == "S0" for scenario, _ in cells) == 1
    for scenario in ("S1", "S2", "S3", "S4", "S5"):
        deltas = [delta for name, delta in cells if name == scenario]
        assert deltas == [0.25, 0.5, 1.0]


def test_fold_positions_map_train_val_test():
    positions = bench.fold_positions(
        np.arange(4), np.arange(4, 6), np.arange(6, 8)
    )
    assert positions["train"].tolist() == [0, 1, 2, 3]
    assert positions["val"].tolist() == [4, 5]
    assert positions["test"].tolist() == [6, 7]
    assert positions["holdout_rows"].tolist() == [4, 5, 6, 7]


def test_donor_scores_perfect_and_single_class():
    labels = np.array([0, 0, 1, 1])
    probs = np.array([0.1, 0.2, 0.8, 0.9])
    donors = np.array(["d0", "d1", "d2", "d3"])
    perfect = bench.donor_scores(labels, probs, donors)
    assert perfect["status"] == "ok"
    assert perfect["donor_balanced_accuracy"] == 1.0
    assert perfect["donor_auroc"] == 1.0
    assert perfect["donor_log_loss"] < 0.3
    single = bench.donor_scores(np.zeros(4, dtype=int), probs, donors)
    assert single["status"] == "single_class"
    assert single["donor_balanced_accuracy"] is None


def test_regime_labels_and_acceptance_checks():
    models = ("logreg_concat", "rna_atac_concat", "gated_fusion", "token_concat",
              "cross_attention")
    records = []
    for name in models:
        for fold in range(3):
            records.append(
                {"scenario": "S1", "delta": 1.0, "model": name, "fold": fold,
                 "donor_balanced_accuracy": 0.95 if name != "cross_attention" else 0.91,
                 "status": "ok"}
            )
            records.append(
                {"scenario": "S0", "delta": 0.0, "model": name, "fold": fold,
                 "donor_balanced_accuracy": 0.5, "status": "ok"}
            )
            records.append(
                {"scenario": "S5", "delta": 1.0, "model": name, "fold": fold,
                 "donor_balanced_accuracy": 0.5, "status": "ok"}
            )
    labels = bench.regime_labels(records)
    assert labels["S1@1.0"]["regime"] == "LINEAR_SUFFICIENT"
    checks = bench.acceptance_checks(records)
    assert checks["s0_null_within_0p35_0p65"] is True
    assert checks["s1_delta1_all_models_at_least_0p9"] is True
    assert checks["s5_delta1_within_0p05_of_chance"] is True
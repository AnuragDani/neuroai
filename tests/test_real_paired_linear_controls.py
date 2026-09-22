"""Offline tests for the paired simple linear controls."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


def test_donor_cell_weights_are_inverse_count_and_mean_one():
    module = load("run_real_paired_linear_controls", "scripts/run_real_paired_linear_controls.py")
    donors = ["a", "a", "a", "b", "b", "c"]
    weights = module.donor_cell_weights(donors)
    assert weights.shape == (6,)
    # Donor a has 3 cells, b has 2, c has 1; per-cell weights are inverse counts.
    assert np.isclose(weights[0], weights[1]) and np.isclose(weights[0], weights[2])
    assert weights[0] < weights[3] < weights[5]
    assert np.isclose(weights.mean(), 1.0)


def test_fit_logistic_converges_on_separable_data():
    module = load("run_real_paired_linear_controls", "scripts/run_real_paired_linear_controls.py")
    rng = np.random.default_rng(0)
    x = np.vstack([rng.normal(-2, 1, (20, 4)), rng.normal(2, 1, (20, 4))])
    labels = np.array([0] * 20 + [1] * 20)
    weights = np.ones(len(labels))
    estimator, convergence = module.fit_logistic(x, labels, weights)
    assert convergence["converged"] is True
    assert convergence["extension_used"] is False
    assert estimator.predict(x).tolist() == labels.tolist()


def test_fit_logistic_records_numerical_extension(monkeypatch):
    module = load("run_real_paired_linear_controls", "scripts/run_real_paired_linear_controls.py")
    monkeypatch.setattr(module, "FROZEN", {**module.FROZEN, "max_iter": 1})
    rng = np.random.default_rng(1)
    x = rng.normal(0, 1, (60, 5))
    labels = (x[:, 0] + 0.5 * x[:, 1] > 0).astype(int)
    weights = np.ones(len(labels))
    _estimator, convergence = module.fit_logistic(x, labels, weights)
    assert convergence["extension_used"] is True
    assert convergence["extension_max_iter"] == module.CONVERGENCE_EXTENSION_MAX_ITER
    assert "independent of test accuracy" in convergence["reason"]


def test_reference_repeats_loads_token_concat_predictions(tmp_path):
    module = load("run_real_paired_linear_controls", "scripts/run_real_paired_linear_controls.py")
    per_fold = [
        {
            "repeat": 0,
            "fold": 0,
            "record": {
                "models": {
                    "token_concat": {
                        "predictions": [
                            {"donor_id": "d1", "label": 0, "probability": 0.2, "prediction": 0},
                            {"donor_id": "d2", "label": 1, "probability": 0.8, "prediction": 1},
                        ]
                    }
                }
            },
        }
    ]
    (tmp_path / "per_fold.json").write_text(json.dumps(per_fold))
    repeats = module._reference_repeats(tmp_path)
    assert set(repeats) == {0}
    frame = pd.concat(repeats[0]["token_concat"], ignore_index=True)
    assert sorted(frame.donor_id) == ["d1", "d2"]

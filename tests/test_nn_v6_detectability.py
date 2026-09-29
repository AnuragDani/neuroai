"""X4: detectability helpers for S4 CA−TC contrast at 30 donors."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parents[1]


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


mod = _load("nn_v6_detectability", "scripts/nn_v6_detectability.py")


def _frame(donors, labels, probs) -> pd.DataFrame:
    return pd.DataFrame({"donor_id": donors, "label": labels, "probability": probs})


def test_ci_excludes_zero():
    assert mod.ci_excludes_zero([0.1, 0.3]) is True
    assert mod.ci_excludes_zero([-0.3, -0.1]) is True
    assert mod.ci_excludes_zero([-0.1, 0.2]) is False
    assert mod.ci_excludes_zero([None, 0.2]) is False
    assert mod.ci_excludes_zero([0.0, 0.1]) is False


def test_summarize_repeat_contrast_detects_clear_advantage():
    donors = [f"d{i}" for i in range(30)]
    labels = [i % 2 for i in range(30)]
    # CA perfect; TC chance → positive delta, CI should exclude 0.
    ca = _frame(donors, labels, [0.1 if y == 0 else 0.9 for y in labels])
    tc = _frame(donors, labels, [0.5] * 30)
    out = mod.summarize_repeat_contrast(ca, tc, n_replicates=200, seed=22)
    assert out["estimate"] is not None and out["estimate"] > 0.2
    assert out["ci_excludes_zero"] is True
    assert out["ci"][0] > 0


def test_summarize_repeat_contrast_null_includes_zero():
    donors = [f"d{i}" for i in range(30)]
    labels = [i % 2 for i in range(30)]
    probs = [0.2 if y == 0 else 0.8 for y in labels]
    ca = _frame(donors, labels, probs)
    tc = _frame(donors, labels, probs)
    out = mod.summarize_repeat_contrast(ca, tc, n_replicates=200, seed=22)
    assert abs(out["estimate"]) < 1e-9
    assert out["ci_excludes_zero"] is False
    assert out["ci"][0] <= 0 <= out["ci"][1]


def test_min_detectable_delta_and_build_summary(tmp_path: Path):
    # Fabricate 2 repeats × 5 folds for each delta with controlled detection.
    donors = [f"d{i:02d}" for i in range(30)]
    labels = [i % 2 for i in range(30)]
    records = []
    for delta in mod.DELTAS:
        for repeat in range(2):
            # Strong CA advantage only for delta >= 0.75.
            strong = delta >= 0.75
            for fold in range(5):
                ids = donors[fold * 6 : (fold + 1) * 6]
                y = labels[fold * 6 : (fold + 1) * 6]
                if strong:
                    ca_p = [0.05 if yi == 0 else 0.95 for yi in y]
                    tc_p = [0.5] * len(y)
                else:
                    ca_p = tc_p = [0.2 if yi == 0 else 0.8 for yi in y]
                records.append({
                    "scenario": "S4",
                    "delta": float(delta),
                    "repeat": repeat,
                    "fold": fold,
                    "status": "ok",
                    "ca_donors": [
                        {"donor_id": d, "label": yi, "probability": p}
                        for d, yi, p in zip(ids, y, ca_p)
                    ],
                    "tc_donors": [
                        {"donor_id": d, "label": yi, "probability": p}
                        for d, yi, p in zip(ids, y, tc_p)
                    ],
                })

    protocol = mod.detectability_protocol(2)
    summary = mod.build_summary(records, n_repeats=2, cap=1000, protocol=protocol)
    assert summary["min_detectable_delta"] == 0.75
    assert summary["statement"] is None
    assert summary["per_delta"]["0.1"]["detection_fraction"] == 0.0
    assert summary["per_delta"]["0.75"]["detection_fraction"] == 1.0
    assert summary["per_delta"]["1.0"]["mean_contrast"] > 0

    # Null-across-board → min_detectable_delta null + statement.
    null_records = []
    for delta in mod.DELTAS:
        for repeat in range(2):
            for fold in range(5):
                ids = donors[fold * 6 : (fold + 1) * 6]
                y = labels[fold * 6 : (fold + 1) * 6]
                probs = [0.2 if yi == 0 else 0.8 for yi in y]
                null_records.append({
                    "scenario": "S4",
                    "delta": float(delta),
                    "repeat": repeat,
                    "fold": fold,
                    "status": "ok",
                    "ca_donors": [
                        {"donor_id": d, "label": yi, "probability": p}
                        for d, yi, p in zip(ids, y, probs)
                    ],
                    "tc_donors": [
                        {"donor_id": d, "label": yi, "probability": p}
                        for d, yi, p in zip(ids, y, probs)
                    ],
                })
    null_summary = mod.build_summary(null_records, n_repeats=2, cap=1000, protocol=protocol)
    assert null_summary["min_detectable_delta"] is None
    assert null_summary["statement"] == "not detectable up to δ = 1.0"

    md = tmp_path / "DETECTABILITY.md"
    mod.write_reading(null_summary, md)
    text = md.read_text()
    assert "min_detectable_delta" in text
    assert text.count("\n") <= 30
    assert "not detectable up to" in text


def test_delta_grid_and_protocol():
    assert list(mod.DELTAS) == [0.1, 0.25, 0.5, 0.75, 1.0]
    assert mod.SCENARIO == "S4"
    assert mod.MODELS == ("cross_attention", "token_concat")
    proto = mod.detectability_protocol(3)
    assert proto.n_repeats == 3
    assert proto.n_folds == 5
    assert proto.fingerprint == mod.detectability_protocol(3).fingerprint


def test_fold_local_donors_partition_without_duplicates():
    """Regression: positions index fold arrays, so donor IDs must be fold-local."""
    donors_fold = np.array([f"d{i}" for i in range(12)])
    labels = np.array([0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1])
    # Simulate fold-local test slice at the end of [train|val|test].
    positions_test = np.arange(8, 12)
    probs = np.array([0.1, 0.2, 0.8, 0.9])
    frame = mod._donor_frame(labels[positions_test], probs, donors_fold[positions_test])
    assert set(frame["donor_id"]) == {"d8", "d9", "d10", "d11"}
    # Original-metadata-style indexing would wrongly reuse a fixed absolute slice.
    donors_orig = np.array([f"orig{i}" for i in range(12)])
    wrong = mod._donor_frame(labels[positions_test], probs, donors_orig[positions_test])
    assert set(wrong["donor_id"]) == {"orig8", "orig9", "orig10", "orig11"}
    assert set(wrong["donor_id"]).isdisjoint(set(frame["donor_id"]))

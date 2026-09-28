"""Tests for V1 per-fold metrics (no pooling artefact)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parents[1]


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


mod = _load("nn_v5_per_fold_metrics", "scripts/nn_v5_per_fold_metrics.py")


def _write_fold(
    folds_dir: Path,
    *,
    repeat: int,
    fold: int,
    arm: str,
    labels: list[int],
    probs: list[float],
) -> None:
    donors = [f"d{i}" for i in range(len(labels))]
    rec = {
        "repeat": repeat,
        "fold": fold,
        "arm": arm,
        "donor_ids": donors,
        "donor_labels": labels,
        "donor_probabilities": probs,
        "best_grid_point": {},
        "fit_donors": [],
    }
    (folds_dir / f"r{repeat}_f{fold}_{arm}.json").write_text(json.dumps(rec))


def test_constant_predictor_ba_is_exactly_half():
    """Majority (constant) predictor must get BA=0.5 whenever both classes appear."""
    labels = [0, 0, 1, 1, 0, 1]
    for const in (0.0, 1.0, 0.3, 0.7):
        m = mod.fold_metrics(labels, [const] * len(labels))
        assert m["donor_ba"] == 0.5
        assert m["n_donors_class_0"] == 3
        assert m["n_donors_class_1"] == 3


def test_perfect_scores_give_auroc_one():
    labels = [0, 0, 1, 1]
    probs = [0.1, 0.2, 0.8, 0.9]
    m = mod.fold_metrics(labels, probs)
    assert m["donor_auroc"] == 1.0
    assert m["donor_ba"] == 1.0


def test_summarize_arm_mean_sd_and_pooled(tmp_path: Path):
    folds_dir = tmp_path / "folds"
    folds_dir.mkdir()
    # Fold 0: perfect separation; fold 1: inverted (AUROC 0).
    _write_fold(
        folds_dir,
        repeat=0,
        fold=0,
        arm="toy",
        labels=[0, 0, 1, 1],
        probs=[0.1, 0.2, 0.8, 0.9],
    )
    _write_fold(
        folds_dir,
        repeat=0,
        fold=1,
        arm="toy",
        labels=[0, 0, 1, 1],
        probs=[0.9, 0.8, 0.2, 0.1],
    )
    # Majority constant on both folds.
    _write_fold(
        folds_dir,
        repeat=0,
        fold=0,
        arm="majority",
        labels=[0, 0, 1, 1],
        probs=[1.0, 1.0, 1.0, 1.0],
    )
    _write_fold(
        folds_dir,
        repeat=0,
        fold=1,
        arm="majority",
        labels=[0, 1, 0, 1],
        probs=[0.0, 0.0, 0.0, 0.0],
    )

    summary = mod.compute_per_fold_metrics(tmp_path)
    assert set(summary["per_arm"]) == {"toy", "majority"}

    toy = summary["per_arm"]["toy"]
    assert toy["n_folds"] == 2
    assert abs(toy["per_fold_auroc_mean"] - 0.5) < 1e-12
    assert abs(toy["per_fold_auroc_sd"] - 0.5) < 1e-12
    # Pooled across inverted folds → chance AUROC.
    assert abs(toy["pooled_auroc"] - 0.5) < 1e-12

    maj = summary["per_arm"]["majority"]
    assert all(row["donor_ba"] == 0.5 for row in maj["per_fold"])
    assert maj["per_fold_ba_mean"] == 0.5
    assert maj["per_fold_ba_sd"] == 0.0


def test_write_outputs_and_canonical_pointer(tmp_path: Path):
    run = tmp_path / "run"
    folds = run / "folds"
    folds.mkdir(parents=True)
    _write_fold(
        folds,
        repeat=0,
        fold=0,
        arm="majority",
        labels=[0, 1],
        probs=[1.0, 1.0],
    )
    out = tmp_path / "out"
    summary = mod.write_outputs(run, out, canonical_text="reports/generated/nn_20260923/ladder_v2")
    assert summary["n_arms"] == 1
    assert (out / "per_fold_metrics.json").is_file()
    assert (out / "CANONICAL_LADDER.txt").read_text().strip() == (
        "reports/generated/nn_20260923/ladder_v2"
    )


def test_canonical_ladder_majority_ba_is_half_every_fold():
    """Live check on the frozen ladder_v2 majority arm (constant predictor)."""
    run = ROOT / "reports/generated/nn_20260923/ladder_v2"
    if not (run / "folds").is_dir():
        return
    summary = mod.compute_per_fold_metrics(run)
    assert summary["n_arms"] == 18
    assert len(summary["per_arm"]) == 18
    maj = summary["per_arm"]["majority"]
    assert maj["n_folds"] == 25
    assert all(row["donor_ba"] == 0.5 for row in maj["per_fold"]), maj["per_fold"]
    for arm, block in summary["per_arm"].items():
        assert "per_fold_auroc_mean" in block, arm
        assert "per_fold_auroc_sd" in block, arm
        assert "pooled_auroc" in block, arm
        assert "per_fold" in block, arm

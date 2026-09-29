"""X3: per-fold R3_ca − R3_tc contrast + donor-cluster bootstrap CI."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


mod = _load("nn_v6_per_fold_contrast", "scripts/nn_v6_per_fold_contrast.py")


def _write_fold(
    folds_dir: Path,
    *,
    repeat: int,
    fold: int,
    arm: str,
    donor_ids: list[str],
    labels: list[int],
    probs: list[float],
) -> None:
    rec = {
        "repeat": repeat,
        "fold": fold,
        "arm": arm,
        "donor_ids": donor_ids,
        "donor_labels": labels,
        "donor_probabilities": probs,
        "best_grid_point": {},
        "fit_donors": [],
    }
    (folds_dir / f"r{repeat}_f{fold}_{arm}.json").write_text(json.dumps(rec))


def _toy_ladder(tmp_path: Path) -> Path:
    """5×5 folds, 30 donors partitioned 6 per fold; CA better than TC on BA."""
    run = tmp_path / "ladder_toy"
    folds = run / "folds"
    folds.mkdir(parents=True)
    # Interleave labels so every 6-donor fold has both classes (3/3).
    donors = [f"d{i:02d}" for i in range(30)]
    labels_all = [i % 2 for i in range(30)]
    for repeat in range(5):
        order = donors[repeat:] + donors[:repeat]
        labs = labels_all[repeat:] + labels_all[:repeat]
        for fold in range(5):
            ids = order[fold * 6 : (fold + 1) * 6]
            y = labs[fold * 6 : (fold + 1) * 6]
            assert set(y) == {0, 1}
            # CA: strong but fold-dependent; TC: weaker / inverted on some folds.
            strength = 0.55 + 0.08 * ((fold + repeat) % 5)
            ca_probs = [1.0 - strength if yi == 0 else strength for yi in y]
            flip = (fold + repeat) % 3 == 0
            tc_probs = (
                [strength if yi == 0 else 1.0 - strength for yi in y]
                if flip
                else [0.5] * len(y)
            )
            _write_fold(
                folds,
                repeat=repeat,
                fold=fold,
                arm="R3_ca",
                donor_ids=ids,
                labels=y,
                probs=ca_probs,
            )
            _write_fold(
                folds,
                repeat=repeat,
                fold=fold,
                arm="R3_tc",
                donor_ids=ids,
                labels=y,
                probs=tc_probs,
            )
    return run


def test_load_paired_folds_computes_deltas(tmp_path: Path):
    run = _toy_ladder(tmp_path)
    rows = mod.load_paired_folds(run)
    assert len(rows) == 25
    for r in rows:
        assert r["donor_ba_delta"] is not None
        assert r["donor_auroc_delta"] is not None
        assert r["donor_ba_ca"] >= r["donor_ba_tc"] - 1e-9


def test_summarize_run_estimate_and_ci_shape(tmp_path: Path):
    run = _toy_ladder(tmp_path)
    out = mod.summarize_run(run, metric="donor_ba", n_draws=50, seed=22)
    assert out["metric"] == "donor_ba"
    assert out["estimate"] is not None
    assert len(out["ci"]) == 2
    assert out["ci"][0] <= out["ci"][1]
    assert out["n_folds"] == 25
    assert len(out["per_fold"]) == 25
    assert out["valid_draws"] == 50
    assert out["donor_auroc"]["estimate"] is not None
    assert len(out["donor_auroc"]["ci"]) == 2


def test_bootstrap_is_deterministic_with_seed(tmp_path: Path):
    run = _toy_ladder(tmp_path)
    a = mod.summarize_run(run, n_draws=40, seed=22)
    b = mod.summarize_run(run, n_draws=40, seed=22)
    c = mod.summarize_run(run, n_draws=40, seed=23)
    assert a["ci"] == b["ci"]
    assert a["ci"] != c["ci"]


def test_write_includes_v4_when_present(tmp_path: Path):
    v3 = _toy_ladder(tmp_path / "v3")
    v4 = _toy_ladder(tmp_path / "v4")
    out = tmp_path / "per_fold_contrast.json"
    payload = mod.write_per_fold_contrast(
        out, run_v3=v3, run_v4=v4, n_draws=20, seed=22
    )
    assert out.is_file()
    loaded = json.loads(out.read_text())
    assert loaded["estimate"] is not None
    assert len(loaded["ci"]) == 2
    assert "per_fold" in loaded
    assert loaded["metric"] == "donor_ba"
    assert "ladder_v4_chr21forced" in loaded
    assert loaded["ladder_v4_chr21forced"]["estimate"] == payload["estimate"]
